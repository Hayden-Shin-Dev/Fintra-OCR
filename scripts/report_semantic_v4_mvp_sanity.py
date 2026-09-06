"""Summarize the prediction-blind semantic-v4 MVP sanity review.

This report reads only v4 Gold, its image/TL audit, and the preserved known
defect review.  It deliberately does not open OCR, extractor, or final
holdout artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CORE_FIELDS = {
    "Commercial Invoice": [
        "invoice_number", "invoice_date", "seller", "buyer", "currency", "total_amount",
        "items[0].description", "items[0].quantity", "items[0].unit", "items[0].unit_price", "items[0].amount",
    ],
    "Packing List": [
        "packing_list_number", "date", "exporter", "consignee", "items[0].description", "items[0].quantity",
        "items[0].unit", "package_count", "gross_weight", "net_weight", "weight_unit",
    ],
    "B/L": [
        "bl_number", "shipper", "consignee", "notify_party", "vessel", "port_of_loading",
        "port_of_discharge", "shipment_date", "package_count", "gross_weight", "weight_unit", "goods_description",
    ],
}


def field_family(name: str) -> str:
    return re.sub(r"items\[\d+\]", "items[*]", name)


def load_fields(root: Path, allowlist: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case_id in [line.strip() for line in allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]:
        case = root / case_id
        manifest = json.loads((case / "case_manifest.json").read_text(encoding="utf-8"))
        for field in json.loads((case / "semantic_gold_fields.json").read_text(encoding="utf-8")):
            records.append({"case_id": case_id, "document_type": manifest["document_type"], **field})
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--audit-metrics", type=Path, required=True)
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--known-defects", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fast-gold-metrics", type=Path)
    parser.add_argument("--fast-audit-metrics", type=Path)
    parser.add_argument("--image-reviewed-case", action="append", default=[])
    args = parser.parse_args()

    fields = load_fields(args.gold_root, args.allowlist)
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    for field in fields:
        by_type[field["document_type"]][field.get("status", "missing")] += 1
        by_family[f"{field['document_type']}:{field_family(field['field_name'])}"][field.get("status", "missing")] += 1

    audit = json.loads(args.audit_metrics.read_text(encoding="utf-8"))
    audit_rows = list(csv.DictReader(args.audit_csv.open(encoding="utf-8-sig", newline="")))
    # The semantic audit intentionally emits CANNOT_VERIFY for ambiguous Gold
    # rows.  MVP readiness is about the available subset, so do not turn an
    # excluded ambiguous row into an available-field failure.
    available_audit_rows = [row for row in audit_rows if row.get("gold_status") == "available"]
    audit_status = Counter(row.get("semantic_status") for row in available_audit_rows)
    known = json.loads(args.known_defects.read_text(encoding="utf-8"))["records"]
    field_map = {(row["case_id"], row["field_name"]): row for row in fields}
    known_rows = []
    for record in known:
        key = (record["case_id"], record["field_name"])
        current = field_map.get(key)
        reviewed = record["new_gold"].get("value")
        if current is None:
            status = "MISSING"
        elif current.get("status") == "ambiguous_gt":
            status = "CONSERVATIVE_AMBIGUOUS"
        elif current.get("status") == "available" and current.get("value") == reviewed:
            status = "VERIFIED_CORRECT"
        else:
            status = "VALUE_MISMATCH"
        known_rows.append({
            "case_id": record["case_id"], "field_name": record["field_name"],
            "reviewed_value": reviewed, "v4_status": current.get("status") if current else "missing",
            "v4_value": current.get("value") if current else None, "resolution": status,
        })

    image_cases = []
    allowlisted = set(line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip())
    for case_id in args.image_reviewed_case:
        if case_id not in allowlisted:
            raise ValueError(f"image sanity case is outside Accurate75 allowlist: {case_id}")
        image_cases.append(case_id)

    available = sum(counter["available"] for counter in by_type.values())
    ambiguous = sum(counter["ambiguous_gt"] for counter in by_type.values())
    not_applicable = sum(counter["not_applicable"] for counter in by_type.values())
    core_counts: dict[str, dict[str, int]] = {}
    all_ambiguous_core: list[str] = []
    for doc_type, names in CORE_FIELDS.items():
        for requested in names:
            family = field_family(requested)
            counter = by_family.get(f"{doc_type}:{family}", Counter())
            key = f"{doc_type}:{family}"
            core_counts[key] = dict(counter)
            if counter and counter["available"] == 0 and counter["not_applicable"] == 0:
                all_ambiguous_core.append(key)

    known_counts = Counter(row["resolution"] for row in known_rows)
    evaluator_input_contract = all(
        field.get("status") != "available"
        or bool(field.get("value"))
        and bool(field.get("source_token_indices"))
        and bool(field.get("bbox"))
        for field in fields
    )
    fast_audit = json.loads(args.fast_audit_metrics.read_text(encoding="utf-8")) if args.fast_audit_metrics else {}
    fast_gold = json.loads(args.fast_gold_metrics.read_text(encoding="utf-8")) if args.fast_gold_metrics else {}
    fast_sanity_pass = bool(
        not args.fast_audit_metrics
        or (fast_audit.get("gold_freeze_ready")
            and fast_audit.get("row_cannot_verify") == 0
            and fast_audit.get("semantic_classification", {}).get("VERIFIED_CORRECT", 0) == fast_audit.get("available_fields"))
    )
    # Unsupported field families are an explicit MVP scope decision.  They
    # remain ambiguous_gt and do not block this development benchmark.
    mvp_ready = bool(
        audit.get("gold_freeze_ready")
        and audit_status["VERIFIED_ERROR"] == 0
        and audit_status["CANNOT_VERIFY"] == 0
        and all(by_type[doc_type]["available"] > 0 for doc_type in CORE_FIELDS)
        and known_counts["VALUE_MISMATCH"] == 0
        and known_counts["MISSING"] == 0
        and evaluator_input_contract
        and fast_sanity_pass
    )

    supported = sorted(key for key, counter in by_family.items() if counter["available"] > 0)
    unsupported = sorted(key for key, counter in by_family.items() if counter["available"] == 0 and counter["ambiguous_gt"] > 0 and counter["not_applicable"] == 0)

    report = {
        "gold_name": "MVP_DEVELOPMENT_GOLD_V4",
        "scope": "development benchmark over semantically verified available fields; ambiguous_gt is excluded",
        "accurate75": {"available": available, "ambiguous": ambiguous, "not_applicable": not_applicable, "total_fields": len(fields)},
        "by_document_type": {key: dict(value) for key, value in sorted(by_type.items())},
        "core_field_status": core_counts,
        "core_fields_all_ambiguous": all_ambiguous_core,
        "supported_field_families": supported,
        "unsupported_in_mvp_gold": unsupported,
        "image_sanity_checked_cases": image_cases,
        "image_sanity_checked_case_count": len(image_cases),
        "known_defects": {"count": len(known_rows), "resolution_counts": dict(known_counts), "records": known_rows},
        "audit": {"gold_freeze_ready": audit.get("gold_freeze_ready"), "available_field_semantic_status_counts": dict(audit_status), "row_cannot_verify": audit.get("row_cannot_verify"), "prediction_blind": audit.get("prediction_blind"), "ocr_read": audit.get("ocr_read"), "extractor_read": audit.get("extractor_read"), "final_holdout_2_accessed": audit.get("final_holdout_2_accessed")},
        "evaluator_input_contract": evaluator_input_contract,
        "fast300_sanity_pass": fast_sanity_pass,
        "mvp_gold_sanity_ready": mvp_ready,
    }
    if args.fast_gold_metrics:
        report["fast300_gold_metrics"] = fast_gold
    if args.fast_audit_metrics:
        report["fast300_audit_metrics"] = fast_audit
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
