"""Build an independent, typed semantic-gold view from AI-Hub annotations.

AI-Hub provides word-level annotations, not Fintra field labels.  This builder
uses only the frozen source annotation and relative template zones.  It never
reads recognition predictions.  Values that cannot be separated by a typed
constraint are marked ``ambiguous_gt`` instead of being guessed.

The original ``case_manifest.json`` gold is intentionally left untouched.  A
``semantic_gold_fields.json`` file is written beside each case and is selected
explicitly by the evaluator with ``--gold-source semantic-v2``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fintra.normalization.values import normalize_date


WIDTH = 1654.0
HEIGHT = 2340.0
MONTHS = {name: i for i, name in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1
)}
UNIT_RE = re.compile(r"^(?:\d[\d.,]*\s*)?(?:KG|KGS|G|GRAM|GRAMS)$", re.I)
NUMBER_RE = re.compile(r"^[+-]?(?:\d[\d.,]*|\d[\d.,]*[A-Z]+)$", re.I)


def _tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result.append({
            "index": index,
            "text": "" if item.get("data") is None else str(item["data"]).strip(),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
            "polygon": [[xs[i], ys[i]] for i in range(len(xs))],
        })
    return result


def _zone(tokens: Iterable[dict[str, Any]], x1: float, x2: float, y1: float, y2: float) -> list[dict[str, Any]]:
    return sorted(
        (item for item in tokens if item["bbox"][0] >= x1 and item["bbox"][2] <= x2
         and item["bbox"][1] >= y1 and item["bbox"][3] <= y2),
        key=lambda item: ((item["bbox"][1] + item["bbox"][3]) / 2, item["bbox"][0], item["index"]),
    )


def _relative_zone(tokens: Iterable[dict[str, Any]], x1: float, x2: float, y1: float, y2: float) -> list[dict[str, Any]]:
    return _zone(tokens, x1 * WIDTH, x2 * WIDTH, y1 * HEIGHT, y2 * HEIGHT)


def _join(items: Iterable[dict[str, Any]]) -> str:
    return " ".join(item["text"] for item in items if item["text"])


def _lines(items: Iterable[dict[str, Any]], tolerance: float = 18.0) -> list[list[dict[str, Any]]]:
    lines: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=lambda value: ((value["bbox"][1] + value["bbox"][3]) / 2, value["bbox"][0], value["index"])):
        cy = (item["bbox"][1] + item["bbox"][3]) / 2
        if not lines:
            lines.append([item])
            continue
        previous_cy = sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in lines[-1]) / len(lines[-1])
        if abs(cy - previous_cy) <= tolerance:
            lines[-1].append(item)
        else:
            lines.append([item])
    return [sorted(line, key=lambda value: (value["bbox"][0], value["index"])) for line in lines]


def _box(items: list[dict[str, Any]]) -> list[list[float]] | None:
    if not items:
        return None
    return [[min(x["bbox"][0] for x in items), min(x["bbox"][1] for x in items)],
            [max(x["bbox"][2] for x in items), min(x["bbox"][1] for x in items)],
            [max(x["bbox"][2] for x in items), max(x["bbox"][3] for x in items)],
            [min(x["bbox"][0] for x in items), max(x["bbox"][3] for x in items)]]


def _evidence(field_name: str, items: list[dict[str, Any]], *, value: str | None = None,
              status: str = "available", review: str = "relative_template_and_type_constraint") -> dict[str, Any]:
    if status == "available" and not items:
        status = "ambiguous_gt"
    source = _join(items) if items else None
    if value is None and status == "available":
        value = source
    return {
        "field_name": field_name,
        "value": value if status == "available" else None,
        "status": status,
        "source_text": source,
        "bbox": _box(items),
        "source_token_indices": [item["index"] for item in items],
        "gold_review": review,
    }


def _single_line(field_name: str, items: list[dict[str, Any]], *, pick: str = "first") -> dict[str, Any]:
    lines = _lines(items)
    if not lines:
        return _evidence(field_name, [], status="ambiguous_gt", review="no_source_annotation_in_typed_zone")
    chosen = lines[0] if pick == "first" else lines[-1]
    return _evidence(field_name, chosen)


def _explicit_date(text: str) -> str | None:
    """Parse the three unambiguous English-month layouts seen in annotations."""
    normalized = re.sub(r"[,]+", " ", text.upper())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    match = re.fullmatch(r"(\d{4}) ([A-Z]{3,9}) (\d{1,2})", normalized)
    if match:
        year, month, day = match.groups()
    else:
        match = re.fullmatch(r"([A-Z]{3,9}) (\d{1,2}) (\d{4})", normalized)
        if match:
            month, day, year = match.groups()
        else:
            match = re.fullmatch(r"(\d{1,2}) ([A-Z]{3,9}) (\d{4})", normalized)
            if not match:
                return normalize_date(text)
            day, month, year = match.groups()
    month_number = MONTHS.get(month[:3])
    if month_number is None:
        return None
    try:
        return date(int(year), month_number, int(day)).isoformat()
    except ValueError:
        return None


def _date_field(field_name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [(line, _explicit_date(_join(line))) for line in _lines(items)]
    valid = [(line, parsed) for line, parsed in candidates if parsed]
    if len(valid) != 1:
        return _evidence(field_name, [], status="ambiguous_gt", review="date_not_uniquely_parseable_in_typed_zone")
    return _evidence(field_name, valid[0][0])


def _typed_lines(items: list[dict[str, Any]], predicate) -> list[list[dict[str, Any]]]:
    return [line for line in _lines(items) if predicate(_join(line))]


def _numeric(text: str) -> bool:
    return bool(re.search(r"\d", text)) and bool(re.fullmatch(r"[\s$€£¥A-Z(),.+/-]*\d[\s$€£¥A-Z(),.+/-]*", text, re.I))


def _item_rows(items: list[dict[str, Any]], quantity_x=(820, 950), minimum=45.0) -> list[float]:
    centers: list[float] = []
    for item in sorted((x for x in items if quantity_x[0] <= x["bbox"][0] <= quantity_x[1]), key=lambda x: x["bbox"][1]):
        center = (item["bbox"][1] + item["bbox"][3]) / 2
        if not centers or center - centers[-1] > minimum:
            centers.append(center)
    return centers


def _near(items: list[dict[str, Any]], center: float, tolerance: float = 42.0) -> list[dict[str, Any]]:
    return [item for item in items if abs((item["bbox"][1] + item["bbox"][3]) / 2 - center) <= tolerance]


def _cell(field_name: str, items: list[dict[str, Any]], *, numeric: bool = False) -> dict[str, Any]:
    lines = _lines(items)
    if numeric:
        lines = [line for line in lines if _numeric(_join(line))]
    if len(lines) != 1:
        return _evidence(field_name, [], status="ambiguous_gt", review="cell_not_uniquely_separable")
    return _evidence(field_name, lines[0])


def _ci_gold(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        _single_line("invoice_number", _relative_zone(tokens, .51, .80, .10, .17)),
        _date_field("invoice_date", _relative_zone(tokens, .51, .88, .14, .24)),
        _single_line("seller", _relative_zone(tokens, .06, .52, .12, .24)),
        _single_line("buyer", _relative_zone(tokens, .06, .52, .24, .34)),
    ]
    currency = [x for x in tokens if re.fullmatch(r"USD|EUR|GBP|JPY|CNY|KRW", x["text"], re.I)]
    fields.append(_evidence("currency", currency) if len({x["text"].upper() for x in currency}) == 1 else _evidence("currency", [], status="ambiguous_gt", review="currency_not_unique"))
    total = _relative_zone(tokens, .72, .96, .62, .78)
    total_lines = [line for line in _lines(total) if any(_numeric(x["text"]) for x in line)]
    fields.append(_evidence("total_amount", total_lines[0]) if len(total_lines) == 1 else _evidence("total_amount", [], status="ambiguous_gt", review="total_not_unique_in_footer_zone"))
    item_tokens = [x for x in tokens if 1000 <= x["bbox"][1] <= 1400]
    for index, center in enumerate(_item_rows(item_tokens)):
        row = _near(item_tokens, center)
        fields.extend([
            _cell(f"items[{index}].description", [x for x in row if 120 <= x["bbox"][0] <= 700]),
            _cell(f"items[{index}].quantity", [x for x in row if 820 <= x["bbox"][0] <= 950], numeric=True),
            _cell(f"items[{index}].unit", [x for x in row if 950 <= x["bbox"][0] <= 1100]),
            _cell(f"items[{index}].unit_price", [x for x in row if 1100 <= x["bbox"][0] <= 1260], numeric=True),
            _cell(f"items[{index}].amount", [x for x in row if 1260 <= x["bbox"][0] <= 1520], numeric=True),
        ])
    return fields


def _packing_gold(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        _evidence("packing_list_number", [], status="not_applicable", review="template_does_not_expose_a_unique_number_field"),
        _date_field("date", _relative_zone(tokens, .69, .91, .07, .15)),
        _single_line("exporter", _relative_zone(tokens, .06, .49, .12, .22)),
        _single_line("consignee", _relative_zone(tokens, .06, .46, .21, .31)),
    ]
    item_tokens = [x for x in tokens if 1000 <= x["bbox"][1] <= 1520]
    for index, center in enumerate(_item_rows(item_tokens)):
        row = _near(item_tokens, center)
        fields.extend([
            _cell(f"items[{index}].description", [x for x in row if x["bbox"][0] < 730]),
            _cell(f"items[{index}].quantity", [x for x in row if 800 <= x["bbox"][0] <= 950], numeric=True),
            _cell(f"items[{index}].unit", [x for x in row if 800 <= x["bbox"][0] <= 950 and not re.fullmatch(r"\d+(?:[.,]\d+)?", x["text"]) ]),
        ])
    package_zone = _relative_zone(tokens, .21, .40, .70, .79)
    package_tokens = [x for x in package_zone if re.fullmatch(r"\d+(?:[.,]\d+)?", x["text"])]
    fields.append(_evidence("package_count", package_tokens[:1]) if len(package_tokens) == 1 else _evidence("package_count", [], status="ambiguous_gt", review="package_count_not_unique"))
    gross_zone = _relative_zone(tokens, .24, .43, .74, .81)
    gross_tokens = [x for x in gross_zone if re.search(r"KG|KGS|GRAM|\bG\b", x["text"], re.I) and re.search(r"\d", x["text"])]
    fields.append(_evidence("gross_weight", gross_tokens[:1]) if len(gross_tokens) == 1 else _evidence("gross_weight", [], status="ambiguous_gt", review="gross_weight_not_unique"))
    fields.append(_evidence("net_weight", [], status="ambiguous_gt", review="net_weight_not_semantically_separable_from_template"))
    units = [x for x in tokens if re.fullmatch(r"KG|KGS|G|GRAM|GRAMS", x["text"], re.I)]
    fields.append(_evidence("weight_unit", units[:1]) if len({x["text"].upper() for x in units}) == 1 and units else _evidence("weight_unit", [], status="ambiguous_gt", review="weight_unit_not_unique"))
    return fields


def _last_line(field_name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return _single_line(field_name, items, pick="last")


def _bl_gold(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    number_zone = _relative_zone(tokens, .70, .94, .115, .18)
    number_candidates = [x for x in number_zone if re.search(r"[A-Za-z]", x["text"]) and re.search(r"\d", x["text"]) and not _explicit_date(x["text"])]
    date_zone = _relative_zone(tokens, .70, .96, .07, .13)
    fields = [
        _evidence("bl_number", number_candidates[:1]) if len(number_candidates) == 1 else _evidence("bl_number", [], status="ambiguous_gt", review="B/L_identifier_not_unique"),
        _single_line("shipper", _relative_zone(tokens, .04, .49, .12, .22)),
        _single_line("consignee", _relative_zone(tokens, .04, .49, .21, .31)),
        _single_line("notify_party", _relative_zone(tokens, .04, .49, .29, .39)),
        _last_line("vessel", _relative_zone(tokens, .04, .27, .35, .43)),
        _last_line("port_of_loading", _relative_zone(tokens, .27, .49, .35, .43)),
        _last_line("port_of_discharge", _relative_zone(tokens, .04, .27, .40, .49)),
        _date_field("shipment_date", date_zone),
    ]
    table = _relative_zone(tokens, .30, .69, .50, .65)
    total_lines = [line for line in _lines(tokens) if any(x["text"].upper() == "TOTAL" for x in line)]
    total_line = total_lines[-1] if total_lines else []
    package_total = [x for x in total_line if .12 * WIDTH <= x["bbox"][0] <= .30 * WIDTH and re.fullmatch(r"\d+(?:[.,]\d+)?", x["text"])]
    gross_total = [x for x in total_line if .68 * WIDTH <= x["bbox"][0] <= .79 * WIDTH
                   and re.search(r"\d", x["text"])
                   and re.search(r"(?:KG|KGS|GRAM|GRAMS|\bG\b)", x["text"], re.I)]
    fields.extend([
        _evidence("package_count", package_total) if len(package_total) == 1 else _evidence("package_count", [], status="ambiguous_gt", review="no_unique_total_package_count"),
        _evidence("gross_weight", gross_total) if len(gross_total) == 1 else _evidence("gross_weight", [], status="ambiguous_gt", review="no_unique_total_gross_weight"),
    ])
    units = [x for x in tokens if re.fullmatch(r"KG|KGS|G|GRAM|GRAMS", x["text"], re.I)]
    fields.append(_evidence("weight_unit", units[:1]) if len({x["text"].upper() for x in units}) == 1 and units else _evidence("weight_unit", [], status="ambiguous_gt", review="weight_unit_not_unique"))
    goods_lines = []
    for line in _lines(table):
        text = _join(line)
        kept = [x for x in line if x["text"].upper() not in {"TOTAL", "PKG", "KGS", "KG", "G"} and not re.fullmatch(r"\d+(?:[.,]\d+)?", x["text"])]
        if kept and any(re.search(r"[A-Za-z]", x["text"]) for x in kept):
            goods_lines.append(kept)
    goods_items = [x for line in goods_lines for x in line]
    fields.append(_evidence("goods_description", goods_items) if goods_items else _evidence("goods_description", [], status="ambiguous_gt", review="goods_description_not_found_in_table_zone"))
    return fields


def _gold(payload: dict[str, Any], document_type: str) -> list[dict[str, Any]]:
    tokens = _tokens(payload)
    if document_type == "Commercial Invoice":
        return _ci_gold(tokens)
    if document_type == "Packing List":
        return _packing_gold(tokens)
    return _bl_gold(tokens)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    args = parser.parse_args()
    counts = {"available": 0, "ambiguous_gt": 0, "not_applicable": 0}
    cases = 0
    for case_dir in sorted(path for path in args.cases.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        gt_path = case_dir / "gt.json"
        if not manifest_path.is_file() or not gt_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = json.loads(gt_path.read_text(encoding="utf-8"))
        fields = _gold(payload, manifest["document_type"])
        for field in fields:
            counts[field["status"]] = counts.get(field["status"], 0) + 1
        (case_dir / "semantic_gold_fields.json").write_text(json.dumps(fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cases += 1
    print(json.dumps({"cases": cases, "fields": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
