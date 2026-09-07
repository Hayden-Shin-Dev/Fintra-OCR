"""Header-relative item-table resolver for CI and packing lists."""

from __future__ import annotations

import re
from statistics import median

from fintra.domain.schema import EvidenceField, LineItem, evidence, missing

from .candidate import FieldCandidate
from .layout import Cell, Layout, canonical
from .scalar import _numeric_text, is_number, is_quantity, is_unit, numeric_parts


TABLE_ALIASES = {
    "description": ("DESCRIPTION", "DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "COMMODITY", "PARTICULARS"),
    "quantity": ("QUANTITY", "QTY", "QUANTITY UNIT", "QUANTITY OR NET", "NO OF PKGS"),
    "unit": ("UNIT", "UOM", "QUANTITY UNIT", "QUANTITY / UNIT"),
    "unit_price": ("UNIT PRICE", "UNIT PRICE", "RATE", "PRICE"),
    "amount": ("AMOUNT", "VALUE", "EXTENDED AMOUNT", "TOTAL VALUE"),
}
STOP = re.compile(r"\b(?:SUBTOTAL|GRAND TOTAL|TOTAL|REMARKS?|NOTE|TERMS|FREIGHT|SIGNATURE|SIGNED\s+BY|AUTHORIZED|CERTIFIED\s+BY|DECLARATION|COUNTRY\s+OF\s+ORIGIN|NUMBER\s+OF\s+PACKAGES?)\b", re.I)
STRUCTURAL = re.compile(r"\b(?:HS\s*CODE|PRODUCT\s*CODE|ITEM\s*CODE|SHIPPING\s*MARK|SHIPPING|KIND\s+OF|MARKS?|CONTAINER|PACKAGE|PKGS?|WEIGHT|MEASUREMENT|NO\.?\s*&?\s*KINDS?)\b", re.I)


def _header_tags(line: list[Cell]) -> dict[str, Cell]:
    headers: dict[str, Cell] = {}
    for cell in line:
        text = canonical(cell.text)
        if re.search(r"DESCRIPTION|COMMODITY|PARTICULARS|GOODS", text) and not re.search(r"PACKAGE", text):
            headers.setdefault("description", cell)
        if re.search(r"QUANTITY|Q\s*T\s*Y|NO\s+OF\s+PKGS", text):
            headers.setdefault("quantity", cell)
            if re.search(r"UNIT", text):
                headers.setdefault("unit", cell)
        if re.search(r"UNIT|UOM", text) and not re.search(r"UNIT PRICE|UNIT QUANTITY", text):
            headers.setdefault("unit", cell)
        if re.search(r"UNIT PRICE|PRICE|RATE", text) and not re.search(r"QUANTITY", text):
            headers.setdefault("unit_price", cell)
        if re.search(r"AMOUNT|VALUE|EXTENDED", text):
            headers.setdefault("amount", cell)
        if STRUCTURAL.search(text):
            headers.setdefault(f"_structural_{cell.index}", cell)
    return headers


def _header(layout: Layout):
    options = []
    for line in layout.lines:
        y = median(cell.y for cell in line)
        if not 0.18 < y < 0.82:
            continue
        tags = _header_tags(line)
        semantic = len([key for key in tags if not key.startswith("_")])
        if "description" in tags and ("quantity" in tags or "amount" in tags or "unit" in tags):
            options.append((semantic, y, tags))
    return max(options, key=lambda item: (item[0], -item[1])) if options else None


def _bounds(headers: dict[str, Cell]) -> dict[str, tuple[float, float]]:
    # Composite headers (for example ``Q'ty/Unit``) intentionally map two
    # semantic fields to one x-center.  Deduplicate centers before deriving
    # boundaries; otherwise the duplicate center creates a zero-width column.
    grouped: dict[float, list[str]] = {}
    for field, cell in headers.items():
        center = round(cell.x, 6)
        grouped.setdefault(center, []).append(field)
    centers = sorted(grouped)
    result = {}
    for idx, center in enumerate(centers):
        left = 0.0 if idx == 0 else (centers[idx - 1] + center) / 2
        right = 1.0 if idx == len(centers) - 1 else (center + centers[idx + 1]) / 2
        for field in grouped[center]:
            result[field] = (left, right)
    # A single Quantity column often carries a unit on the following OCR
    # line.  Its typed unit candidate belongs to the same normalized column.
    if "quantity" in result and "unit" not in result:
        result["unit"] = result["quantity"]
    return result


def _rows(layout: Layout, headers: dict[str, Cell]) -> list[list[Cell]]:
    bottom = max(cell.box[3] for key, cell in headers.items() if not key.startswith("_"))
    lines = [line for line in layout.lines if median(cell.y for cell in line) > bottom + max(layout.line_height * 0.45, 0.006)]
    stop_y = next((median(cell.y for cell in line) for line in lines if STOP.search(layout.text(line))), 1.01)
    lines = [line for line in lines if median(cell.y for cell in line) < stop_y]
    numeric = []
    for line in lines:
        if any(is_quantity(cell.text) or is_number(cell.text) or re.search(r"\d", cell.text) for cell in line):
            numeric.append(median(cell.y for cell in line))
    centers = []
    for y in numeric:
        if not centers or y - centers[-1] > max(layout.line_height * 1.7, 0.018):
            centers.append(y)
    if not centers:
        centers = [median(cell.y for cell in line) for line in lines if any(re.search(r"[A-Za-z]", cell.text) for cell in line)]
    groups = []
    continuation_margin = max(layout.line_height * 0.45, 0.006)
    for i, center in enumerate(centers):
        top = bottom if i == 0 else (centers[i - 1] + center) / 2 - continuation_margin
        low = stop_y if i == len(centers) - 1 else (center + centers[i + 1]) / 2 + continuation_margin
        group = [cell for line in lines for cell in line if top <= cell.y < low]
        if group:
            groups.append(group)
    return groups


def _text_cells(cells: list[Cell]) -> list[Cell]:
    selected = []
    for cell in cells:
        text = cell.text.strip()
        if not re.search(r"[A-Za-z]", text) or STRUCTURAL.fullmatch(text) or STOP.fullmatch(text):
            continue
        if canonical(text) in {"PKG", "PKGS", "KG", "KGS", "CBM"}:
            continue
        selected.append(cell)
    return sorted(selected, key=lambda item: (item.y, item.box[0]))


def _description_value(value: str) -> str:
    """Remove only unmistakable same-region header/footer contamination."""
    text = " ".join(value.split()).strip()
    text = re.sub(r"^(?:DESCRIPTION\s+OF\s+(?:GOODS?|GOOD\(?S?\)? )|DESCRIPTION\s+OF\s+GOOD\(?S?\)?|PARTICULARS)\s+", "", text, flags=re.I)
    text = re.sub(r"\s+(?:SIGNED\s+BY|AUTHORIZED|CERTIFIED\s+BY)\b.*$", "", text, flags=re.I)
    # A merged OCR region may span the description and amount columns.  Strip
    # a trailing standalone monetary/decimal token, while preserving embedded
    # product codes and alphanumeric descriptions.
    text = re.sub(r"\s+(?:[$€£]|USD|EUR|GBP|JPY|CNY|KRW)?\s*\d[\d,]*(?:\.\d+)?\s*$", "", text, flags=re.I)
    return text.strip(" ,;:")


def _field_candidate(layout: Layout, name: str, cells: list[Cell], value: str, valid: bool, score: float, reason: str | None = None) -> FieldCandidate:
    box = layout.box(cells)
    conf = min((cell.confidence for cell in cells if cell.confidence is not None), default=None)
    ev = evidence(value, source_text=layout.text(cells), bbox=box, confidence=conf, method="clean_table_candidate") if valid else None
    geometry = (min(cell.box[0] for cell in cells), min(cell.box[1] for cell in cells), max(cell.box[2] for cell in cells), max(cell.box[3] for cell in cells)) if cells else None
    return FieldCandidate(name, value, layout.text(cells), tuple(cell.index for cell in cells), box, conf, None, "table_row_column", geometry, valid, "item_table", score, reason, ev)


def _choose(layout: Layout, name: str, cells: list[Cell], kind: str, header: Cell | None, row_y: float) -> EvidenceField:
    candidates = []
    for cell in cells:
        text = cell.text.strip()
        value = _numeric_text(text)
        valid = True
        if kind == "description":
            valid = bool(_text_cells([cell]))
        elif kind == "quantity":
            parts = numeric_parts(text)
            value = parts[0] if parts else ("1" if text in {"I", "l"} else text)
            valid = is_quantity(text)
        elif kind == "unit":
            parts = numeric_parts(text)
            value = parts[1] if parts and parts[1] else text
            valid = bool(parts and parts[1]) or is_unit(text)
        elif kind in {"unit_price", "amount"}:
            valid = is_number(text)
        score = 3 - abs(cell.y - row_y) * 10 - (abs(cell.x - header.x) * 1.5 if header else 0)
        candidates.append(_field_candidate(layout, name, [cell], value, valid, score, None if valid else "typed_rejection"))
    valid = sorted((item for item in candidates if item.accepted), key=lambda item: (item.score, item.ocr_confidence or 0), reverse=True)
    return valid[0].evidence if valid else missing("clean_table_no_typed_candidate")


def _choose_description(layout: Layout, cells: list[Cell], header: Cell | None, row_y: float) -> EvidenceField:
    """Select a description through the same typed candidate path."""
    selected = _text_cells(cells)
    if not selected:
        return missing("clean_table_no_description_candidate")
    value = _description_value(layout.text(selected))
    if not value:
        return missing("clean_table_empty_description_candidate")
    score = 3.0 - abs(median(cell.y for cell in selected) - row_y) * 10
    if header:
        score -= abs(median(cell.x for cell in selected) - header.x) * 1.5
    candidate = _field_candidate(layout, "description", selected, value, True, score)
    return candidate.evidence or missing("clean_table_description_selection_failed")


def _combined_evidence(layout: Layout, name: str, cells: list[Cell], value: str | None, method: str) -> EvidenceField:
    if not cells or not value:
        return missing(f"clean_inferred_{name}_missing")
    return evidence(
        value,
        source_text=layout.text(cells),
        bbox=layout.box(cells),
        confidence=min((cell.confidence for cell in cells if cell.confidence is not None), default=None),
        method=method,
    )


def _inferred_rows(layout: Layout) -> list[list[Cell]]:
    """Build repeated rows when an OCR output loses the table header.

    Row centers come from repeated typed numeric cells.  Text cells are then
    interpreted relative to the row's rightmost typed columns, which is robust
    to optional product-code/marks columns and shifted page layouts.
    """
    usable = []
    for line in layout.lines:
        y = median(cell.y for cell in line)
        if y < 0.22 or STOP.search(layout.text(line)):
            continue
        numeric = [cell for cell in line if is_number(cell.text)]
        if len(numeric) >= 3:
            usable.append((y, numeric))
    if not usable:
        return []
    # Find a repeated x-column signature before interpreting any row.  This
    # filters phone/address/date lines that happen to contain several digits.
    def matches(left, right):
        return sum(1 for cell in left if any(abs(cell.x - other.x) <= 0.045 for other in right))
    best = None
    for i, (left_y, left) in enumerate(usable):
        for right_y, right in usable[i + 1:]:
            if right_y - left_y > 0.18:
                continue
            score = matches(left, right)
            if score >= 3 and (best is None or score > best[0] or (score == best[0] and right_y - left_y < best[1])):
                best = (score, right_y - left_y, left_y, [cell.x for cell in left])
    if best is None:
        return []
    _, _, first_y, signature = best
    centers: list[float] = []
    for y, numeric in usable:
        if y < first_y - max(layout.line_height * 1.5, 0.018):
            continue
        if matches(numeric, [Cell(-1, "", (x, 0, x, 0), [], None, 1) for x in signature]) < 3:
            continue
        if not centers or y - centers[-1] > max(layout.line_height * 1.8, 0.018):
            centers.append(y)
    if not centers:
        return []
    groups = []
    for index, center in enumerate(centers):
        top = max(0.0, center - max(layout.line_height * 1.5, 0.018)) if index == 0 else (centers[index - 1] + center) / 2 - max(layout.line_height * 0.45, 0.006)
        low = (center + max(layout.line_height * 4.0, 0.045)) if index == len(centers) - 1 else (center + centers[index + 1]) / 2 + max(layout.line_height * 0.45, 0.006)
        cells = [cell for line in layout.lines for cell in line if top <= cell.y <= low]
        if cells:
            groups.append(cells)
    return groups


def _infer_item(layout: Layout, row: list[Cell]) -> LineItem | None:
    ordered = sorted(row, key=lambda cell: (cell.y, cell.box[0], cell.index))
    numeric = sorted((cell for cell in ordered if is_number(cell.text)), key=lambda cell: (cell.x, cell.y, cell.index))
    if len(numeric) < 2:
        return None
    amount_cell = numeric[-1]
    price_cell = numeric[-2] if len(numeric) >= 3 else None
    # A currency-marked rightmost pair is the strongest amount/price signal.
    if not re.search(r"[$€£¥]|USD|EUR|GBP|JPY|CNY|KRW", amount_cell.text, re.I) and price_cell is not None and re.search(r"[$€£¥]|USD|EUR|GBP|JPY|CNY|KRW", price_cell.text, re.I):
        amount_cell, price_cell = price_cell, amount_cell
    before_price = [cell for cell in numeric if cell.x < (price_cell.x if price_cell else amount_cell.x)]
    qty_cell = before_price[-1] if before_price else None
    if qty_cell is None:
        return None
    unit_cells = [cell for cell in ordered if cell.x >= qty_cell.x - 0.025 and cell.x <= (price_cell.x if price_cell else amount_cell.x) and is_unit(cell.text)]
    unit_cell = min(unit_cells, key=lambda cell: abs(cell.x - qty_cell.x)) if unit_cells else None
    description_limit = qty_cell.x - max(qty_cell.width * 0.55, 0.015)
    description_cells = [cell for cell in ordered if cell.x < description_limit and re.search(r"[A-Za-z]", cell.text) and not STRUCTURAL.search(cell.text) and not STOP.search(cell.text) and not is_unit(cell.text)]
    # Product/HS code columns are typed numeric cells and therefore do not
    # enter the description.  Marks are retained only when they are the only
    # textual part of the row.
    description_cells = sorted(description_cells, key=lambda cell: (cell.y, cell.box[0], cell.index))
    description = layout.text(description_cells) if description_cells else None
    description = _description_value(description) if description else None
    quantity = qty_cell.text.strip()
    unit = unit_cell.text.strip() if unit_cell else None
    unit_price = _numeric_text(price_cell.text) if price_cell and (re.search(r"[$€£¥]|USD|EUR|GBP|JPY|CNY|KRW", price_cell.text, re.I) or len(numeric) >= 4) else None
    amount = _numeric_text(amount_cell.text) if amount_cell else None
    return LineItem(
        description=_combined_evidence(layout, "description", description_cells, description, "clean_inferred_table_description"),
        quantity=_combined_evidence(layout, "quantity", [qty_cell], quantity, "clean_inferred_table_quantity"),
        unit=_combined_evidence(layout, "unit", [unit_cell] if unit_cell else [], unit, "clean_inferred_table_unit"),
        unit_price=_combined_evidence(layout, "unit_price", [price_cell] if unit_price and price_cell else [], unit_price, "clean_inferred_table_unit_price"),
        amount=_combined_evidence(layout, "amount", [amount_cell] if amount else [], amount, "clean_inferred_table_amount"),
    )


def _infer_table(layout: Layout) -> list[LineItem]:
    items = []
    for row in _inferred_rows(layout):
        item = _infer_item(layout, row)
        if item and any(field.value for field in (item.description, item.quantity, item.unit_price, item.amount)):
            items.append(item)
    return items


def resolve_goods_description(layout: Layout) -> EvidenceField:
    """Resolve B/L goods text from repeated row geometry only.

    The B/L schema has no line-item array, but its cargo table still exposes a
    stable text column between package/class cells and gross-weight cells.
    """
    selected: list[Cell] = []
    for row in _inferred_rows(layout):
        numeric = sorted((cell for cell in row if is_number(cell.text)), key=lambda cell: cell.x)
        if len(numeric) < 3:
            continue
        left = numeric[0].x + 0.04
        right = numeric[-2].x - 0.04
        for cell in row:
            text = canonical(cell.text)
            if left <= cell.x <= right and re.search(r"[A-Za-z]{2,}", cell.text) and not STRUCTURAL.search(cell.text) and not STOP.search(cell.text) and text not in {"PKG", "PKGS", "KG", "KGS", "CBM"}:
                selected.append(cell)
    if not selected:
        return missing("clean_goods_no_inferred_rows")
    return _combined_evidence(layout, "goods_description", selected, layout.text(selected), "clean_inferred_goods_column")


def resolve(layout: Layout) -> list[LineItem]:
    found = _header(layout)
    if not found:
        return _infer_table(layout)
    _, _, headers = found
    bounds = _bounds(headers)
    output = []
    for row in _rows(layout, headers):
        y = median(cell.y for cell in row)
        values: dict[str, EvidenceField] = {}
        for field in ("description", "quantity", "unit", "unit_price", "amount"):
            if field not in bounds:
                values[field] = missing("clean_table_column_not_detected")
                continue
            left, right = bounds[field]
            selected = [cell for cell in row if left <= cell.x < right]
            if field == "description":
                values[field] = _choose_description(layout, selected, headers.get(field), y)
            else:
                values[field] = _choose(layout, field, selected, field, headers.get(field), y)
        if any(values[name].value for name in ("description", "quantity", "unit_price", "amount")):
            output.append(LineItem(description=values["description"], quantity=values["quantity"], unit=values["unit"], unit_price=values["unit_price"], amount=values["amount"]))
    return output


__all__ = ["resolve", "resolve_goods_description"]
