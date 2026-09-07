"""Typed scalar candidate generation for Extractor v2."""

from __future__ import annotations

import re
from datetime import date
from difflib import SequenceMatcher
from typing import Callable

from fintra.normalization.values import normalize_currency, normalize_date, parse_amount

from .candidate import Candidate, select
from .layout import Anchor, Cell, Layout, canonical
from .specs import SPECS


INCOTERMS = {"FOB", "CIF", "CFR", "DAF", "DDP", "DDU", "DEQ", "CFS", "CY"}
UNITS = {"EA", "EACH", "PCS", "PC", "PKG", "PKGS", "BOX", "CTN", "CARTON", "KGS", "KG", "G", "GRAM", "CBM", "M3", "MT", "TON", "SET", "SETS", "PAIR", "DOZ"}
STOP = re.compile(r"\b(?:DESCRIPTION|QUANTITY|QTY|UNIT PRICE|AMOUNT|TOTAL|SUBTOTAL|PACKAGE|PACKAGES|WEIGHT|PORT|VESSEL|VOYAGE|CONSIGNEE|SHIPPER|NOTIFY|BUYER|SELLER|EXPORTER)\b", re.I)


def _clean(value: str) -> str:
    return " ".join(str(value or "").replace("?쇳몴", ",").split()).strip(" :;-|/")


def _collapse_identifier_fragments(value: str) -> str:
    words = _clean(value).split()
    if len(words) < 2:
        return _clean(value)
    result = []
    for index, word in enumerate(words):
        compact_word = canonical(word).replace(" ", "")
        later = [canonical(other).replace(" ", "") for other in words[index + 1:]]
        if compact_word and any(len(compact_word) >= 2 and compact_word in other for other in later):
            continue
        result.append(word)
    return " ".join(result)


def _remove_alias(text: str, alias: str) -> str | None:
    raw = _clean(text)
    pattern = re.compile(r"^\s*" + re.escape(alias).replace(r"\ ", r"\s+") + r"\s*[:#-]?\s*(.*?)\s*$", re.I)
    match = pattern.match(raw)
    return _clean(match.group(1)) if match and match.group(1).strip() else None


def _is_date(value: str) -> bool:
    if normalize_date(value):
        return True
    return bool(re.search(r"\b\d{1,4}[./-]\d{1,2}(?:[./-]\d{1,4})?\b", value)) or bool(re.search(r"\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)", value, re.I))


def _is_number(value: str) -> bool:
    return bool(re.search(r"\d", value)) and parse_amount(value) is not None and len(canonical(value).split()) <= 5


def _is_currency(value: str) -> bool:
    return normalize_currency(value) is not None or bool(re.search(r"\b(?:USD|EUR|GBP|JPY|CNY|KRW|HKD|SGD|AUD|CAD)\b|[$€£¥]", value, re.I))


def _is_unit(value: str) -> bool:
    return canonical(value) in UNITS or bool(re.fullmatch(r"[A-Za-z]{1,8}", value.strip())) and canonical(value) not in {"TOTAL", "AMOUNT", "PRICE"}


def _is_identifier(value: str) -> bool:
    text = canonical(value)
    return (
        bool(re.search(r"[A-Z0-9]", text))
        and len(text) >= 2
        and text not in {"BILL", "LADING", "OF", "PO", "NO", "NUMBER", "INVOICE", "DOCUMENT", "BOOKING", "CONTAINER", "SEAL", "PO NO", "P O NO", "INVOICE NO", "INV NO", "B L NO", "BL NO", "DOCUMENT NO", "NAME"}
        and not STOP.fullmatch(text)
        and len(text.split()) <= 8
    )


def _is_location(value: str) -> bool:
    upper = canonical(value)
    return bool(re.search(r"[A-Z]{2,}", upper)) and not re.search(
        r"\b(?:FOB|CIF|CFR|DAF|DDP|DDU|DEQ|CFS|CY|VESSEL|VOYAGE|CONSIGNEE|SHIPPER|BUYER|SELLER|"
        r"PORT|PLACE|FREIGHT|PAYABLE|CARRIER|CONTAINER|DELIVERY|RECEIPT|NAME|COUNTRY|ADDRESS|VIA|"
        r"THIRD PARTY|RECEIVED|ACCEPTANCE|RATE)\b",
        upper,
    )


def _is_vessel(value: str) -> bool:
    upper = canonical(value)
    return (
        len(upper) >= 3
        and upper not in {"VESSEL", "VESSEL NAME", "NAME", "VOY", "VOYAGE"}
        and "," not in value
        and not re.search(r"\b(?:FOB|CIF|CFR|DAF|DDP|DDU|DEQ|CFS|CY|PORT|PLACE|COUNTRY|ADDRESS|VOYAGE|V\s*\d+)\b", upper)
        and not _is_number(value)
    )


def _anchor_compatible(field: str, anchor: Anchor) -> bool:
    """Prevent fuzzy aliases from crossing explicit semantic role labels."""
    observed = canonical(anchor.text)
    if field == "port_of_loading":
        if "DISCHARGE" in observed:
            return False
        if not (observed.startswith("PORT OF LOADING") or observed.startswith("PLACE OF LOADING") or observed.startswith("LOADING PORT")):
            return False
    if field == "port_of_discharge":
        if "LOADING" in observed:
            return False
        if not (observed.startswith("PORT OF DISCHARGE") or observed.startswith("PLACE OF DISCHARGE") or observed.startswith("DISCHARGE PORT")):
            return False
    if field == "gross_weight" and "NET" in observed:
        return False
    if field == "net_weight" and "GROSS" in observed:
        return False
    if field == "vessel" and not any(token in observed for token in ("VESSEL", "EXPORT CARRIER")):
        return False
    if field == "voyage_number" and not any(token in observed for token in ("VOY", "VOYAGE")):
        return False
    identifier_prefixes = {
        "invoice_number": ("INVOICE", "INV"),
        "bl_number": ("BILL OF LADING", "B L", "BL"),
        "lc_number": ("L C", "LC", "LETTER OF CREDIT"),
        "purchase_order_number": ("PURCHASE ORDER", "P O", "PO"),
        "invoice_reference": ("INVOICE", "REFERENCE", "REF"),
        "document_number": ("DOCUMENT", "PACKING LIST", "DOC"),
        "container_number": ("CONTAINER",),
        "seal_number": ("SEAL",),
        "booking_number": ("BOOKING",),
    }
    if field in identifier_prefixes and not any(token in observed for token in identifier_prefixes[field]):
        return False
    date_prefixes = {
        "invoice_date": ("INVOICE",), "lc_date": ("L C", "LC", "LETTER OF CREDIT"),
        "departure_date": ("DEPARTURE", "ETD"), "arrival_date": ("ARRIVAL", "ETA"),
        "shipment_date": ("SHIPMENT", "ON BOARD", "SHIPPED"),
        "document_date": ("DOCUMENT", "PACKING LIST"),
    }
    if field in date_prefixes and not any(token in observed for token in date_prefixes[field]):
        return False
    return True


def _predicate(kind: str) -> Callable[[str], bool]:
    return {
        "date": _is_date,
        "amount": _is_number,
        "quantity": _is_number,
        "weight": _is_number,
        "currency": _is_currency,
        "unit": _is_unit,
        "identifier": _is_identifier,
        "location": _is_location,
        "vessel": _is_vessel,
        "code": lambda value: canonical(value) in INCOTERMS or bool(re.search(r"[A-Za-z]{2,}", value)),
        "measurement": _is_number,
        "text": lambda value: bool(re.search(r"[A-Za-z]{2,}", value)) and not STOP.fullmatch(canonical(value)),
    }.get(kind, lambda value: bool(value.strip()))


def _score(kind: str, value: str, relation: str, anchor: Anchor, distance: float) -> float:
    score = anchor.strength * 4.0 + (1.5 if relation == "right" else 0.8 if relation == "inline" else 0.0) - distance * 7.0
    if kind in {"date", "amount", "quantity", "weight"} and _is_number(value):
        score += 1.0
    if kind == "location" and "," in value:
        score += 0.7
    if kind == "vessel" and len(value.split()) >= 2:
        score += 0.5
    if kind == "identifier":
        # Prefer the complete identifier region over a short OCR fragment
        # emitted from the same anchored line.
        score += min(len(canonical(value)) / 20.0, 1.0)
    return score


def _candidates(layout: Layout, field: str, all_anchors: list[Anchor]) -> list[Candidate]:
    spec = SPECS[field]
    output: list[Candidate] = []
    for anchor in layout.anchors(field, spec.aliases):
        if not _anchor_compatible(field, anchor):
            continue
        # Inline value in a merged OCR line/region.
        for cell in anchor.cells:
            value = _remove_alias(cell.text, anchor.alias)
            if (value and spec.kind == "identifier" and
                    canonical(value) in set(canonical(anchor.text).split())):
                value = None
            if value and _predicate(spec.kind)(value):
                output.append(Candidate(field, value, cell.text, anchor.text, (cell,), anchor, "inline",
                                        True, "label_value", _score(spec.kind, value, "inline", anchor, 0.0)))
        for cells, relation, distance in layout.adjacent(anchor, all_anchors):
            for size in range(1, min(4, len(cells)) + 1):
                chosen = tuple(cells[:size]) if relation == "right" else tuple(cells[:size])
                value = _clean(layout.text(chosen))
                if spec.kind == "identifier":
                    value = _collapse_identifier_fragments(value)
                if not value or not _predicate(spec.kind)(value):
                    continue
                if spec.kind == "identifier" and canonical(value) in set(canonical(anchor.text).split()):
                    continue
                if spec.kind == "vessel" and canonical(value) in INCOTERMS:
                    continue
                output.append(Candidate(field, value, layout.text(chosen), anchor.text, chosen, anchor, relation,
                                        True, "label_value", _score(spec.kind, value, relation, anchor, distance) - size * 0.04))
    if spec.kind == "identifier":
        # OCR may expose both a short overlapping fragment and the complete
        # identifier from one semantic anchor.  Keep the longest evidence
        # candidate; this is text+same-anchor arbitration, not a value list.
        compact_values = [(candidate, canonical(candidate.value).replace(" ", "")) for candidate in output]
        output = [candidate for candidate, value in compact_values if not any(
            candidate is not other
            and value
            and value != other_value
            and value in other_value
            and candidate.anchor is not None
            and other.anchor is not None
            and candidate.anchor.field == other.anchor.field
            and canonical(candidate.anchor.text) == canonical(other.anchor.text)
            for other, other_value in compact_values
        )]
    return output


def _fallback(layout: Layout, field: str) -> list[Candidate]:
    spec = SPECS[field]
    predicate = _predicate(spec.kind)
    cells = [cell for cell in layout.cells if predicate(cell.text) and not STOP.search(cell.text)]
    candidates = []
    for cell in cells:
        # Unanchored candidates are deliberately lower ranked than evidence
        # attached to a semantic label.
        candidates.append(Candidate(field, _clean(cell.text), cell.text, None, (cell,), None, "typed_fallback",
                                    True, "unanchored", 0.25 + (cell.confidence or 0.0) * 0.1))
    return candidates


def resolve(layout: Layout, field: str, all_anchors: list[Anchor] | None = None) -> dict:
    all_anchors = all_anchors or layout.all_anchors({field: SPECS[field].aliases})
    candidates = _candidates(layout, field, all_anchors)
    if not candidates and field in {"currency", "incoterm"}:
        candidates = _fallback(layout, field)
    return select(layout, candidates, method="v2_scalar_rank")


__all__ = ["resolve"]
