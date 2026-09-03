"""Evaluate explicit Commercial Invoice seller extraction using reconstructed sample GT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintra_ocr.field_evaluation import _prediction_list, load_prediction_rows
from fintra_ocr.common_schema import document_type_from_form_type
from fintra_ocr.field_extraction import extract_fields
from fintra_ocr.label_bbox import parse_bounding_boxes
from fintra_ocr.normalization import normalize_fields
from fintra_ocr.oracle_validation import (
    _agreement_threshold,
    _field_agreement,
    _semantic_value_valid,
    build_oracle_document,
)
from fintra_ocr.sample_dataset import iter_target_documents


def _box(bbox: object) -> object:
    if bbox is None:
        return None
    return [[int(x), int(y)] for x, y in bbox]  # type: ignore[misc]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--sample-zip", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_prediction_rows(args.input_dir)
    samples = {sample.document_id: sample for sample in iter_target_documents(args.sample_zip, paired_only=True)}
    results: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: str(item["document_id"])):
        if document_type_from_form_type(str(row["form_type"])) != "commercial_invoice":
            continue
        document_id = str(row["document_id"])
        predictions = _prediction_list(row)
        sample = samples.get(document_id)
        if sample is None:
            continue
        oracle = build_oracle_document(
            str(row["form_type"]), document_id, predictions,
            parse_bounding_boxes(sample.label),
        )["fields"]["seller"]
        actual = normalize_fields(extract_fields(str(row["form_type"]), predictions))["seller"]
        expected = oracle.get("normalized") if oracle.get("normalized") is not None else oracle.get("value")
        available = (
            str(oracle.get("status")) == "found"
            and _semantic_value_valid("seller", expected)
        )
        if not available:
            outcome = "manual_review"
        elif actual.status == "ambiguous":
            outcome = "ambiguous"
        elif actual.status == "missing":
            outcome = "missing"
        elif _field_agreement("seller", actual.normalized, expected) >= _agreement_threshold("seller"):
            outcome = "correct"
        else:
            outcome = "wrong"
        results.append({
            "document_id": document_id,
            "document_type": "commercial_invoice",
            "field": "seller",
            "evaluation_available": available,
            "oracle_proxy": True,
            "expected_value": expected,
            "expected_raw_text": oracle.get("raw_text"),
            "expected_bbox": _box(oracle.get("bbox")),
            "extractor_status": actual.status,
            "extractor_output": actual.value,
            "extractor_normalized": actual.normalized,
            "extractor_raw_text": actual.raw_text,
            "extractor_bbox": _box(actual.bbox),
            "extractor_source_indices": list(actual.source_indices),
            "outcome": outcome,
            "reason": actual.reason,
        })
    counts: dict[str, int] = {}
    for item in results:
        counts[str(item["outcome"])] = counts.get(str(item["outcome"]), 0) + 1
    report = {
        "evaluation": "explicit_seller_field_regression",
        "note": "Expected values are reconstructed from lightweight GT value boxes plus static OCR; unavailable/non-semantic cases are manual_review and are excluded from accuracy.",
        "document_count": len(results),
        "available_count": sum(1 for item in results if item["evaluation_available"]),
        "outcome_counts": counts,
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"documents": len(results), "available": report["available_count"], "outcomes": counts, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
