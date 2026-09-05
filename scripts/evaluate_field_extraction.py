"""Evaluate Fintra field extraction against prepared evidence-based gold."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import struct
from dataclasses import replace
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from decimal import Decimal
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fintra.extraction.documents import extract_bill_of_lading, extract_commercial_invoice, extract_packing_list
from fintra.extraction.documents import extract_bill_of_lading_legacy, extract_commercial_invoice_legacy, extract_packing_list_legacy
from fintra.normalization.values import normalize_company, normalize_currency, normalize_date, parse_amount
from fintra.ocr.adapter import OCRResult


def _status(value: Any) -> str:
    return getattr(value, "value", value)


def _field_kind(name: str) -> str:
    if any(token in name for token in ("seller", "buyer", "exporter", "consignee", "shipper", "notify_party")):
        return "company"
    if "currency" in name:
        return "currency"
    if "date" in name:
        return "date"
    if name.endswith("unit"):
        return "unit"
    if any(token in name for token in ("amount", "quantity", "package_count", "unit_price", "weight")):
        return "number"
    return "text"


def normalize_field(value: Any, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    # The Modern recognition writer escapes commas so that official TXT rows
    # remain comma-delimited. Restore that serialization escape for semantic
    # field comparison; raw output remains unchanged on disk.
    value = str(value).replace("쉼표", ",")
    kind = _field_kind(field_name)
    if kind == "company":
        return normalize_company(value)
    if kind == "currency":
        return normalize_currency(value)
    if kind == "date":
        return normalize_date(value)
    if kind == "number":
        number = parse_amount(value)
        return format(number, "f") if number is not None else None
    if kind == "unit":
        unit = unicodedata.normalize("NFKC", str(value)).strip().upper()
        return {"KGS": "KG", "KILOGRAM": "KG", "KILOGRAMS": "KG", "GRAM": "G", "GRAMS": "G"}.get(unit, unit)
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()


def _document_payload(result: OCRResult, strategy: str = "active") -> dict[str, Any]:
    legacy={"Commercial Invoice":extract_commercial_invoice_legacy,"Packing List":extract_packing_list_legacy,"B/L":extract_bill_of_lading_legacy}
    if strategy=="legacy":return legacy[result.document_type](result).to_dict()
    if strategy == "layout":
        from fintra.extraction.strategies import STRATEGIES
        return STRATEGIES[result.document_type](result).extract().to_dict()
    if strategy in ("typed", "ordered", "table"):
        from fintra.extraction.refinement import typed_refinement, ordered_refinement, table_refinement
        functions=legacy
        doc=typed_refinement(result,functions[result.document_type](result))
        if strategy=="ordered":doc=ordered_refinement(result,doc)
        if strategy=="table":doc=table_refinement(result,doc,strategy)
        return doc.to_dict()
    if result.document_type == "Commercial Invoice":
        return extract_commercial_invoice(result).to_dict()
    if result.document_type == "Packing List":
        return extract_packing_list(result).to_dict()
    if result.document_type == "B/L":
        return extract_bill_of_lading(result).to_dict()
    raise ValueError(f"unsupported document type: {result.document_type}")


def compare_field(predicted: Any, gold: Any, field_name: str) -> str:
    """Only successful normalization can establish equality."""
    if predicted == gold:
        return "exact_match"
    left, right = normalize_field(predicted, field_name), normalize_field(gold, field_name)
    if _field_kind(field_name) == "number" and left is not None and right is not None:
        return "normalized_match" if Decimal(left) == Decimal(right) else "wrong"
    if left is not None and right is not None and left == right:
        return "normalized_match"
    return "wrong"


def _predicted_field(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    match = re.match(r"items\[(\d+)\]\.(\w+)$", field_name)
    if match:
        items = payload.get("items", [])
        index = int(match.group(1))
        return items[index].get(match.group(2), {}) if index < len(items) else {"status": "missing"}
    return payload.get(field_name, {"status": "missing"})


def _case_prediction(case_dir: Path) -> OCRResult | None:
    candidates = sorted((case_dir / "outputs" / "recognition").glob("*.json"))
    if not candidates:
        return None
    manifest = json.loads((case_dir / "case_manifest.json").read_text(encoding="utf-8"))
    result=OCRResult.from_json(candidates[0], document_type=manifest["document_type"])
    image=case_dir / manifest.get("image", "")
    if image.is_file():
        with image.open('rb') as handle:
            header=handle.read(24)
        if header[:8]==b'\x89PNG\r\n\x1a\n':
            width,height=struct.unpack('>II',header[16:24])
            result=replace(result,source_file=str(image),metadata={**result.metadata,'page_width':width,'page_height':height})
    return result


def _bbox_string(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value is not None else ""


def evaluate(cases_root: Path, output_dir: Path, strategy: str = "active") -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        gold = manifest.get("gold_fields", [])
        prediction = _case_prediction(case_dir)
        predicted_payload = _document_payload(prediction,strategy) if prediction else {}
        for gold_field in gold:
            gt_status = gold_field["status"]
            predicted = _predicted_field(predicted_payload, gold_field["field_name"])
            prediction_status = _status(predicted.get("status", "missing"))
            predicted_value = predicted.get("value")
            if gt_status == "not_applicable":
                result_status = "not_applicable"
            elif gt_status == "ambiguous_gt":
                result_status = "ambiguous"
            elif prediction_status == "ambiguous":
                result_status = "ambiguous"
            elif prediction_status != "extracted" or predicted_value in (None, ""):
                result_status = "missing"
            else:
                result_status = compare_field(predicted_value, gold_field.get("value"), gold_field["field_name"])
            rows.append({
                "document_id": manifest["document_id"], "document_type": manifest["document_type"],
                "case_id": manifest["case_id"], "field_name": gold_field["field_name"],
                "gt_status": gt_status, "gt_value": gold_field.get("value"),
                "predicted_value": predicted_value if prediction_status == "extracted" else None,
                "normalized_gt": normalize_field(gold_field.get("value"), gold_field["field_name"]),
                "normalized_prediction": normalize_field(predicted_value, gold_field["field_name"]),
                "status": result_status, "confidence": predicted.get("confidence"),
                "source_text": predicted.get("source_text"), "bbox": _bbox_string(predicted.get("bbox")),
            })

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "field_results.csv"
    fields = ["document_id", "document_type", "case_id", "field_name", "gt_status", "gt_value", "predicted_value", "normalized_gt", "normalized_prediction", "status", "confidence", "source_text", "bbox"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    def metric(subset: list[dict[str, Any]]) -> dict[str, Any]:
        applicable = [row for row in subset if row["gt_status"] == "available"]
        counts = Counter(row["status"] for row in subset)
        ambiguous_gt = sum(row["gt_status"] == "ambiguous_gt" for row in subset)
        predicted_ambiguous = max(counts["ambiguous"] - ambiguous_gt, 0)
        exact = counts["exact_match"]
        normalized = exact + counts["normalized_match"]
        denominator = len(applicable)
        return {
            "rows": len(subset), "applicable_gold": denominator,
            "ambiguous_gt": ambiguous_gt, "not_applicable": counts["not_applicable"],
            "exact_matches": exact, "normalized_matches": normalized,
            "exact_field_accuracy": exact / denominator if denominator else 0.0,
            "normalized_field_accuracy": normalized / denominator if denominator else 0.0,
            "wrong": counts["wrong"], "missing": counts["missing"], "ambiguous": predicted_ambiguous,
            "wrong_extraction_rate": counts["wrong"] / denominator if denominator else 0.0,
            "missing_rate": counts["missing"] / denominator if denominator else 0.0,
            "ambiguous_rate": predicted_ambiguous / denominator if denominator else 0.0,
            "status_counts": dict(counts),
        }

    by_type = {kind: metric([row for row in rows if row["document_type"] == kind]) for kind in ("Commercial Invoice", "Packing List", "B/L")}
    by_field = {f"{kind}:{field}": metric([row for row in rows if row["document_type"] == kind and row["field_name"] == field]) for kind, field in sorted({(row["document_type"], row["field_name"]) for row in rows})}
    applicable_fields = [item for key, item in by_field.items() if item["applicable_gold"]]
    worst = sorted(((key, value["normalized_field_accuracy"], value["applicable_gold"]) for key, value in by_field.items() if value["applicable_gold"]), key=lambda item: (item[1], -item[2]))[:10]
    result = {
        "schema_version": "fintra-ocr-v2.field-extraction-evaluation.v1",
        "strategy": strategy,
        "score_contract": "non-null-normalization-v2; fixed available-gold denominator",
        "gold_validity": "UNREVIEWED_LEGACY_TEMPLATE_GOLD; not a validated semantic accuracy claim",
        "selection": {"documents": len({row["case_id"] for row in rows}), "rows": len(rows)},
        "overall": metric(rows), "by_document_type": by_type, "by_field": by_field,
        "weakest_fields": [{"field": key, "normalized_accuracy": accuracy, "applicable_gold": count} for key, accuracy, count in worst],
        "gold_policy": "Only explicit values in AI-Hub word annotations inside inspected template zones are available gold; ambiguous_gt and not_applicable are excluded from accuracy denominator.",
    }
    (output_dir / "field_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    examples = {status: [row for row in rows if row["status"] == status][:20] for status in ("wrong", "missing", "ambiguous")}
    lines = ["# Fintra field extraction evaluation", "", f"Documents: {result['selection']['documents']} (CI/PL/B-L selected by the preparation manifest)", "", "## Overall", "", f"- Exact Field Accuracy: {result['overall']['exact_field_accuracy']:.6f}", f"- Normalized Field Accuracy: {result['overall']['normalized_field_accuracy']:.6f}", f"- Wrong Extraction Rate: {result['overall']['wrong_extraction_rate']:.6f}", f"- Missing Rate: {result['overall']['missing_rate']:.6f}", f"- Ambiguous Rate: {result['overall']['ambiguous_rate']:.6f}", f"- Applicable gold fields: {result['overall']['applicable_gold']}", "", "## By document type", "", "| Type | Exact | Normalized | Wrong | Missing | Ambiguous | Applicable |", "|---|---:|---:|---:|---:|---:|---:|"]
    for kind, item in by_type.items():
        lines.append(f"| {kind} | {item['exact_field_accuracy']:.6f} | {item['normalized_field_accuracy']:.6f} | {item['wrong_extraction_rate']:.6f} | {item['missing_rate']:.6f} | {item['ambiguous_rate']:.6f} | {item['applicable_gold']} |")
    lines += ["", "## Weakest fields", ""]
    lines += [f"- `{key}`: normalized accuracy {accuracy:.6f} over {count} applicable gold rows" for key, accuracy, count in worst]
    lines += ["", "## Examples", ""]
    for status, status_rows in examples.items():
        lines += [f"### {status}", ""]
        for row in status_rows:
            lines.append(f"- `{row['document_id']}` `{row['field_name']}`: GT={row['gt_value']!r}; prediction={row['predicted_value']!r}; source={row['source_text']!r}")
        lines.append("")
    lines += ["## Gold and normalization policy", "", result["gold_policy"], "Normalization changes representation only: company case/punctuation/whitespace, ISO dates, Decimal numbers, known currency codes, and unit case. Semantic substitutions are not performed.", "", "The report is not valid until the 60-case Modern OCR prediction outputs exist under each case's `outputs/recognition/` directory."]
    (output_dir / "FIELD_EXTRACTION_EVALUATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--strategy", choices=("active", "legacy", "layout", "typed", "ordered", "table"), default="active")
    args = parser.parse_args()
    result = evaluate(args.cases, args.output_dir, args.strategy)
    print(json.dumps({"documents": result["selection"]["documents"], "applicable_gold": result["overall"]["applicable_gold"]}, ensure_ascii=False))
    print(f"FIELD_RESULTS={args.output_dir / 'field_results.csv'}")
    print(f"FIELD_METRICS={args.output_dir / 'field_metrics.json'}")


if __name__ == "__main__":
    main()
