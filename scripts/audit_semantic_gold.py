"""Audit semantic-v2 field gold without reading extractor predictions.

The AI-Hub source is word-level annotation rather than a Fintra field schema.
This audit therefore records the semantic anchor as unavailable when the label
is not present in the source annotation, and checks the selected value against
its relative section, reading order, and field-type constraints.  It never
reads OCR predictions and never changes a gold file.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_semantic_field_gold import HEIGHT, WIDTH
from fintra.normalization.values import normalize_date


COUNTRIES = {
    "ARGENTINA", "AUSTRALIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA",
    "DENMARK", "EGYPT", "ERITREA", "FINLAND", "FRANCE", "GERMANY", "GREECE",
    "HAITI", "INDIA", "IRELAND", "ISRAEL", "ITALY", "JAPAN", "KOREA", "MALAYSIA",
    "MEXICO", "NIGERIA", "NORWAY", "POLAND", "SOUTH AFRICA", "SPAIN", "TAIWAN",
    "THAILAND", "TURKEY", "UNITED KINGDOM", "UNITED STATES", "VIET NAM", "VIETNAM",
}
UNIT_WORDS = {"KG", "KGS", "G", "GRAM", "GRAMS", "PC", "PCS", "EA", "EACH", "PKG", "BOX", "CTN", "SET", "UNIT"}
LABEL_ALIASES = {
    "invoice_number": ("INVOICE", "INVOICE NO", "NO. & DATE OF INVOICE"),
    "invoice_date": ("DATE", "INVOICE DATE"),
    "seller": ("SELLER", "SHIPPER", "EXPORTER"),
    "buyer": ("BUYER", "CONSIGNEE"),
    "currency": ("CURRENCY", "USD", "EUR", "GBP", "JPY", "CNY", "KRW"),
    "total_amount": ("TOTAL", "TOTAL AMOUNT"),
    "exporter": ("EXPORTER", "SHIPPER"),
    "consignee": ("CONSIGNEE", "BUYER"),
    "date": ("DATE",),
    "package_count": ("PACKAGE", "PACKAGES", "PKGS", "PKG"),
    "gross_weight": ("GROSS", "GROSS WEIGHT"),
    "net_weight": ("NET", "NET WEIGHT"),
    "weight_unit": ("KG", "KGS"),
    "bl_number": ("B/L", "BL NO", "BILL OF LADING"),
    "shipper": ("SHIPPER", "EXPORTER"),
    "notify_party": ("NOTIFY", "NOTIFY PARTY"),
    "vessel": ("VESSEL", "CARRIER"),
    "port_of_loading": ("PORT OF LOADING", "LOADING"),
    "port_of_discharge": ("PORT OF DISCHARGE", "DISCHARGE"),
    "shipment_date": ("SHIPMENT", "ON BOARD", "DATE"),
    "goods_description": ("DESCRIPTION", "GOODS"),
}


def _tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result.append({
            "index": index,
            "text": str(item.get("data") or "").strip(),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
        })
    return result


def _base(field_name: str) -> str:
    return re.sub(r"^items\[\d+\]\.", "", field_name)


def _zone(field_name: str, document_type: str) -> tuple[float, float, float, float] | None:
    base = _base(field_name)
    if document_type == "Commercial Invoice":
        if base == "invoice_number": return (.51, .80, .10, .17)
        if base == "invoice_date": return (.51, .88, .14, .24)
        if base == "seller": return (.06, .52, .12, .24)
        if base == "buyer": return (.06, .52, .24, .34)
        if base == "total_amount": return (.72, .96, .62, .78)
        if field_name.startswith("items["):
            if base == "description": return (.07, .52, 1000 / HEIGHT, 1400 / HEIGHT)
            if base == "quantity": return (.49, .60, 1000 / HEIGHT, 1400 / HEIGHT)
            if base == "unit": return (.49, .67, 1000 / HEIGHT, 1400 / HEIGHT)
            if base == "unit_price": return (.67, .77, 1000 / HEIGHT, 1400 / HEIGHT)
            if base == "amount": return (.77, .92, 1000 / HEIGHT, 1400 / HEIGHT)
        return None
    if document_type == "Packing List":
        if base == "date": return (.69, .91, .07, .15)
        if base == "exporter": return (.06, .49, .12, .22)
        if base == "consignee": return (.06, .46, .21, .31)
        if field_name.startswith("items["):
            if base == "description": return (.07, .44, 1000 / HEIGHT, 1520 / HEIGHT)
            if base in {"quantity", "unit"}: return (.48, .60, 1000 / HEIGHT, 1520 / HEIGHT)
        if base == "package_count": return (.21, .40, .70, .79)
        if base == "gross_weight": return (.24, .43, .74, .81)
        return None
    if base == "bl_number": return (.70, .94, .115, .18)
    if base == "shipment_date": return (.70, .96, .07, .13)
    if base == "shipper": return (.04, .49, .12, .22)
    if base == "consignee": return (.04, .49, .21, .31)
    if base == "notify_party": return (.04, .49, .29, .39)
    if base == "vessel": return (.04, .27, .35, .43)
    if base == "port_of_loading": return (.27, .49, .35, .43)
    if base == "port_of_discharge": return (.04, .27, .40, .49)
    if base == "goods_description": return (.30, .69, .50, .65)
    if base in {"package_count", "gross_weight"}: return (.12, .79, .50, .70)
    return None


def _in_zone(token: dict[str, Any], zone: tuple[float, float, float, float]) -> bool:
    x1, x2, y1, y2 = zone
    bx = token["bbox"]
    return bx[0] >= x1 * WIDTH and bx[2] <= x2 * WIDTH and bx[1] >= y1 * HEIGHT and bx[3] <= y2 * HEIGHT


def _line_key(token: dict[str, Any]) -> tuple[float, float, int]:
    return ((token["bbox"][1] + token["bbox"][3]) / 2, token["bbox"][0], token["index"])


def _lines(items: Iterable[dict[str, Any]], tolerance: float = 18.0) -> list[list[dict[str, Any]]]:
    lines: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=_line_key):
        cy = (item["bbox"][1] + item["bbox"][3]) / 2
        if not lines:
            lines.append([item])
        else:
            previous = sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in lines[-1]) / len(lines[-1])
            if abs(cy - previous) <= tolerance:
                lines[-1].append(item)
            else:
                lines.append([item])
    return [sorted(line, key=lambda x: (x["bbox"][0], x["index"])) for line in lines]


def _text(items: Iterable[dict[str, Any]]) -> str:
    return " ".join(x["text"] for x in sorted(items, key=_line_key) if x["text"])


def _norm_label(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _anchor(tokens: list[dict[str, Any]], field_name: str, zone: tuple[float, float, float, float] | None) -> tuple[str, str]:
    aliases = LABEL_ALIASES.get(_base(field_name), ())
    for token in tokens:
        normalized = _norm_label(token["text"])
        if normalized in {_norm_label(alias) for alias in aliases}:
            return token["text"], json.dumps(token["bbox"], ensure_ascii=False)
    if zone:
        return "UNANNOTATED_LABEL|aliases=" + ",".join(aliases), f"relative:{zone}"
    return "UNANNOTATED_LABEL", "unknown"


def _is_phone(text: str) -> bool:
    return bool(re.search(r"(?:TEL|FAX|\+?\d)[^A-Za-z]{0,4}\d", text.upper())) and len(re.findall(r"\d", text)) >= 5


def _is_address(text: str) -> bool:
    upper = text.upper()
    return bool(re.search(r"\b(?:STREET|ST\.|ROAD|RD\.|AVENUE|AVE\.|CITY|DISTRICT|KOREA|JAPAN|CHINA|TAIWAN|USA|UNITED STATES|QLD|AK|ZIP|REP\.)\b", upper)) or bool(re.search(r"\b\d{4,6}\b", text))


def _is_country_only(text: str) -> bool:
    return _norm_label(text) in {_norm_label(x) for x in COUNTRIES}


def _is_port_identifier(text: str) -> bool:
    compact = re.sub(r"[^A-Z0-9]", "", text.upper())
    return bool(re.fullmatch(r"(?:DLSU\d+|[BU]\d{4,}|U\d+|D\d+)", compact))


def _is_unit(text: str) -> bool:
    return _norm_label(text) in UNIT_WORDS


def _is_number(text: str) -> bool:
    return bool(re.search(r"\d", text)) and bool(re.fullmatch(r"[\s$€£¥₩A-Z0-9,./()+:-]+", text, re.I))


def _is_date(text: str) -> bool:
    return normalize_date(text) is not None


def _type_reason(field_name: str, value: str, document_type: str) -> list[str]:
    base = _base(field_name)
    reasons: list[str] = []
    if base in {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party"}:
        if _is_phone(value): reasons.append("party_value_is_phone_or_fax")
        if _is_country_only(value): reasons.append("party_value_is_country_only")
        if _is_address(value) and not re.search(r"\b(?:INC|LTD|CO|CORP|CORPORATION|COMPANY|LLC)\b", value.upper()): reasons.append("party_value_is_address_or_postal_text")
    if base in {"port_of_loading", "port_of_discharge"} and _is_port_identifier(value):
        reasons.append("port_value_is_container_or_booking_identifier")
    if base == "unit" and not _is_unit(value):
        reasons.append("unit_value_is_not_a_known_unit")
    if base in {"date", "invoice_date", "shipment_date", "on_board_date"} and not _is_date(value):
        reasons.append("date_value_fails_date_type_constraint")
    if base in {"quantity", "package_count"} and not _is_number(value):
        reasons.append("quantity_value_fails_numeric_constraint")
    if base in {"amount", "unit_price", "total_amount", "gross_weight", "net_weight"} and not _is_number(value):
        reasons.append("numeric_value_fails_numeric_constraint")
    if base == "weight_unit" and not _is_unit(value):
        reasons.append("weight_unit_is_not_a_known_unit")
    if base == "bl_number" and _is_date(value):
        reasons.append("B/L_identifier_is_date_typed_value")
    return reasons


def _structural_reasons(field: dict[str, Any], value_tokens: list[dict[str, Any]], all_tokens: list[dict[str, Any]], document_type: str) -> list[str]:
    field_name = field["field_name"]
    base = _base(field_name)
    reasons: list[str] = []
    zone = _zone(field_name, document_type)
    if not zone or not value_tokens:
        return reasons
    candidates = [token for token in all_tokens if _in_zone(token, zone)]
    lines = _lines(candidates)
    current_y = min(token["bbox"][1] for token in value_tokens)
    current_line = next((i for i, line in enumerate(lines) if any(x["index"] in {t["index"] for t in value_tokens} for x in line)), -1)
    if document_type == "B/L" and base == "port_of_discharge":
        place_lines = [i for i, line in enumerate(lines) if "," in _text(line) and not _is_port_identifier(_text(line))]
        if place_lines and current_line != min(place_lines):
            reasons.append("selected_later_same_column_place_after_earlier_port_candidate")
    if document_type == "B/L" and base == "vessel":
        plausible = [i for i, line in enumerate(lines) if not _is_port_identifier(_text(line)) and not _is_country_only(_text(line)) and not _is_phone(_text(line)) and not "," in _text(line)]
        if plausible and current_line != min(plausible):
            reasons.append("selected_later_vessel_line_after_earlier_candidate")
    if base == "notify_party" and any(_is_phone(_text(line)) or _is_address(_text(line)) for line in lines[:1]):
        if any(re.search(r"[A-Za-z]{3,}", _text(line)) and not _is_address(_text(line)) and not _is_phone(_text(line)) for line in lines[1:]):
            reasons.append("party_selection_starts_in_address_or_phone_line_before_party_candidate")
    if base in {"seller", "buyer", "exporter", "consignee", "shipper"} and (_is_address(field.get("value") or "") or _is_phone(field.get("value") or "") or _is_country_only(field.get("value") or "")):
        if any(re.search(r"[A-Za-z]{3,}", _text(line)) and not _is_address(_text(line)) and not _is_phone(_text(line)) for line in lines):
            reasons.append("party_gold_is_non_party_line_inside_adjacent_party_block")
    if base == "goods_description" and re.search(r"\b(?:TOTAL|PKG|KGS|KG)\b", field.get("value") or "", re.I):
        reasons.append("goods_description_contains_table_total_or_unit_token")
    if base == "description" and re.search(r"\b(?:DLSU\d+|B\d{4,}|U\d+)\b", field.get("value") or "", re.I):
        reasons.append("item_description_contains_marks_or_container_identifier")
    return reasons


def audit(cases_root: Path, output_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        gt_path = case_dir / "gt.json"
        gold_path = case_dir / "semantic_gold_fields.json"
        if not all(path.is_file() for path in (manifest_path, gt_path, gold_path)):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_gt = json.loads(gt_path.read_text(encoding="utf-8"))
        tokens = _tokens(raw_gt)
        gold_fields = json.loads(gold_path.read_text(encoding="utf-8"))
        for field in gold_fields:
            if field.get("status") != "available":
                continue
            indices = [int(index) for index in field.get("source_token_indices", [])]
            value_tokens = [token for token in tokens if token["index"] in set(indices)]
            value = str(field.get("value") or "")
            zone = _zone(field["field_name"], manifest["document_type"])
            inside = bool(value_tokens) and all(_in_zone(token, zone) for token in value_tokens) if zone else bool(value_tokens)
            anchor_text, anchor_position = _anchor(tokens, field["field_name"], zone)
            type_reasons = _type_reason(field["field_name"], value, manifest["document_type"])
            structural = _structural_reasons(field, value_tokens, tokens, manifest["document_type"])
            if not inside:
                structural.insert(0, "gold_tokens_outside_semantic_relative_section")
            reasons = type_reasons + structural
            gold_box = None
            if value_tokens:
                gold_box = [min(x["bbox"][0] for x in value_tokens), min(x["bbox"][1] for x in value_tokens), max(x["bbox"][2] for x in value_tokens), max(x["bbox"][3] for x in value_tokens)]
            boundary = f"relative_zone={zone}; next_boundary=zone_end_or_next_template_section"
            rows.append({
                "case_id": manifest["case_id"],
                "document_type": manifest["document_type"],
                "field_name": field["field_name"],
                "current_gold": value,
                "anchor_text": anchor_text,
                "anchor_position": anchor_position,
                "gold_position": json.dumps(gold_box, ensure_ascii=False),
                "next_boundary": boundary,
                "source_token_indices": json.dumps(indices),
                "gold_token_positions": json.dumps({str(token["index"]): token["bbox"] for token in value_tokens}, ensure_ascii=False),
                "section_internal": inside,
                "type_compatible": not type_reasons,
                "classification": "SUSPECT_GOLD" if reasons else "VALID_GOLD",
                "suspect_reason": ";".join(reasons),
            })
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["case_id", "document_type", "field_name"]
    with (output_dir / "suspect_gold.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    by_field: dict[str, Counter[str]] = defaultdict(Counter)
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_field[f"{row['document_type']}::{_base(row['field_name'])}"]["available"] += 1
        by_field[f"{row['document_type']}::{_base(row['field_name'])}"]["suspect" if row["classification"] == "SUSPECT_GOLD" else "valid"] += 1
        by_type[row["document_type"]]["available"] += 1
        by_type[row["document_type"]]["suspect" if row["classification"] == "SUSPECT_GOLD" else "valid"] += 1
    summary = {
        "prediction_blind": True,
        "source": "AI-Hub gt.json token text and geometry plus semantic-v2 gold; no extractor/OCR prediction read",
        "available": len(rows),
        "suspect": sum(row["classification"] == "SUSPECT_GOLD" for row in rows),
        "valid": sum(row["classification"] == "VALID_GOLD" for row in rows),
        "by_document_type": {key: dict(value) for key, value in sorted(by_type.items())},
        "by_field": {key: dict(value) for key, value in sorted(by_field.items())},
    }
    (output_dir / "gold_audit_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# semantic-v2 gold audit", "", "This audit is prediction-blind: it reads only AI-Hub gt.json, token geometry, and semantic-v2 gold.", "", f"Available gold fields: {summary['available']}", f"SUSPECT_GOLD: {summary['suspect']}", f"VALID_GOLD: {summary['valid']}", "", "## By document type", "", "| Document type | Available | Suspect | Valid |", "|---|---:|---:|---:|"]
    for key, value in sorted(by_type.items()):
        lines.append(f"| {key} | {value['available']} | {value['suspect']} | {value['valid']} |")
    lines += ["", "## By field", "", "| Document type / field | Available | Suspect | Valid |", "|---|---:|---:|---:|"]
    for key, value in sorted(by_field.items()):
        lines.append(f"| {key} | {value['available']} | {value['suspect']} | {value['valid']} |")
    lines += ["", "`anchor_text=UNANNOTATED_LABEL` means the label was not present as an exact word token in the AI-Hub source annotation; it is not treated as a gold failure by itself.", ""]
    (output_dir / "GOLD_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("artifacts/fintra/field_eval/cases"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v2"))
    args = parser.parse_args()
    print(json.dumps(audit(args.cases, args.output_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
