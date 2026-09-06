"""Build an audited semantic-v3 gold view from AI-Hub annotations only.

This is deliberately separate from ``build_semantic_field_gold.py``.  The
semantic-v2 files remain frozen for historical comparison.  The v3 rules use
relative layout, reading order, typed candidates, and table columns; they do
not read OCR/extractor predictions or case-specific values.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_semantic_field_gold as v2


COMPANY_MARKERS = {
    "CO", "CO.", "LTD", "LTD.", "INC", "INC.", "LLC", "CORP", "CORPORATION",
    "COMPANY", "INDUSTRIES", "ENTERPRISES", "TRADING", "SYSTEMS", "GROUP",
    "STRUCTURES", "TECHNOLOGIES", "SOLUTIONS", "AUTHORITY", "OFFICE",
}
TRANSPORT_PREFIXES = ("CFS", "CY", "DEQ", "FOB", "DDU", "DDP", "V.")
KNOWN_UNITS = {"KG", "KGS", "G", "GRAM", "GRAMS", "PC", "PCS", "EA", "EACH", "PKG", "BOX", "CTN", "SET", "UNIT", "POUND", "YARD", "DRUM", "BAG", "PIECE", "ST"}


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _is_phone(text: str) -> bool:
    return bool(re.search(r"(?:TEL|FAX|\+?\d)[^A-Za-z]{0,4}\d", text.upper())) and len(re.findall(r"\d", text)) >= 5


def _is_address(text: str) -> bool:
    upper = text.upper()
    return bool(re.search(r"\b(?:STREET|ROAD|AVENUE|CITY|DISTRICT|KOREA|JAPAN|CHINA|TAIWAN|USA|UNITED STATES|QLD|AK|ZIP)\b", upper)) or bool(re.search(r"\bREP\.", upper)) or bool(re.search(r"(?:^|[\s,])(?:ST|RD|AVE)\.?(?:[\s,]|$)", upper)) or bool(re.search(r"\b\d{4,6}\b", text))


def _is_country(text: str) -> bool:
    return _norm(text) in {_norm(x) for x in (
        "ARGENTINA", "AUSTRALIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA", "DENMARK", "EGYPT", "ERITREA", "FINLAND", "FRANCE", "GERMANY", "GREECE", "HAITI", "INDIA", "IRELAND", "ISRAEL", "ITALY", "JAPAN", "KOREA", "MALAYSIA", "MEXICO", "NIGERIA", "NORWAY", "POLAND", "SOUTH AFRICA", "SPAIN", "TAIWAN", "THAILAND", "TURKEY", "UNITED KINGDOM", "UNITED STATES", "VIET NAM", "VIETNAM"
    )}


def _contains_country(text: str) -> bool:
    upper = text.upper()
    return any(re.search(r"\b" + re.escape(country) + r"\b", upper) for country in (
        "AUSTRALIA", "BELGIUM", "CANADA", "CHILE", "CHINA", "DENMARK", "EGYPT", "ERITREA", "FINLAND", "FRANCE", "GERMANY", "GREECE", "HAITI", "INDIA", "IRELAND", "ISRAEL", "ITALY", "JAPAN", "KOREA", "MALAYSIA", "NIGERIA", "NORWAY", "POLAND", "SOUTH AFRICA", "SPAIN", "TAIWAN", "THAILAND", "TURKEY", "UNITED STATES", "VIET NAM"
    ))


def _company_like(text: str) -> bool:
    stripped = text.strip()
    if not stripped or _is_phone(stripped) or _is_address(stripped) or _is_country(stripped) or "@" in stripped:
        return False
    upper = stripped.upper()
    if upper.startswith("CODE:") or re.match(r"^(?:CFS|CY)(?:/|\s|$)", upper) or any(upper == prefix or upper.startswith(prefix + " ") for prefix in TRANSPORT_PREFIXES):
        return False
    if upper == "SAME AS CONSIGNEE":
        return True
    words = re.findall(r"[A-Z][A-Z.'-]*", upper)
    if ("," in stripped or _contains_country(stripped)) and not any(marker in words for marker in COMPANY_MARKERS):
        return False
    return len(words) >= 2


def _party_lines(tokens: list[dict[str, Any]], document_type: str) -> list[list[dict[str, Any]]]:
    max_y = .36 if document_type == "B/L" else .40
    candidates = [token for token in tokens if token["bbox"][2] <= .49 * v2.WIDTH and .08 * v2.HEIGHT <= token["bbox"][1] <= max_y * v2.HEIGHT]
    return [line for line in v2._lines(candidates) if _company_like(v2._join(line))]


def _party(field_name: str, tokens: list[dict[str, Any]], document_type: str, ordinal: int) -> dict[str, Any]:
    lines = _party_lines(tokens, document_type)
    if ordinal >= len(lines):
        return v2._evidence(field_name, [], status="ambiguous_gt", review="party_block_has_no_unique_company_line_in_source_annotation")
    return v2._evidence(field_name, lines[ordinal], review="relative_party_block_and_typed_company_line")


def _place_line(field_name: str, tokens: list[dict[str, Any]], *, left: bool, target_y: float | None = None) -> dict[str, Any]:
    if left:
        items = [x for x in tokens if .02 * v2.WIDTH <= x["bbox"][0] and x["bbox"][2] <= .30 * v2.WIDTH and .35 * v2.HEIGHT <= x["bbox"][1] <= .55 * v2.HEIGHT]
    else:
        items = [x for x in tokens if .25 * v2.WIDTH <= x["bbox"][0] and x["bbox"][2] <= .55 * v2.WIDTH and .30 * v2.HEIGHT <= x["bbox"][1] <= .55 * v2.HEIGHT]
    place_lines = []
    for line in v2._lines(items):
        text = v2._join(line)
        if "," in text and not _is_country(text) and not _is_phone(text) and not re.match(r"^(?:CFS|CY|DEQ|FOB|DDU|DDP)\b", text.upper()):
            center_y = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in line) / len(line)
            place_lines.append((abs(center_y - target_y) if target_y is not None else center_y, line))
    if place_lines:
        return v2._evidence(field_name, min(place_lines, key=lambda item: item[0])[1], review="same_column_place_candidate_aligned_to_vessel_row")
    return v2._evidence(field_name, [], status="ambiguous_gt", review="no_unique_place_candidate_in_port_section")


def _vessel(tokens: list[dict[str, Any]]) -> dict[str, Any]:
    items = [x for x in tokens if .02 * v2.WIDTH <= x["bbox"][0] and x["bbox"][2] <= .30 * v2.WIDTH and .35 * v2.HEIGHT <= x["bbox"][1] <= .55 * v2.HEIGHT]
    for line in v2._lines(items):
        text = v2._join(line)
        upper = text.upper()
        if not text or "," in text or _is_country(text) or _is_phone(text) or re.match(r"^(?:CFS|CY|DEQ|FOB|DDU|DDP|V\.)\b", upper):
            continue
        if re.search(r"[A-Za-z]", text):
            return v2._evidence("vessel", line, review="first_reading_order_vessel_candidate_in_vessel_column")
    return v2._evidence("vessel", [], status="ambiguous_gt", review="no_unique_vessel_candidate_in_source_annotation")


def _unit_cell(field_name: str, row: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for item in row:
        if not (.47 * v2.WIDTH <= item["bbox"][0] <= .62 * v2.WIDTH):
            continue
        if _norm(item["text"]) in KNOWN_UNITS:
            candidates.append((item, item["text"]))
            continue
        match = re.fullmatch(r"\d+(?:[.,]\d+)?\s+([A-Za-z]+)", item["text"].strip())
        if match and _norm(match.group(1)) in KNOWN_UNITS:
            candidates.append((item, match.group(1)))
    if len(candidates) == 1:
        item, value = candidates[0]
        return v2._evidence(field_name, [item], value=value, review="quantity_unit_component_split_from_single_source_token")
    return v2._evidence(field_name, [], status="ambiguous_gt", review="unit_not_uniquely_separable_in_quantity_unit_column")


def _numeric(text: str) -> bool:
    return bool(re.search(r"\d", text)) and bool(re.fullmatch(r"[\s$€£¥₩A-Za-z0-9,./()+:-]+", text))


def _quantity_cell(field_name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for line in v2._lines(items):
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)(?:\s+[A-Za-z]+)?", v2._join(line).strip())
        if match:
            candidates.append((line, match.group(1)))
    if len(candidates) == 1:
        line, value = candidates[0]
        return v2._evidence(field_name, line, value=value, review="typed_quantity_component_from_table_cell")
    return v2._evidence(field_name, [], status="ambiguous_gt", review="quantity_not_uniquely_separable_after_v3_column_rule")


def _cell(field_name: str, items: list[dict[str, Any]], *, numeric: bool = False) -> dict[str, Any]:
    lines = v2._lines(items)
    if numeric:
        lines = [line for line in lines if _numeric(v2._join(line))]
    if len(lines) != 1:
        return v2._evidence(field_name, [], status="ambiguous_gt", review="cell_not_uniquely_separable_after_v3_column_rule")
    return v2._evidence(field_name, lines[0])


def _ci_table(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    item_tokens = [x for x in tokens if 1000 <= x["bbox"][1] <= 1520]
    fields: list[dict[str, Any]] = []
    for index, center in enumerate(v2._item_rows(item_tokens)):
        row = v2._near(item_tokens, center, tolerance=50.0)
        fields.extend([
            _cell(f"items[{index}].description", [x for x in row if .24 * v2.WIDTH <= x["bbox"][0] <= .53 * v2.WIDTH]),
            _quantity_cell(f"items[{index}].quantity", [x for x in row if .47 * v2.WIDTH <= x["bbox"][0] <= .62 * v2.WIDTH]),
            _unit_cell(f"items[{index}].unit", row),
            _cell(f"items[{index}].unit_price", [x for x in row if .65 * v2.WIDTH <= x["bbox"][0] <= .78 * v2.WIDTH], numeric=True),
            _cell(f"items[{index}].amount", [x for x in row if .78 * v2.WIDTH <= x["bbox"][0] <= .94 * v2.WIDTH], numeric=True),
        ])
    return fields


def build_v3(payload: dict[str, Any], document_type: str) -> list[dict[str, Any]]:
    tokens = v2._tokens(payload)
    fields = v2._gold(payload, document_type)
    replacements: dict[str, dict[str, Any]] = {}
    if document_type == "Commercial Invoice":
        for name, ordinal in (("seller", 0), ("buyer", 1)):
            replacements[name] = _party(name, tokens, document_type, ordinal)
        for field in _ci_table(tokens):
            replacements[field["field_name"]] = field
    elif document_type == "Packing List":
        for name, ordinal in (("exporter", 0), ("consignee", 1)):
            replacements[name] = _party(name, tokens, document_type, ordinal)
        # Packing layouts use a shared quantity/unit column.  Replace only the
        # unit resolver; descriptions/quantities remain the v2 evidence view.
        item_tokens = [x for x in tokens if 1000 <= x["bbox"][1] <= 1520]
        for index, center in enumerate(v2._item_rows(item_tokens)):
            replacements[f"items[{index}].unit"] = _unit_cell(f"items[{index}].unit", v2._near(item_tokens, center, tolerance=50.0))
    else:
        for name, ordinal in (("shipper", 0), ("consignee", 1), ("notify_party", 2)):
            replacements[name] = _party(name, tokens, document_type, ordinal)
        replacements["vessel"] = _vessel(tokens)
        vessel_items = replacements["vessel"].get("source_token_indices", [])
        vessel_tokens = [token for token in tokens if token["index"] in set(vessel_items)]
        vessel_y = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in vessel_tokens) / len(vessel_tokens) if vessel_tokens else None
        replacements["port_of_loading"] = _place_line("port_of_loading", tokens, left=False, target_y=vessel_y)
        replacements["port_of_discharge"] = _place_line("port_of_discharge", tokens, left=True, target_y=vessel_y)
    return [replacements.get(field["field_name"], field) for field in fields]


def _write_diff(old_root: Path, new_root: Path, diff_path: Path) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for case_dir in sorted(path for path in new_root.iterdir() if path.is_dir()):
        case_id = case_dir.name
        old_path = old_root / case_id / "semantic_gold_fields.json"
        new_path = case_dir / "semantic_gold_fields.json"
        if not old_path.is_file():
            continue
        old = {field["field_name"]: field for field in json.loads(old_path.read_text(encoding="utf-8"))}
        new = {field["field_name"]: field for field in json.loads(new_path.read_text(encoding="utf-8"))}
        manifest = json.loads((case_dir / "case_manifest.json").read_text(encoding="utf-8")) if (case_dir / "case_manifest.json").is_file() else {}
        for field_name in sorted(set(old) | set(new)):
            before, after = old.get(field_name, {}), new.get(field_name, {})
            if before.get("value") == after.get("value") and before.get("status") == after.get("status") and before.get("source_token_indices") == after.get("source_token_indices"):
                continue
            changes.append({
                "case_id": case_id,
                "document_type": manifest.get("document_type", ""),
                "field_name": field_name,
                "old_gold": before.get("value"),
                "new_gold": after.get("value"),
                "old_status": before.get("status"),
                "new_status": after.get("status"),
                "change_reason": after.get("gold_review", "semantic-v3 typed/layout rule"),
                "old_source_token_indices": json.dumps(before.get("source_token_indices", [])),
                "new_source_token_indices": json.dumps(after.get("source_token_indices", [])),
                "source_token_indices_changed": before.get("source_token_indices", []) != after.get("source_token_indices", []),
            })
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(changes[0]) if changes else ["case_id", "document_type", "field_name", "old_gold", "new_gold", "change_reason"]
    with diff_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(changes)
    return changes


def build(cases_root: Path, output_root: Path, diff_path: Path) -> dict[str, Any]:
    output_cases = output_root / "cases"
    output_cases.mkdir(parents=True, exist_ok=True)
    case_count = 0
    for source_case in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path, gt_path = source_case / "case_manifest.json", source_case / "gt.json"
        if not manifest_path.is_file() or not gt_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields = build_v3(json.loads(gt_path.read_text(encoding="utf-8")), manifest["document_type"])
        target = output_cases / source_case.name
        target.mkdir(parents=True, exist_ok=True)
        (target / "case_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "semantic_gold_fields.json").write_text(json.dumps(fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        case_count += 1
    changes = _write_diff(cases_root, output_cases, diff_path)
    return {"cases": case_count, "changed_fields": len(changes), "gold_root": str(output_cases), "gold_diff": str(diff_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("artifacts/fintra/field_eval/cases"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3"))
    parser.add_argument("--gold-diff", type=Path, default=Path("artifacts/fintra/gold_audit/gold_diff.csv"))
    args = parser.parse_args()
    print(json.dumps(build(args.cases, args.output_root, args.gold_diff), ensure_ascii=False))


if __name__ == "__main__":
    main()
