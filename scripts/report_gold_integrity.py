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


def normalized_status(field: dict[str, Any]) -> str:
    return str(field.get("status") or "missing_or_nonexistent")


def transition_type(old_status: str, new_status: str) -> str:
    if old_status == new_status:
        return "unchanged_value_or_source"
    return f"{old_status}_to_{new_status}"


def load_integrity_reasons(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}


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
    by_group = {case_id: str(manifest[case_id]["source_group"]) for case_id in ids}
    integrity_rows = load_integrity_reasons(args.new_integrity_root / "gold_candidate_integrity_fields.csv")
    rows = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key, {}), new.get(key, {})
        if before.get("status") == after.get("status") and before.get("value") == after.get("value") and before.get("source_token_indices") == after.get("source_token_indices"):
            continue
        case_id, field_name = key
        rows.append({
            "case_id": case_id,
            "document_type": by_type[case_id],
            "source_group": by_group[case_id],
            "field_name": field_name,
            "old_status": normalized_status(before),
            "new_status": normalized_status(after),
            "old_value": before.get("value"),
            "new_value": after.get("value"),
            "old_source_token_indices": json.dumps(before.get("source_token_indices", [])),
            "new_source_token_indices": json.dumps(after.get("source_token_indices", [])),
            "source_token_indices_changed": before.get("source_token_indices", []) != after.get("source_token_indices", []),
            "transition_type": transition_type(normalized_status(before), normalized_status(after)),
            "generator_reason": after.get("gold_review") or "field absent from candidate",
            "independent_audit_reason": integrity_rows.get(key, {}).get("semantic_reason", "not available field or no audit row"),
            "semantic_classification": integrity_rows.get(key, {}).get("semantic_status", "NOT_APPLICABLE" if normalized_status(after) == "not_applicable" else "CANNOT_VERIFY"),
        })
    args.output_root.mkdir(parents=True, exist_ok=True)
    diff_path = args.output_root / "gold_denominator_diff.csv"
    with diff_path.open("w", encoding="utf-8-sig", newline="") as handle:
        columns = ["case_id", "document_type", "source_group", "field_name", "old_status", "new_status", "old_value", "new_value", "old_source_token_indices", "new_source_token_indices", "source_token_indices_changed", "transition_type", "generator_reason", "independent_audit_reason", "semantic_classification"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)

    counts = {"old": Counter(), "new": Counter()}
    all_counts: dict[str, dict[str, Counter]] = defaultdict(lambda: {"old": Counter(), "new": Counter()})
    field_counts: dict[str, dict[str, Counter]] = defaultdict(lambda: {"old": Counter(), "new": Counter()})
    for label, data in (("old", old), ("new", new)):
        for (case_id, field_name), field in data.items():
            status = normalized_status(field)
            kind = by_type[case_id]
            if status == "available":
                counts[label][kind] += 1
                counts[label]["Overall"] += 1
                counts[label][f"source_group:{by_group[case_id]}"] += 1
                field_counts[f"{by_type[case_id]}:{field_name}"][label]["available"] += 1
            all_counts["Overall"][label][status] += 1
            all_counts[kind][label][status] += 1
            all_counts[f"{kind}:{field_name}"][label][status] += 1

    transition_counts = Counter(row["transition_type"] for row in rows)
    transition_delta: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        for scope in ("Overall", row["document_type"], f"{row['document_type']}:{row['field_name']}", f"source_group:{row['source_group']}"):
            transition_delta[scope][row["transition_type"]] += 1

    def available_delta(scope: str) -> int:
        return counts["new"][scope] - counts["old"][scope]

    def transition_available_delta(scope: str) -> int:
        values = transition_delta[scope]
        entering = sum(value for name, value in values.items() if name.endswith("_to_available"))
        leaving = sum(value for name, value in values.items() if name.startswith("available_to_") and not name.endswith("_to_available"))
        return entering - leaving

    scopes = ["Overall", "Commercial Invoice", "Packing List", "B/L"] + sorted(field_counts) + [f"source_group:{group}" for group in sorted(set(by_group.values()))]
    reconciliation = {}
    for scope in scopes:
        expected = available_delta(scope) if scope in counts["old"] or scope in counts["new"] else 0
        actual = transition_available_delta(scope)
        reconciliation[scope] = {"expected_available_delta": expected, "transition_available_delta": actual, "match": expected == actual}
    reconciliation_pass = all(value["match"] for value in reconciliation.values())
    summary = {
        "cases": len(ids),
        "document_types": dict(Counter(by_type.values())),
        "old_available": dict(counts["old"]),
        "new_available": dict(counts["new"]),
        "delta_available": {key: counts["new"][key] - counts["old"][key] for key in sorted(set(counts["old"]) | set(counts["new"]))},
        "changed_fields": len(rows),
        "changed_by_document_type": dict(Counter(row["document_type"] for row in rows)),
        "changed_by_field": dict(Counter(f"{row['document_type']}:{row['field_name']}" for row in rows)),
        "transition_counts": dict(transition_counts),
        "transition_reconciliation": reconciliation,
        "transition_reconciliation_status": "PASS" if reconciliation_pass else "FAIL",
        "status_counts_by_scope": {scope: {label: dict(value[label]) for label in ("old", "new")} for scope, value in all_counts.items()},
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
