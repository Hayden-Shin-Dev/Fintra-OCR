"""Compare clean baseline values with independent v2 semantic candidates.

This is a read-only diagnostic.  It never changes OCR, Gold, or extraction
dispatch.  It is intended to separate candidate-generation/ranking signal
from the frozen baseline before a semantic arbitration rule is enabled.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction.v2.baseline import extract_baseline
from fintra.extraction.v2.layout import Layout, canonical
from fintra.extraction.v2.party import resolve as resolve_party
from fintra.extraction.v2.scalar import resolve as resolve_scalar
from fintra.extraction.v2.specs import DOCUMENT_FIELDS, FIELD_FAMILY, ITEM_FIELDS, PARTY_FIELDS
from fintra.extraction.v2.table import resolve as resolve_table
from fintra.ocr.adapter import OCRResult
from scripts.evaluate_field_extraction import _gold_fields


def _case_result(case_dir: Path, manifest: dict) -> OCRResult:
    candidates = sorted((case_dir / "outputs" / "recognition").glob("*.json"))
    if len(candidates) != 1:
        raise ValueError(f"expected one recognition JSON in {case_dir}, found {len(candidates)}")
    return OCRResult.from_json(candidates[0], document_type=manifest["document_type"], preserve_raw=False)


def _value(field: dict | None) -> str:
    return str((field or {}).get("value") or "")


def _match(left: str, right: str) -> bool:
    return bool(left and right and canonical(left) == canonical(right))


def diagnose(cases_root: Path, gold_source: str, gold_root: Path | None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = _case_result(case_dir, manifest)
        baseline = extract_baseline(result)
        layout = Layout(result)
        document_type = manifest["document_type"]
        anchor_fields = {name: tuple() for name in DOCUMENT_FIELDS[document_type]}
        from fintra.extraction.v2.specs import SPECS
        anchor_fields = {name: SPECS[name].aliases for name in DOCUMENT_FIELDS[document_type] if name in SPECS}
        anchors = layout.all_anchors(anchor_fields)
        parties: dict[str, dict] = {}
        candidates: dict[str, dict] = {}
        for field in DOCUMENT_FIELDS[document_type]:
            if field in PARTY_FIELDS:
                candidate = resolve_party(layout, field, anchors, parties)
                parties[field] = candidate
            else:
                candidate = resolve_scalar(layout, field, anchors)
            candidates[field] = candidate
        table_rows = resolve_table(layout, document_type) if document_type in ITEM_FIELDS else []
        gold = _gold_fields(case_dir, manifest, gold_source, gold_root)
        for item in gold:
            if item.get("status") != "available":
                continue
            field_name = item["field_name"]
            if field_name.startswith("items["):
                import re
                match = re.fullmatch(r"items\[(\d+)\]\.(.+)", field_name)
                if not match:
                    continue
                index, leaf = int(match.group(1)), match.group(2)
                base = (baseline.get("items") or [])[index].get(leaf, {}) if index < len(baseline.get("items") or []) else {}
                candidate = table_rows[index].get(leaf, {}) if index < len(table_rows) else {}
            else:
                base = baseline.get(field_name, {})
                candidate = candidates.get(field_name, {})
            gt = str(item.get("value") or "")
            base_value, candidate_value = _value(base), _value(candidate)
            base_correct = _match(base_value, gt)
            candidate_correct = _match(candidate_value, gt)
            if candidate_correct and not base_correct:
                outcome = "CANDIDATE_IMPROVES"
            elif base_correct and not candidate_correct and candidate_value:
                outcome = "CANDIDATE_REGRESSION"
            elif candidate_correct and base_correct:
                outcome = "BOTH_CORRECT"
            elif candidate_value:
                outcome = "BOTH_WRONG"
            else:
                outcome = "CANDIDATE_MISSING"
            meta = candidate.get("candidate") or {}
            rows.append({
                "case_id": manifest["case_id"],
                "document_type": document_type,
                "field_name": field_name,
                "field_family": FIELD_FAMILY.get(field_name, "table" if field_name.startswith("items[") else "scalar"),
                "gt_value": gt,
                "baseline_value": base_value,
                "candidate_value": candidate_value,
                "baseline_correct": base_correct,
                "candidate_correct": candidate_correct,
                "outcome": outcome,
                "candidate_status": candidate.get("status", "missing"),
                "candidate_anchor": meta.get("semantic_anchor", ""),
                "candidate_relation": meta.get("relation", ""),
                "candidate_section": meta.get("section", ""),
                "candidate_score": meta.get("score", ""),
                "candidate_source_text": candidate.get("source_text", ""),
                "baseline_source_text": base.get("source_text", ""),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--gold-source", required=True)
    parser.add_argument("--gold-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = diagnose(args.cases, args.gold_source, args.gold_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["case_id"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    from collections import Counter
    counts = Counter(row["outcome"] for row in rows)
    print(json.dumps({"rows": len(rows), "outcomes": counts}, ensure_ascii=False))
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
