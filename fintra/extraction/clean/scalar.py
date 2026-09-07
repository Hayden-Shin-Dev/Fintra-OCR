"""Typed scalar candidate generation for the clean extractor."""

from __future__ import annotations

import re
from dataclasses import replace
from statistics import median

from fintra.domain.schema import EvidenceField, evidence, missing
from fintra.normalization.values import normalize_currency, normalize_date, parse_amount

from .candidate import FieldCandidate
from .layout import Anchor, Layout, canonical


ALIASES = {
    "invoice_number": ("INVOICE NO", "INVOICE NUMBER", "INV NO", "NO AND DATE OF INVOICE", "NO DATE OF INVOICE"),
    "invoice_date": ("INVOICE DATE", "DATE OF INVOICE", "NO AND DATE OF INVOICE", "NO DATE OF INVOICE"),
    "packing_list_number": ("PACKING LIST NO", "PACKING LIST NUMBER", "INVOICE NO AND DATE OF INVOICE"),
    "date": ("PACKING DATE", "DATE OF PACKING", "DATE"),
    "bl_number": ("BILL OF LADING NO", "BILL OF LADING NUMBER", "BL NO", "B/L NO", "B L NO"),
    "shipment_date": ("DATE SHIPPED", "SHIPPED ON BOARD", "ON BOARD DATE", "SHIPMENT DATE"),
    "vessel": ("VESSEL", "VESSEL / VOY", "VESSEL VOY", "EXPORT CARRIER"),
    "port_of_loading": ("PORT OF LOADING", "LOADING PORT"),
    "port_of_discharge": ("PORT OF DISCHARGE", "DISCHARGE PORT"),
    "currency": ("CURRENCY", "CURRENCY CODE"),
    "total_amount": ("GRAND TOTAL", "TOTAL AMOUNT", "INVOICE TOTAL", "TOTAL VALUE", "TOTAL"),
    "package_count": ("TOTAL PACKAGES", "NO OF PKGS", "NUMBER OF PACKAGES", "TOTAL PKGS", "PACKAGES"),
    "gross_weight": ("GROSS WEIGHT", "TOTAL GROSS WEIGHT", "GROSS WT", "G W"),
    "net_weight": ("NET WEIGHT", "TOTAL NET WEIGHT", "NET WT", "N W"),
    "weight_unit": ("WEIGHT UNIT", "UNIT OF WEIGHT"),
    "goods_description": ("DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "DESCRIPTION OF CARGO", "DESCRIPTION OF PACKAGE AND GOODS", "PARTICULARS FURNISHED BY SHIPPER", "COMMODITY"),
}

INCOTERMS = {"FOB", "CIF", "CFR", "DAF", "DDP", "DDU", "DEQ", "CFS", "CY"}
UNITS = {"EA", "EACH", "PCS", "PC", "BOX", "CTN", "CTNS", "PKG", "PKGS", "PALLET", "SET", "SETS", "KG", "KGS", "G", "CBM", "CFT", "MT", "M", "L", "LTR"}


def _numeric_text(value: str) -> str:
    value = str(value).strip()
    return re.sub(r"([.,])\1+", r"\1", value)


def numeric_parts(value: str):
    value = _numeric_text(value)
    match = re.fullmatch(r"\s*(?:(?:USD|EUR|GBP|JPY|CNY|KRW|US\$|[$€£¥])\s*)?([+-]?[\d][\d,.]*)\s*([A-Za-z]{1,14})?\s*", value, re.I)
    return (match.group(1), match.group(2)) if match else None


def is_number(value: str) -> bool:
    return numeric_parts(value) is not None and parse_amount(_numeric_text(value)) is not None


def is_quantity(value: str) -> bool:
    return is_number(value) or bool(re.fullmatch(r"[Il]", value.strip()))


def is_date(value: str) -> bool:
    return normalize_date(value.strip()) is not None


def is_identifier(value: str) -> bool:
    value = value.strip()
    # Generic phone/contact-number shape.  These values can be nearby an
    # invoice/B/L number but are not document identifiers.
    if re.fullmatch(r"\d{2,5}[-/]\d{2,5}[-/]\d{2,5}", value):
        return False
    return bool(len(value) >= 4 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./_-]*", value) and re.search(r"\d", value) and not is_date(value))


def is_unit(value: str) -> bool:
    value = value.strip().upper()
    return value in UNITS or bool(re.fullmatch(r"[A-Za-z]{1,14}(?:/[A-Za-z]{1,8})?", value))


def is_weight_unit(value: str) -> bool:
    return value.strip().upper() in {"KG", "KGS", "G", "GRAM", "GRAMS", "LB", "LBS", "MT", "TON", "TONS"}


def is_text(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value)) and not re.search(r"\b(?:PORT|PLACE|CARRIER|TOTAL|WEIGHT|PACKAGE|DESCRIPTION)\b", value, re.I)


def _predicate(field: str):
    if field in {"date", "invoice_date", "shipment_date"}:
        return is_date
    if field in {"invoice_number", "packing_list_number", "bl_number"}:
        return is_identifier
    if field == "currency":
        return lambda value: bool(normalize_currency(value) or re.fullmatch(r"[A-Z]{3}", value.strip(), re.I))
    if field in {"total_amount", "package_count", "gross_weight", "net_weight"}:
        return is_number
    if field == "weight_unit":
        return is_weight_unit
    if field == "vessel":
        return lambda value: is_text(value) and len(canonical(value)) >= 5 and "," not in value and canonical(value) not in {"VESSEL", "VOY", "EXPORT CARRIER"} and not re.search(r"\b(?:PORT|PLACE|CARRIER|FOB|CIF|CFR|DAF|DDP|DDU|DEQ|CFS|CY|V\.?\s*\d+|AMOUNT|CHARGES|TOTAL|THIRD PARTY|COMPANY CHECK|METHOD|NUMBER|DESCRIPTION|PACKAGE|WEIGHT)\b", value, re.I)
    if field in {"port_of_loading", "port_of_discharge"}:
        return lambda value: is_text(value) and "," in value and not re.search(r"[$€£¥]|\b(?:KG|KGS|CBM|PKG|PACKAGES|PORT|PLACE|DESTINATION|CARRIER|V(?:OY)?\.?\s*\d+|FOB|CIF|CFR|DAF|DDP|DDU|DEQ|CFS|CY)\b", value, re.I) and not re.search(r"\d", value)
    return is_text


def _inline(value: str, alias: str) -> str | None:
    tokens = canonical(alias).split()
    if not tokens:
        return None
    # Match the semantic words while preserving punctuation/currency in the
    # captured value (canonical() is intentionally lossy for comparison).
    pattern = r"^\s*" + r"\W+".join(re.escape(token) for token in tokens) + r"\s*[:#-]?\s*(.+)$"
    match = re.match(pattern, value.strip(), re.I)
    if match:
        return match.group(1).strip()
    fallback = re.match(r"^\s*" + re.escape(canonical(alias)).replace(r"\ ", r"\s+") + r"\s*[:#-]?\s*(.+)$", canonical(value), re.I)
    return fallback.group(1).strip() if fallback else None


def _candidate(layout: Layout, field: str, anchor: Anchor | None, cells, value: str, relation: str, score: float, valid: bool = True, reason: str | None = None) -> FieldCandidate:
    text = layout.text(cells)
    box = layout.box(cells)
    conf = min((cell.confidence for cell in cells if cell.confidence is not None), default=None)
    ev = evidence(value, source_text=text, bbox=box, confidence=conf, method="clean_scalar_candidate") if valid else None
    geometry = (min(cell.box[0] for cell in cells), min(cell.box[1] for cell in cells), max(cell.box[2] for cell in cells), max(cell.box[3] for cell in cells)) if cells else None
    return FieldCandidate(field, value, text, tuple(cell.index for cell in cells), box, conf, anchor.alias if anchor else None, relation, geometry, valid, "document_scalar", score, reason, ev)


def _anchor_scope(field: str, anchor: Anchor, cells, relation: str) -> bool:
    """Keep transport/typed scalar candidates in the anchor's column.

    B/L forms place several unrelated values on the same horizontal bands.
    A broad right/below search is useful for noisy labels, but it can select a
    carrier, destination, or measurement column instead of the value directly
    belonging to the anchor.  Normalized geometry makes this independent of
    page resolution and form size.
    """
    if field not in {
        "vessel", "port_of_loading", "port_of_discharge", "shipment_date",
        "package_count", "gross_weight", "net_weight", "weight_unit",
    }:
        return True
    center = sum(cell.x for cell in cells) / max(1, len(cells))
    if relation == "below" and abs(center - anchor.x) > 0.16:
        return False
    if relation == "right" and cells[0].box[0] - anchor.box[2] > 0.16:
        return False
    return True


def _goods_candidates(layout: Layout) -> list[FieldCandidate]:
    """Collect goods text from the bounded description column of a B/L.

    B/L forms frequently put package marks, freight class, weights, and legal
    boilerplate on the same page.  A description anchor plus the neighboring
    header columns gives a document-independent section boundary without
    accepting the first arbitrary text region on the page.
    """
    anchors = layout.anchors({"goods_description": ALIASES["goods_description"]})
    result: list[FieldCandidate] = []
    stop = re.compile(r"\b(?:TOTAL|FREIGHT|MARKS?|CONTAINER|GROSS|MEASUREMENTS?|WEIGHT|DECLARED VALUE|LIMITATION|TERMS|SIGNATURE|ISSUED AT)\b", re.I)
    for anchor in anchors:
        anchor_ids = {cell.index for cell in anchor.cells}
        header_line = next((line for line in layout.lines if anchor_ids & {cell.index for cell in line}), list(anchor.cells))
        ordered = sorted(header_line, key=lambda cell: cell.x)
        anchor_x = anchor.x
        prior = [cell for cell in ordered if cell.x < anchor_x and canonical(cell.text) != canonical(anchor.text)]
        following = [cell for cell in ordered if cell.x > anchor_x and canonical(cell.text) != canonical(anchor.text)]
        left = (prior[-1].x + anchor_x) / 2 if prior else max(0.0, anchor.box[0] - 0.08)
        right = (following[0].x + anchor_x) / 2 if following else min(1.0, anchor.box[2] + 0.20)
        cells: list = []
        for line in layout.lines:
            if not line or line[0].page != anchor.cells[0].page:
                continue
            y = median(cell.y for cell in line)
            if y <= anchor.box[3] + max(layout.line_height * 0.5, 0.006):
                continue
            line_text = layout.text(line)
            if stop.search(line_text):
                break
            selected = [cell for cell in line if cell.box[2] >= left and cell.box[0] <= right and re.search(r"[A-Za-z]", cell.text)]
            selected = [cell for cell in selected if not re.fullmatch(r"(?:KG|KGS|CBM|PKG|PKGS|PCS|PC|CT|MT|CFT|TOTAL|FREIGHT)", canonical(cell.text))]
            if not selected:
                continue
            text = layout.text(selected)
            if not re.search(r"[A-Za-z]{2,}", text) or stop.search(text):
                continue
            cells.extend(selected)
        if cells:
            value = layout.text(cells)
            result.append(_candidate(layout, "goods_description", anchor, cells, value, "bounded_description_column", anchor.strength * 5.0 - (median(cell.y for cell in cells) - anchor.y) * 4.0))
    return result


def _fallback_candidates(layout: Layout, field: str) -> list[FieldCandidate]:
    """Generate typed candidates when a noisy OCR stream loses its label.

    This is deliberately weak evidence: it only uses field type, normalized
    geometry, and a broad document header/footer zone.  It never invents a
    value and remains below an explicit semantic anchor in ranking.
    """
    result: list[FieldCandidate] = []
    for cell in layout.cells:
        value = cell.text.strip()
        valid = False
        zone_score = 0.0
        if field in {"invoice_number", "packing_list_number", "bl_number"}:
            valid = is_identifier(value)
            zone_score = (1.0 - cell.y) * 2.0 + cell.x
            if cell.y > 0.34 or cell.x < 0.45:
                valid = False
        elif field in {"invoice_date", "date", "shipment_date"}:
            valid = is_date(value)
            zone_score = (1.0 - cell.y) * 2.0 + cell.x
            if cell.y > 0.55:
                valid = False
        elif field == "total_amount":
            valid = is_number(value) and bool(re.search(r"[$€£¥]|USD|EUR|GBP|JPY|CNY|KRW", value, re.I))
            zone_score = cell.y + cell.x
            if cell.y < 0.55 or cell.x < 0.45:
                valid = False
        elif field == "weight_unit":
            parts = numeric_parts(value)
            if parts and parts[1] and is_weight_unit(parts[1]):
                value = parts[1]
                valid = True
            else:
                valid = is_weight_unit(value)
            zone_score = cell.y + cell.x
        if valid:
            result.append(_candidate(layout, field, None, [cell], value, "typed_zone_fallback", zone_score, True))
    return result


def candidates(layout: Layout, field: str) -> list[FieldCandidate]:
    if field == "goods_description":
        return _goods_candidates(layout)
    aliases = {field: ALIASES.get(field, ())}
    anchors = layout.anchors(aliases)
    predicate = _predicate(field)
    result: list[FieldCandidate] = []
    for anchor in anchors:
        # Inline values are common in B/L and invoice headers.
        inline = _inline(anchor.text, anchor.alias)
        if inline and predicate(inline) and canonical(inline) not in {canonical(alias) for alias in aliases[field]}:
            result.append(_candidate(layout, field, anchor, list(anchor.cells), inline, "inline", anchor.strength * 5.0))
        for score, cells, value, relation in layout.nearby(anchor, anchors, lambda text: text if predicate(text) else None):
            if not _anchor_scope(field, anchor, cells, relation):
                continue
            result.append(_candidate(layout, field, anchor, cells, value, relation, score))
    # Composite header lines such as ``B/L No. HG...`` and ``Vessel/voy. X``
    # are semantic candidates even when the complete phrase is not a compact
    # anchor span.
    for line in layout.lines:
        text = layout.text(line)
        upper = canonical(text)
        if field == "bl_number" and re.search(r"\b(?:B L|BILL OF LADING)\b", upper):
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9./-]{4,}", text):
                if is_identifier(token):
                    result.append(_candidate(layout, field, None, line, token, "composite_label", 3.5))
        if field == "vessel" and re.search(r"\b(?:VESSEL|EXPORT CARRIER)\b", upper):
            match = re.search(r"(?:VESSEL\s*/?\s*VOY\.?|VESSEL\s+NAME|EXPORT\s+CARRIER)\s*[:#-]?\s*(.+)$", text, re.I)
            if match and _predicate(field)(match.group(1)):
                result.append(_candidate(layout, field, None, line, match.group(1).strip(), "composite_label", 3.8))
    if not result:
        result.extend(_fallback_candidates(layout, field))
    return result


def resolve(layout: Layout, field: str) -> EvidenceField:
    values = [item for item in candidates(layout, field) if item.accepted]
    # Same semantic scalar should not be selected twice merely because the
    # label and its containing span both generated it.
    unique: dict[str, FieldCandidate] = {}
    for item in values:
        key = canonical(str(item.value))
        if key not in unique or item.score > unique[key].score:
            unique[key] = item
    values = sorted(unique.values(), key=lambda item: (item.score + (1.0 if item.semantic_anchor else 0.0), item.ocr_confidence or 0), reverse=True)
    if field in {"port_of_loading", "port_of_discharge"}:
        values = [item for item in values if canonical(str(item.value)) not in {"PLACE OF DELIVERY", "FINAL DESTINATION", "PLACE OF RECEIPT"}]
    if field in {"invoice_number", "invoice_date"}:
        # ``No. & Date of invoice`` is often one OCR label.  The value pair is
        # discovered from the compact header band by type, without a page-size
        # or document-template coordinate.
        header_lines = [line for line in layout.lines if "INVOICE" in canonical(layout.text(line)) and "DATE" in canonical(layout.text(line))]
        if header_lines:
            typed = []
            for line in layout.lines:
                y = sum(cell.y for cell in line) / len(line)
                if y > min(sum(cell.y for cell in x) / len(x) for x in header_lines) + 0.10:
                    continue
                for cell in line:
                    if field == "invoice_date" and is_date(cell.text):
                        typed.append((abs(cell.y - min(x.y for x in header_lines[0])), cell))
                    if field == "invoice_number" and is_identifier(cell.text):
                        typed.append((abs(cell.y - min(x.y for x in header_lines[0])), cell))
            if typed:
                cell = min(typed, key=lambda item: item[0])[1]
                return evidence(cell.text.strip(), source_text=cell.text, bbox=cell.polygon, confidence=cell.confidence, method="clean_composite_invoice_header")
    if field == "currency":
        currency_cells = []
        for cell in layout.cells:
            if re.search(r"(?:USD|EUR|GBP|JPY|CNY|KRW|[$€£¥])", cell.text, re.I):
                code = normalize_currency(cell.text) or ({"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(next((symbol for symbol in "$€£¥" if symbol in cell.text), "")))
                if code:
                    currency_cells.append((cell, code))
        if currency_cells:
            cell, code = currency_cells[-1]
            return evidence(code, source_text=cell.text, bbox=cell.polygon, confidence=cell.confidence, method="clean_currency_symbol_candidate")
    return values[0].evidence if values and values[0].evidence else missing("clean_scalar_no_candidate")


__all__ = ["ALIASES", "candidates", "resolve", "numeric_parts", "is_number", "is_quantity", "is_unit", "is_text"]
