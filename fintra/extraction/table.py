"""Header-relative item table extraction.

The AI-Hub forms contain several table layouts.  This module deliberately
derives column positions from the OCR header band instead of the old fixed
template x-ranges.  It is evidence-only: it never reads Gold, document IDs,
or model output and it returns the original OCR text and polygons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

from fintra.domain.schema import LineItem, EvidenceField, evidence, missing
from fintra.ocr.adapter import OCRRegion, OCRResult

from .layout import Layout, Cell, canonical
from .strategies import numeric_value


_DESCRIPTION = re.compile(r"\b(?:DESCRIPTION|GOODS\s+DESCRIPTION|DESCRIPTION\s+OF\s+GOODS|COMMODITY)\b", re.I)
_QUANTITY = re.compile(r"(?:\bQ(?:TY|UANTITY)\b|Q['’]?TY|UNIT\s+QUANTITY|QUANTITY\s*/\s*UNIT|QTY\s*/\s*UNIT|QUANTITY\s+OR)", re.I)
_UNIT = re.compile(r"(?:\bUNIT\s+TYPE\b|\bUNIT\b|Q['’]?TY\s*/\s*UNIT|QUANTITY\s*/\s*UNIT)", re.I)
_PRICE = re.compile(r"(?:\bUNIT\s*[- ]?\s*PRICE\b|\bPRICE\b)", re.I)
_AMOUNT = re.compile(r"(?:\bAMOUNT\b|\bVALUE\b)", re.I)
_STRUCTURAL = re.compile(r"(?:MARKS?|SHIPPING\s+MARK|PRODUCT\s+CODE|HS\s*CODE|\bCODE\b|PO\s*(?:NO|NUMBER)|REFERENCE)", re.I)
_STOP = re.compile(r"\b(?:SUBTOTAL|TOTAL|GRAND\s+TOTAL|REMARKS?|NOTE|TERMS|FREIGHT|SIGNATURE|DECLARATION)\b", re.I)
_UNIT_TOKEN = re.compile(r"^[A-Za-z]{1,14}(?:/[A-Za-z]{1,8})?$")
_NOISE_DESCRIPTION = re.compile(
    r"^(?:PKG(?:S|A)?|PCS?|EA|EACH|BOX(?:ES)?|CTN(?:S)?|CTNS|KGS?|KG|G|CBM|TOTAL|NET|GROSS|N/?A)$",
    re.I,
)


@dataclass(frozen=True)
class _Header:
    field: str
    cell: Cell
    composite: bool = False


def _line_center(line: list[Cell]) -> float:
    return median(cell.cy for cell in line)


def _line_text(line: list[Cell]) -> str:
    return " ".join(cell.text for cell in sorted(line, key=lambda item: item.box[0]))


def _header_for_cell(cell: Cell) -> list[_Header]:
    text = cell.text.strip()
    if not text:
        return []
    result: list[_Header] = []
    if _DESCRIPTION.search(text) and not re.search(r"DESCRIPTION\s+OF\s+PACKAGE", text, re.I):
        result.append(_Header("description", cell))
    composite = bool(_QUANTITY.search(text) and re.search(r"/|\bUNIT\b", text, re.I))
    if _QUANTITY.search(text):
        result.append(_Header("quantity", cell, composite=composite))
    # ``UNIT QUANTITY`` identifies the quantity column; ``UNIT TYPE`` identifies
    # the merchandise unit column.  A plain ``UNIT`` is also a unit column.
    if _UNIT.search(text) and not re.search(r"UNIT\s+(?:QUANTITY|PRICE)", text, re.I):
        result.append(_Header("unit", cell, composite=composite))
    if _PRICE.search(text) and not re.search(r"QUANTITY", text, re.I):
        result.append(_Header("unit_price", cell))
    if _AMOUNT.search(text):
        result.append(_Header("amount", cell))
    if _STRUCTURAL.search(text):
        result.append(_Header(f"__structural_{cell.index}", cell))
    return result


def _header_bands(layout: Layout) -> list[dict[str, _Header]]:
    candidates: list[tuple[float, dict[str, _Header]]] = []
    for line in layout.lines:
        if not line or not 0.12 < _line_center(line) < 0.86:
            continue
        headers: dict[str, _Header] = {}
        for cell in line:
            for header in _header_for_cell(cell):
                current = headers.get(header.field)
                if current is None or len(header.cell.text) > len(current.cell.text):
                    headers[header.field] = header
        if "description" in headers and ("quantity" in headers or "amount" in headers):
            candidates.append((_line_center(line), headers))
    return [item[1] for item in sorted(candidates, key=lambda item: (len(item[1]), item[0]), reverse=True)]


def _bounds_for_headers(headers: dict[str, _Header]) -> dict[str, tuple[float, float]]:
    # Structural columns are boundaries too.  This is what keeps Product Code,
    # Shipping Mark, HS Code and PO No. out of merchandise fields.
    all_columns: list[tuple[float, str]] = []
    for field, header in headers.items():
        all_columns.append((header.cell.cx, field))
    for field, header in headers.items():
        if _STRUCTURAL.search(header.cell.text):
            all_columns.append((header.cell.cx, f"structural:{field}"))
    all_columns.sort()
    # De-duplicate centers while retaining the nearest semantic label.
    centers: list[float] = []
    for center, _ in all_columns:
        if not centers or abs(center - centers[-1]) > 0.012:
            centers.append(center)
    bounds: dict[str, tuple[float, float]] = {}
    for field, header in headers.items():
        center = header.cell.cx
        position = min(range(len(centers)), key=lambda index: abs(centers[index] - center))
        left = 0.0 if position == 0 else (centers[position - 1] + center) / 2
        right = 1.0 if position == len(centers) - 1 else (center + centers[position + 1]) / 2
        bounds[field] = (max(0.0, left), min(1.0, right))
    return bounds


def _numeric_parts(text: str) -> tuple[str, str | None] | None:
    match = re.fullmatch(r"\s*([+-]?[\d][\d,.]*)\s*([A-Za-z]{1,14})?\s*", text)
    if not match:
        return None
    return match.group(1), match.group(2)


def _is_numeric(cell: Cell) -> bool:
    return numeric_value(cell.text) is not None or _numeric_parts(cell.text) is not None


def _evidence(layout: Layout, cells: list[Cell], value: str | None = None) -> EvidenceField:
    return layout.evidence(cells, value=value, method="header_relative_item_table") if cells else missing("header_relative_item_table")


def _select(cells: list[Cell], field: str, header: _Header, center: float) -> list[Cell]:
    if not cells:
        return []
    if field in {"quantity", "unit_price", "amount"}:
        candidates = [cell for cell in cells if _is_numeric(cell)]
    elif field == "unit":
        candidates = [
            cell for cell in cells
            if _UNIT_TOKEN.fullmatch(cell.text.strip())
            or (_numeric_parts(cell.text) is not None and _numeric_parts(cell.text)[1])
        ]
    else:
        candidates = cells
    if not candidates:
        return []
    return [min(candidates, key=lambda cell: (abs(cell.cy - center), abs(cell.cx - header.cell.cx)))]


def _description_cells(cells: list[Cell], center: float) -> list[Cell]:
    selected: list[Cell] = []
    for cell in cells:
        text = cell.text.strip()
        if not re.search(r"[A-Za-z]", text) or _NOISE_DESCRIPTION.fullmatch(text):
            continue
        # Codes/marks are structural when they mix digits and letters.  Product
        # descriptions such as ``A4 STEEL`` remain valid because they contain
        # at least one normal alphabetic word and are not identifier-shaped.
        if re.fullmatch(r"[A-Za-z]*\d[A-Za-z0-9./_-]*", text) and not re.search(r"\s", text):
            continue
        selected.append(cell)
    return sorted(selected, key=lambda cell: (cell.cy, cell.cx))


def _row_groups(layout: Layout, headers: dict[str, _Header], bounds: dict[str, tuple[float, float]]) -> list[list[Cell]]:
    numeric_fields = [field for field in ("quantity", "unit_price", "amount") if field in headers]
    if not numeric_fields:
        return []
    header_bottom = max(header.cell.box[3] for header in headers.values())
    lines = [line for line in layout.lines if _line_center(line) > header_bottom + layout.line_height * 0.5]
    stop_y = min(
        (_line_center(line) for line in lines if _STOP.search(_line_text(line))),
        default=1.01,
    )
    lines = [line for line in lines if _line_center(line) < stop_y]
    row_centers: list[float] = []
    for line in lines:
        for field in numeric_fields:
            left, right = bounds[field]
            if any(left <= cell.cx < right and _is_numeric(cell) for cell in line):
                center = _line_center(line)
                if not row_centers or abs(center - row_centers[-1]) > layout.line_height * 1.35:
                    row_centers.append(center)
                break
    if not row_centers:
        return []
    groups: list[list[Cell]] = []
    for index, center in enumerate(row_centers):
        upper = header_bottom if index == 0 else (row_centers[index - 1] + center) / 2
        lower = stop_y if index == len(row_centers) - 1 else (center + row_centers[index + 1]) / 2
        groups.append([cell for line in lines for cell in line if upper <= cell.cy < lower])
    return groups


def extract_header_relative_items(result: OCRResult, document_type: str | None = None) -> list[LineItem]:
    """Extract merchandise rows using a detected header-relative column grid.

    An empty result means the header is not sufficiently informative; callers
    should retain their existing conservative fallback in that case.
    """
    layout = Layout(result)
    bands = _header_bands(layout)
    if not bands:
        return []
    headers = bands[0]
    bounds = _bounds_for_headers(headers)
    rows = _row_groups(layout, headers, bounds)
    output: list[LineItem] = []
    for row in rows:
        values: dict[str, EvidenceField] = {}
        for field, header in headers.items():
            if field not in {"description", "quantity", "unit", "unit_price", "amount"}:
                continue
            left, right = bounds[field]
            cells = [cell for cell in row if left <= cell.cx < right]
            if field == "description":
                selected = _description_cells(cells, _line_center(row))
                values[field] = _evidence(layout, selected)
            else:
                selected = _select(cells, field, header, _line_center(row))
                if field == "quantity" and selected:
                    parts = _numeric_parts(selected[0].text)
                    values[field] = _evidence(layout, selected, value=parts[0] if parts else None)
                elif field == "unit" and selected:
                    parts = _numeric_parts(selected[0].text)
                    values[field] = _evidence(layout, selected, value=parts[1] if parts and parts[1] else None)
                else:
                    values[field] = _evidence(layout, selected)
        if not values.get("description", missing()).value or not values.get("quantity", missing()).value:
            continue
        output.append(LineItem(
            description=values.get("description", missing()),
            quantity=values.get("quantity", missing()),
            unit=values.get("unit", missing()),
            unit_price=values.get("unit_price", missing()),
            amount=values.get("amount", missing()),
        ))
    return output


__all__ = ["extract_header_relative_items"]
