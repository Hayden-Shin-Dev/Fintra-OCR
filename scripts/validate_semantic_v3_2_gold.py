"""Validate the prediction-blind semantic-v3.2 Gold candidate.

This validator consumes only source annotations and generated Gold.  It does
not read OCR output, extractor output, or FINAL-HOLDOUT #2.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


UNIT_WORDS = {
    "KG", "KGS", "G", "GRAM", "GRAMS", "PC", "PCS", "EA", "EACH", "PKG",
    "BOX", "CTN", "SET", "UNIT", "POUND", "YARD", "INCH", "DRUM", "BAG",
    "PIECE", "ST", "SF", "CT",
}
TRANSPORT_TERMS = {"FOB", "CIF", "CFR", "DAF", "DDP", "DDU", "DEQ", "CFS", "CY"}
NUMERIC = re.compile(r"^[+$-]?\s*\d[\d,./() +:-]*(?:[A-Za-z]+)?$")
DATE = re.compile(r"\d{1,4}[-/]?[A-Za-z]{3,9}[-/]?\d{1,4}|[A-Za-z]{3,9}\s+\d{1,2}[, ]+\d{4}|\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", re.I)


def token_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result.append({"index": index, "text": str(item.get("data") or "").strip(), "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return result


def field_items(field: dict[str, Any], tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_index = {item["index"]: item for item in tokens}
    return [by_index[index] for index in field.get("source_token_indices", []) if index in by_index]


def add_issue(issues: list[dict[str, Any]], case_id: str, field: dict[str, Any], code: str, reason: str) -> None:
    issues.append({
        "case_id": case_id,
        "document_type": "",
        "field_name": field["field_name"],
        "current_value": field.get("value"),
        "invariant_failed": code,
        "source_token_indices": json.dumps(field.get("source_token_indices", [])),
        "reason": reason,
    })


def validate_case(case_dir: Path) -> tuple[list[dict[str, Any]], str]:
    manifest = json.loads((case_dir / "case_manifest.json").read_text(encoding="utf-8"))
    fields = json.loads((case_dir / "semantic_gold_fields.json").read_text(encoding="utf-8"))
    payload = json.loads((Path("artifacts/fintra/train-scale-v1/cases") / case_dir.name / "source_annotation.json").read_text(encoding="utf-8"))
    tokens = token_list(payload)
    issues: list[dict[str, Any]] = []
    for field in fields:
        field["_document_type"] = manifest["document_type"]
        if field.get("status") != "available":
            continue
        items = field_items(field, tokens)
        value = str(field.get("value") or "").strip()
        source = " ".join(item["text"] for item in items)
        if not items:
            add_issue(issues, case_dir.name, field, "SOURCE_INDEX_MISSING", "available Gold has no resolvable source tokens")
            continue
        if source != value:
            add_issue(issues, case_dir.name, field, "VALUE_SOURCE_MISMATCH", f"Gold value {value!r} differs from source tokens {source!r}")
        name = field["field_name"]
        if name.endswith("description") or name == "goods_description":
            if not re.search(r"[A-Za-z]", value) or NUMERIC.fullmatch(value):
                add_issue(issues, case_dir.name, field, "DESCRIPTION_TYPE", "description must contain alphabetic text and must not be numeric-only")
        elif name.endswith("quantity") or name.endswith("unit_price") or name.endswith("amount") or name in {"total_amount", "gross_weight", "net_weight", "package_count"}:
            if not NUMERIC.fullmatch(value):
                add_issue(issues, case_dir.name, field, "NUMERIC_TYPE", "numeric field is not numeric/currency-compatible")
        elif name.endswith("unit"):
            # The invariant permits an explicit vocabulary OR an alphabetic
            # unit token; unknown alphabetic units remain semantically
            # reviewable but are not type-invalid.
            if not re.fullmatch(r"[A-Za-z]+", value):
                add_issue(issues, case_dir.name, field, "UNIT_TYPE", "unit is not an alphabetic known unit")
        elif "date" in name or name == "date":
            if not DATE.search(value):
                add_issue(issues, case_dir.name, field, "DATE_TYPE", "date is not parseable by the supported source format")
        if name == "vessel" and (value.upper() in TRANSPORT_TERMS or re.search(r"\bV\s*\.?\s*\d+\b", value.upper())):
            add_issue(issues, case_dir.name, field, "VESSEL_TRANSPORT_TERM", "vessel is an incoterm or voyage expression")
        if name in {"port_of_loading", "port_of_discharge"} and ("," not in value or value.upper() in TRANSPORT_TERMS):
            add_issue(issues, case_dir.name, field, "PORT_TYPE", "port is not a place-like city/country value")
    return issues, manifest["document_type"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-root", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3.2-accurate75/cases"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3.2-accurate75"))
    args = parser.parse_args()
    issues: list[dict[str, Any]] = []
    types = Counter()
    case_dirs = sorted(path for path in args.gold_root.iterdir() if path.is_dir())
    for case_dir in case_dirs:
        case_issues, document_type = validate_case(case_dir)
        types[document_type] += 1
        for issue in case_issues:
            issue["document_type"] = document_type
        issues.extend(case_issues)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "v3_2_invalid_gold.csv"
    columns = ["case_id", "document_type", "field_name", "current_value", "invariant_failed", "source_token_indices", "reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader(); writer.writerows(issues)
    summary = {
        "gold_root": str(args.gold_root),
        "cases": len(case_dirs),
        "document_types": dict(types),
        "invalid_fields": len(issues),
        "invalid_by_invariant": dict(Counter(issue["invariant_failed"] for issue in issues)),
        "prediction_blind": True,
        "final_holdout_2_accessed": False,
        "status": "PASS" if not issues else "FAIL",
    }
    (args.output_dir / "v3_2_validation_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
