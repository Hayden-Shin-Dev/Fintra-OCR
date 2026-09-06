"""Produce a source-only Gold integrity and denominator-change report."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_fields(root: Path, ids: list[str]) -> dict[tuple[str, str], dict[str, Any]]:
    result = {}
    for case_id in ids:
        path = root / case_id / "semantic_gold_fields.json"
        fields = json.loads(path.read_text(encoding="utf-8"))
        for field in fields:
            result[(case_id, str(field["field_name"]))] = field
    return result


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return {
        item["stable_sample_id"]: item
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
        for item in [json.loads(line)]
    }


def pct(value: int, total: int) -> str:
    return f"{100 * value / total:.2f}%" if total else "n/a"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl"))
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--new-integrity-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    ids = [line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    manifest = load_manifest(args.manifest)
    old = load_fields(args.old_root, ids)
    new = load_fields(args.new_root, ids)
    by_type = {case_id: manifest[case_id]["document_type"] for case_id in ids}
    rows = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key, {}), new.get(key, {})
        if before.get("status") == after.get("status") and before.get("value") == after.get("value") and before.get("source_token_indices") == after.get("source_token_indices"):
            continue
        case_id, field_name = key
        rows.append({
            "case_id": case_id,
            "document_type": by_type[case_id],
            "field_name": field_name,
            "old_status": before.get("status"),
            "new_status": after.get("status"),
            "old_value": before.get("value"),
            "new_value": after.get("value"),
            "old_source_token_indices": json.dumps(before.get("source_token_indices", [])),
            "new_source_token_indices": json.dumps(after.get("source_token_indices", [])),
            "source_token_indices_changed": before.get("source_token_indices", []) != after.get("source_token_indices", []),
            "new_gold_review": after.get("gold_review"),
        })
    args.output_root.mkdir(parents=True, exist_ok=True)
    diff_path = args.output_root / "gold_denominator_diff.csv"
    with diff_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["case_id"])
        writer.writeheader(); writer.writerows(rows)

    counts = {"old": Counter(), "new": Counter()}
    field_counts: dict[str, dict[str, Counter]] = defaultdict(lambda: {"old": Counter(), "new": Counter()})
    for label, data in (("old", old), ("new", new)):
        for (case_id, field_name), field in data.items():
            if field.get("status") == "available":
                kind = by_type[case_id]
                counts[label][kind] += 1
                counts[label]["Overall"] += 1
                field_counts[f"{by_type[case_id]}:{field_name}"][label]["available"] += 1
    summary = {
        "cases": len(ids),
        "document_types": dict(Counter(by_type.values())),
        "old_available": dict(counts["old"]),
        "new_available": dict(counts["new"]),
        "delta_available": {key: counts["new"][key] - counts["old"][key] for key in sorted(set(counts["old"]) | set(counts["new"]))},
        "changed_fields": len(rows),
        "changed_by_document_type": dict(Counter(row["document_type"] for row in rows)),
        "changed_by_field": dict(Counter(f"{row['document_type']}:{row['field_name']}" for row in rows)),
        "integrity_metrics": str(args.new_integrity_root / "gold_candidate_integrity_metrics.json"),
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    (args.output_root / "gold_denominator_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Prediction-blind Gold integrity report",
        "",
        "This report compares Gold status/value/source references only. OCR and extractor outputs were not read.",
        "The original Training TL is word-level (`data`, `x`, `y`) and does not encode semantic field labels; therefore structural integrity can PASS while semantic-role proof remains limited.",
        "",
        f"- Cases: {len(ids)}",
        f"- Types: {dict(Counter(by_type.values()))}",
        f"- Changed fields vs old Gold: {len(rows)}",
        f"- New integrity artifact: `{args.new_integrity_root / 'gold_candidate_integrity_metrics.json'}`",
        f"- FINAL-HOLDOUT #2 accessed: `false`",
        "",
        "## Available denominator audit",
        "",
        "| Scope | Overall | Commercial Invoice | Packing List | B/L |",
        "|---|---:|---:|---:|---:|",
        f"| Old | {counts['old']['Overall']} | {counts['old']['Commercial Invoice']} | {counts['old']['Packing List']} | {counts['old']['B/L']} |",
        f"| New | {counts['new']['Overall']} | {counts['new']['Commercial Invoice']} | {counts['new']['Packing List']} | {counts['new']['B/L']} |",
        f"| Delta | {counts['new']['Overall']-counts['old']['Overall']:+d} | {counts['new']['Commercial Invoice']-counts['old']['Commercial Invoice']:+d} | {counts['new']['Packing List']-counts['old']['Packing List']:+d} | {counts['new']['B/L']-counts['old']['B/L']:+d} |",
        "",
        "The denominator changes are not silently treated as accuracy changes: every changed field is listed in `gold_denominator_diff.csv` with old/new status, value, and source token indices.",
        "",
        "## Integrity interpretation",
        "",
        "- Source token/value/bbox and row-geometry checks are machine-auditable.",
        "- A raw TL file has no semantic labels; loading-vs-discharge, party role, and table-column meaning cannot be proven for every field from TL alone.",
        "- Consequently this artifact does not claim that every Gold value is semantically correct. Fields without decisive structural evidence remain a human/document-semantic review obligation.",
    ]
    (args.output_root / "GOLD_INTEGRITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
