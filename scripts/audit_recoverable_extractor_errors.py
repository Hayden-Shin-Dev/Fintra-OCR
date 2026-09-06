"""List Paddle fields whose raw OCR is recoverable but extraction is not correct."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate_ocr_stages as stage_eval


def audit(cases_root: Path, paddle_cases_root: Path, field_results: Path, gold_root: Path | None = None) -> list[dict[str, object]]:
    with field_results.open(encoding="utf-8-sig", newline="") as handle:
        extracted = {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}

    rows: list[dict[str, object]] = []
    for case_path in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        case = {
            "path": case_path,
            "case_id": manifest["case_id"],
            "document_id": manifest["document_id"],
            "document_type": manifest["document_type"],
        }
        paddle_path = paddle_cases_root / manifest["case_id"] / "outputs" / "recognition" / "paddle.json"
        paddle_rows = stage_eval._field_evidence(case, "paddle", stage_eval._read_ocr(paddle_path), gold_root)
        for evidence in paddle_rows:
            if evidence["classification"] not in stage_eval.RECOVERABLE:
                continue
            prediction = extracted.get((evidence["case_id"], evidence["field_name"]), {})
            if prediction.get("status") in ("exact_match", "normalized_match"):
                continue
            rows.append({
                "case_id": evidence["case_id"],
                "document_id": evidence["document_id"],
                "document_type": evidence["document_type"],
                "field_name": evidence["field_name"],
                "field_base": evidence["field_base"],
                "gt_value": evidence["gt_value"],
                "ocr_classification": evidence["classification"],
                "closest_ocr_text": evidence["closest_ocr_text"],
                "combined_ocr_text": evidence["combined_ocr_text"],
                "neighboring_ocr_texts": evidence["neighboring_ocr_texts"],
                "fuzzy_similarity": evidence["fuzzy_similarity"],
                "fuzzy_cer": evidence["fuzzy_cer"],
                "extractor_status": prediction.get("status", "missing"),
                "extractor_value": prediction.get("predicted_value", ""),
                "extractor_source_text": prediction.get("source_text", ""),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--paddle-cases", type=Path, required=True)
    parser.add_argument("--field-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, default=None, help="Root containing <case_id>/semantic_gold_fields.json")
    args = parser.parse_args()
    counts = Counter()
    rows = audit(args.cases, args.paddle_cases, args.field_results, args.gold_root)
    counts.update(row["field_base"] for row in rows)
    # Re-sort after counting; the first pass only establishes the row set.
    rows.sort(key=lambda row: (-counts[row["field_base"]], str(row["field_base"]), str(row["case_id"]), str(row["field_name"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["case_id"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"RECOVERABLE_BUT_EXTRACTOR_NOT_CORRECT={len(rows)}")
    for field, count in counts.most_common():
        print(f"{field}\t{count}")
    print(f"OUTPUT={args.output}")


if __name__ == "__main__":
    main()
