"""Classify frozen stage rows into actionable extractor failure stages."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def _field_base(field: str) -> str:
    return field.split(".")[-1] if "." in field else field


def classify(row: dict[str, str]) -> str:
    if str(row.get("raw_ocr_recoverable", "")).lower() != "true":
        return "OCR_UNRECOVERABLE"
    field = row.get("field_name", "")
    predicted = row.get("predicted_value", "").strip()
    source = row.get("extractor_source_text", "").strip()
    if row.get("extractor_correct", "").lower() == "true":
        return "NONE"
    if not predicted or not source:
        return "CANDIDATE_GENERATION_FAILURE"
    if field.startswith("items["):
        base = _field_base(field)
        if base == "description":
            return "DESCRIPTION_CONTAMINATION"
        return "COLUMN_MAPPING_FAILURE"
    if _field_base(field) in {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party"}:
        return "ROLE_ASSIGNMENT_FAILURE"
    if row.get("candidate_hit", "").lower() != "true":
        return "CANDIDATE_GENERATION_FAILURE"
    if field.endswith("date") or field.endswith("number") or _field_base(field) in {
        "currency", "total_amount", "package_count", "gross_weight", "net_weight", "weight_unit"
    }:
        return "NORMALIZATION_FAILURE"
    return "CANDIDATE_RANKING_FAILURE"


def run(inputs: list[Path], output: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    for path in inputs:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                row["failure_stage"] = classify(row)
                rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "failure_stage_results.csv"
    fields = list(rows[0]) if rows else ["failure_stage"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row["failure_stage"] for row in rows)
    by_type: dict[str, Counter] = defaultdict(Counter)
    by_field: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        by_type[row.get("document_type", "unknown")][row["failure_stage"]] += 1
        by_field[f"{row.get('document_type', 'unknown')}:{row.get('field_name', '')}"][row["failure_stage"]] += 1
    payload = {
        "inputs": [str(path) for path in inputs],
        "rows": len(rows),
        "counts": dict(sorted(counts.items())),
        "by_document_type": {key: dict(sorted(value.items())) for key, value in sorted(by_type.items())},
        "by_field": {key: dict(sorted(value.items())) for key, value in sorted(by_field.items())},
        "classification_is_diagnostic": True,
    }
    (output / "failure_stage_metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
