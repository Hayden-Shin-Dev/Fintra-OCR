"""Create a separate conservative Gold view from an independent semantic audit.

This does not alter v2/v3/v3.1/v3.2/candidate9.  An available field is kept
only when the source-only auditor marked it VERIFIED_CORRECT; all other
available values become ambiguous_gt with no denominator contribution.  No
OCR/extractor result is read.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--diff", type=Path, required=True)
    args = parser.parse_args()
    audit = {}
    with args.audit_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            audit[(row["case_id"], row["field_name"])] = row
    changes = []
    counts = Counter()
    for case in sorted(p for p in args.source_root.iterdir() if p.is_dir()):
        old_path = case / "semantic_gold_fields.json"
        manifest_path = case / "case_manifest.json"
        if not old_path.is_file() or not manifest_path.is_file():
            continue
        fields = json.loads(old_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        new_fields = []
        for field in fields:
            value = dict(field)
            key = (case.name, str(field["field_name"]))
            audit_row = audit.get(key, {})
            if field.get("status") == "available" and audit_row.get("semantic_status") != "VERIFIED_CORRECT":
                value.update({"value": None, "status": "ambiguous_gt", "source_text": None, "bbox": None, "source_token_indices": [], "gold_review": "semantic_evidence_insufficient_after_original_tl_image_layout_audit"})
                counts[(manifest["document_type"], str(field["field_name"]))] += 1
                changes.append({"case_id": case.name, "document_type": manifest["document_type"], "field_name": field["field_name"], "old_status": field.get("status"), "new_status": value["status"], "old_value": field.get("value"), "new_value": None, "semantic_status": audit_row.get("semantic_status", "MISSING_AUDIT"), "reason": audit_row.get("semantic_reason", "no independent semantic proof"), "source_token_indices_changed": bool(field.get("source_token_indices"))})
            new_fields.append(value)
        target = args.output_root / "cases" / case.name
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, target / "case_manifest.json")
        (target / "semantic_gold_fields.json").write_text(json.dumps(new_fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.diff.parent.mkdir(parents=True, exist_ok=True)
    columns = ["case_id", "document_type", "field_name", "old_status", "new_status", "old_value", "new_value", "semantic_status", "reason", "source_token_indices_changed"]
    with args.diff.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader(); writer.writerows(changes)
    summary = {"changed_fields": len(changes), "changed_by_type": dict(Counter(x["document_type"] for x in changes)), "changed_by_field": dict(Counter(x["field_name"] for x in changes)), "gold_root": str(args.output_root / "cases"), "diff": str(args.diff), "prediction_blind": True, "ocr_read": False, "extractor_read": False, "final_holdout_2_accessed": False}
    (args.output_root / "gold_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
