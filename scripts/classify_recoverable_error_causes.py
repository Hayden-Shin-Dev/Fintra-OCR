"""Classify frozen-OCR recoverable extractor errors without tuning code."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def classify(row: dict[str, str]) -> tuple[str, str]:
    field = row.get("field_name", "")
    predicted = row.get("extractor_value", "").strip()
    expected = row.get("gt_value", "").strip()
    if predicted and expected and _compact(predicted) == _compact(expected):
        return "NORMALIZATION_ERROR", "prediction and gold differ only by separators/case"
    if row.get("extractor_status") == "missing" or not predicted:
        if "items[" in field:
            return "ROW_SELECTION_ERROR", "recoverable field evidence exists but no item value was emitted"
        return "CANDIDATE_GENERATION_ERROR", "recoverable field evidence exists but no scalar value was emitted"
    source = _compact(row.get("extractor_source_text", ""))
    neighbors = [_compact(value) for value in row.get("neighboring_ocr_texts", "").split(" || ") if value.strip()]
    if source and source in neighbors:
        if "items[" in field:
            return "ROW_SELECTION_ERROR", "selected item text is an OCR candidate in the field neighborhood"
        return "CANDIDATE_RANKING_ERROR", "selected text is an OCR candidate but not the gold value"
    return "CANDIDATE_GENERATION_ERROR", "selected text is not present in the field OCR neighborhood"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--failure-matrix", type=Path, action="append", default=[],
                        help="Three-way failure matrix; only EXTRACTOR_WRONG rows are subtype-counted")
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    extractor_wrong_keys: set[tuple[str, str]] | None = None
    if args.failure_matrix:
        extractor_wrong_keys = set()
        for matrix_path in args.failure_matrix:
            with matrix_path.open(encoding="utf-8-sig", newline="") as handle:
                for matrix_row in csv.DictReader(handle):
                    if matrix_row.get("classification") == "EXTRACTOR_WRONG":
                        extractor_wrong_keys.add((matrix_row["case_id"], matrix_row["field_name"]))
    counts = Counter()
    by_type: dict[str, Counter] = defaultdict(Counter)
    by_field: dict[str, Counter] = defaultdict(Counter)
    output = []
    for row in rows:
        if extractor_wrong_keys is not None and (row["case_id"], row["field_name"]) not in extractor_wrong_keys:
            continue
        cause, reason = classify(row)
        counts[cause] += 1
        by_type[row["document_type"]][cause] += 1
        by_field[f'{row["document_type"]}:{row["field_base"]}'][cause] += 1
        output.append({**row, "error_cause": cause, "cause_reason": reason})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output[0]) if output else ["case_id"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    metrics = {
        "input_rows": len(rows),
        "cause_counts": dict(counts),
        "by_document_type": {key: dict(value) for key, value in sorted(by_type.items())},
        "by_field": {key: dict(value) for key, value in sorted(by_field.items())},
        "contract": "Diagnostic only; frozen Accurate75 OCR, extractor, and semantic-v3.1 gold are unchanged.",
    }
    metrics_path = args.output.with_name("error_cause_metrics.json")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False))
    print(f"OUTPUT={args.output}")
    print(f"METRICS={metrics_path}")


if __name__ == "__main__":
    main()
