"""Generalized item-table reconstruction for invoice and packing layouts."""

from __future__ import annotations

import re
from statistics import median
from typing import Any

from .candidate import Candidate, select
from .layout import Cell, Layout, canonical
from .specs import SPECS
from .scalar import _is_number, _is_unit


STOP = re.compile(r"\b(?:SUBTOTAL|SUB TOTAL|GRAND TOTAL|TOTAL|REMARKS?|NOTE|TERMS|FREIGHT|SIGNATURE|AUTHORIZED|CERTIFIED|DECLARATION|COUNTRY OF ORIGIN|NUMBER OF PACKAGES?)\b", re.I)
STRUCTURAL = re.compile(r"\b(?:HS CODE|H[.]?S[.]? CODE|PRODUCT CODE|ITEM CODE|SHIPPING MARK|MARKS AND NUMBERS|CONTAINER|PACKAGE|PKGS?|WEIGHT|MEASUREMENT|COUNTRY OF ORIGIN)\b", re.I)
MONEY = re.compile(r"(?:USD|EUR|GBP|JPY|CNY|KRW|HKD|\$|€|£|¥)", re.I)

TABLE_ALIASES = {
    "description": ("DESCRIPTION", "DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "ITEM DESCRIPTION", "COMMODITY", "PARTICULARS"),
    "hs_code": ("HS CODE", "H.S. CODE", "HARMONIZED CODE", "HS NO"),
    "quantity": ("QUANTITY", "QTY", "QUANTITIES", "NO OF PKGS"),
    "unit": ("UNIT", "UOM", "UNITS"),
    "unit_price": ("UNIT PRICE", "UNIT COST", "PRICE/UNIT", "RATE", "PRICE"),
    "amount": ("LINE AMOUNT", "EXTENDED AMOUNT", "TOTAL PRICE", "AMOUNT", "VALUE"),
    "package_count": ("PACKAGE", "PACKAGES", "PACKAGE COUNT", "NO OF PACKAGES"),
    "package_type": ("PACKAGE TYPE", "KIND OF PACKAGES", "PACKING TYPE"),
    "gross_weight": ("GROSS WEIGHT", "GROSS WT", "G.W.", "G/W"),
    "net_weight": ("NET WEIGHT", "NET WT", "N.W.", "N/W"),
    "weight_unit": ("WEIGHT UNIT", "UNIT OF WEIGHT"),
    "measurement": ("MEASUREMENT", "MEASUREMENTS", "CBM", "M3"),
    "po_number": ("PO NUMBER", "P/O NUMBER", "PURCHASE ORDER NO", "PO NO"),
    "shipping_mark": ("SHIPPING MARK", "SHIPPING MARKS", "MARKS & NOS", "MARKS AND NUMBERS"),
}


def _header_tags(line: list[Cell]) -> dict[str, Cell]:
    found: dict[str, Cell] = {}
    for cell in line:
        text = canonical(cell.text)
        for field, aliases in TABLE_ALIASES.items():
            if any(alias.replace("/", " ") in text or canonical(alias) == text for alias in aliases):
                # Prefer specific headers over generic VALUE/UNIT matches.
                if field not in found or len(canonical(aliases[0])) > len(canonical(found[field].text)):
                    found[field] = cell
    return found


def _header(layout: Layout) -> tuple[list[Cell], dict[str, Cell]] | None:
    candidates = []
    for line in layout.lines:
        tags = _header_tags(line)
        semantic = len(tags)
        if semantic >= 2 and ("description" in tags or "quantity" in tags or "amount" in tags):
            candidates.append((semantic, median(cell.y for cell in line), line, tags))
    if not candidates:
        return None
    _, _, line, tags = max(candidates, key=lambda item: (item[0], -item[1]))
    return line, tags


def _bounds(headers: dict[str, Cell]) -> dict[str, tuple[float, float]]:
    groups: dict[float, list[str]] = {}
    for field, cell in headers.items():
        groups.setdefault(round(cell.x, 6), []).append(field)
    centers = sorted(groups)
    result: dict[str, tuple[float, float]] = {}
    for index, center in enumerate(centers):
        left = 0.0 if index == 0 else (centers[index - 1] + center) / 2.0
        right = 1.0 if index == len(centers) - 1 else (center + centers[index + 1]) / 2.0
        for field in groups[center]:
            result[field] = (left, right)
    if "quantity" in result and "unit" not in result:
        result["unit"] = result["quantity"]
    return result


def _numeric_cells(line: list[Cell]) -> list[Cell]:
    return [cell for cell in line if _is_number(cell.text)]


def _row_lines(layout: Layout, header_line: list[Cell] | None, headers: dict[str, Cell]) -> list[list[Cell]]:
    header_y = max((cell.box[3] for cell in header_line), default=0.0) if header_line else 0.2
    lines = [line for line in layout.lines if median(cell.y for cell in line) > header_y + max(layout.line_height * 0.45, 0.006)]
    stop_y = next((median(cell.y for cell in line) for line in lines if STOP.search(layout.text(line))), 1.01)
    lines = [line for line in lines if median(cell.y for cell in line) < stop_y]
    # A row is normally a numeric line.  A text-only line immediately after a
    # row is a continuation of the description and is attached to that row.
    groups: list[list[Cell]] = []
    for line in lines:
        if not groups:
            groups.append(list(line))
            continue
        prior = groups[-1]
        prior_y = median(cell.y for cell in prior)
        current_y = median(cell.y for cell in line)
        if not _numeric_cells(line) and current_y - prior_y <= max(layout.line_height * 2.2, 0.025):
            groups[-1].extend(line)
        else:
            groups.append(list(line))
    return groups


def _description_cells(cells: list[Cell]) -> list[Cell]:
    output = []
    for cell in cells:
        text = cell.text.strip()
        upper = canonical(text)
        if not re.search(r"[A-Za-z]{2,}", text):
            continue
        if STRUCTURAL.search(upper) or STOP.fullmatch(upper):
            continue
        if upper in {"PKG", "PKGS", "KG", "KGS", "G", "CBM", "M3", "PCS", "EA"}:
            continue
        output.append(cell)
    return sorted(output, key=lambda item: (item.y, item.box[0], item.index))


def _description(value: str) -> str:
    value = " ".join(value.split()).strip(" :;,|")
    value = re.sub(r"^(?:DESCRIPTION(?: OF GOODS?)?|PARTICULARS)\s*[:#-]?\s*", "", value, flags=re.I)
    # Remove only a trailing typed money token; embedded product codes remain.
    value = re.sub(r"\s+(?:USD|EUR|GBP|JPY|CNY|KRW)?\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*$", "", value, flags=re.I)
    return value.strip(" :;,|")


def _field_candidate(layout: Layout, field: str, cells: list[Cell], value: str, valid: bool, score: float, reason: str | None = None) -> Candidate:
    return Candidate(field, value, layout.text(cells), None, tuple(cells), None, "table_cell", valid,
                     "item_table", score, reason or (None if valid else "typed_rejection"))


def _cell_value(layout: Layout, field: str, cells: list[Cell], header: Cell | None, row_y: float) -> dict[str, Any]:
    candidates: list[Candidate] = []
    for cell in cells:
        text = cell.text.strip()
        if field == "description":
            valid = bool(_description_cells([cell]))
            value = _description(text) if valid else ""
        elif field in {"quantity", "package_count"}:
            value, valid = text, _is_number(text)
        elif field in {"unit", "weight_unit"}:
            value, valid = text, _is_unit(text)
        elif field in {"unit_price", "amount", "gross_weight", "net_weight", "measurement"}:
            value, valid = text, _is_number(text)
        elif field == "hs_code":
            value, valid = text, bool(re.fullmatch(r"[A-Za-z0-9 ./-]{3,}", text))
        else:
            value, valid = text, bool(text)
        score = 3.0 - abs(cell.y - row_y) * 8.0
        if header:
            score -= abs(cell.x - header.x) * 1.5
        if valid:
            candidates.append(_field_candidate(layout, field, [cell], value, True, score))
    return select(layout, candidates, method="v2_table_rank") if candidates else {"value": None, "status": "missing", "extraction_method": "v2_table_no_candidate"}


def _header_items(layout: Layout, header_line: list[Cell], headers: dict[str, Cell], document_type: str) -> list[dict[str, Any]]:
    bounds = _bounds(headers)
    rows = _row_lines(layout, header_line, headers)
    output = []
    for row in rows:
        row_y = median(cell.y for cell in row)
        values: dict[str, dict[str, Any]] = {}
        for field in ("description", "hs_code", "quantity", "unit", "unit_price", "amount", "po_number", "package_count", "package_type", "gross_weight", "net_weight", "weight_unit", "measurement", "shipping_mark"):
            if field not in bounds:
                continue
            left, right = bounds[field]
            cells = [cell for cell in row if left <= cell.x < right]
            if cells:
                values[field] = _cell_value(layout, field, cells, headers.get(field), row_y)
        if any(item.get("value") for item in values.values()):
            output.append(values)
    return output


def _inferred_items(layout: Layout, document_type: str) -> list[dict[str, Any]]:
    """Headerless fallback: infer right-side typed columns before text."""
    rows = []
    for line in layout.lines:
        if STOP.search(layout.text(line)):
            break
        numbers = sorted(_numeric_cells(line), key=lambda cell: cell.x)
        if len(numbers) >= 2:
            rows.append(list(line))
    output = []
    for row in rows:
        numbers = sorted(_numeric_cells(row), key=lambda cell: cell.x)
        amount = numbers[-1]
        unit_price = numbers[-2] if len(numbers) >= 3 else None
        # Three numeric cells are the common headerless row shape:
        # quantity, unit_price, amount.  The previous >=4 guard silently
        # dropped quantity for exactly that shape.
        quantity = numbers[-3] if len(numbers) >= 3 else (numbers[0] if len(numbers) == 2 else None)
        unit = next((cell for cell in row if cell.x >= (quantity.x if quantity else 0.0) and cell.x <= (unit_price.x if unit_price else amount.x) and _is_unit(cell.text)), None)
        text_cells = [cell for cell in row if cell.x < (quantity.x if quantity else amount.x) and _description_cells([cell])]
        values: dict[str, dict[str, Any]] = {}
        if text_cells:
            values["description"] = _field_candidate(layout, "description", text_cells, _description(layout.text(text_cells)), True, 1.0).evidence(layout, method="v2_table_inferred")
        if quantity:
            values["quantity"] = _field_candidate(layout, "quantity", [quantity], quantity.text, True, 1.0).evidence(layout, method="v2_table_inferred")
        if unit:
            values["unit"] = _field_candidate(layout, "unit", [unit], unit.text, True, 1.0).evidence(layout, method="v2_table_inferred")
        if unit_price:
            values["unit_price"] = _field_candidate(layout, "unit_price", [unit_price], unit_price.text, True, 1.0).evidence(layout, method="v2_table_inferred")
        values["amount"] = _field_candidate(layout, "amount", [amount], amount.text, True, 1.0).evidence(layout, method="v2_table_inferred")
        if values:
            output.append(values)
    return output


def resolve(layout: Layout, document_type: str) -> list[dict[str, Any]]:
    found = _header(layout)
    rows = _header_items(layout, found[0], found[1], document_type) if found else _inferred_items(layout, document_type)
    return rows


def resolve_goods_description(layout: Layout) -> dict[str, Any]:
    # Prefer an explicit bounded goods-description anchor.
    anchors = layout.anchors("goods_description", SPECS["goods_description"].aliases)
    for anchor in anchors:
        adjacent = layout.adjacent(anchor, anchors)
        if adjacent:
            cells, relation, _ = adjacent[0]
            value = layout.text(cells)
            if re.search(r"[A-Za-z]{2,}", value) and not STOP.search(value):
                return _field_candidate(layout, "goods_description", cells, value, True, anchor.strength * 4.0).evidence(layout, method="v2_goods_anchor")
    # Repeated rows: textual cells between left package/number and right typed
    # columns are cargo evidence, but footer/weight lines are excluded.
    selected = []
    for line in layout.lines:
        if STOP.search(layout.text(line)):
            continue
        nums = sorted(_numeric_cells(line), key=lambda cell: cell.x)
        if len(nums) < 2:
            continue
        for cell in line:
            if cell.x < nums[-1].x and _description_cells([cell]):
                selected.append(cell)
    if selected:
        return _field_candidate(layout, "goods_description", selected, _description(layout.text(selected)), True, 0.8).evidence(layout, method="v2_goods_table")
    return {"value": None, "status": "missing", "extraction_method": "v2_goods_missing"}


__all__ = ["resolve", "resolve_goods_description"]
