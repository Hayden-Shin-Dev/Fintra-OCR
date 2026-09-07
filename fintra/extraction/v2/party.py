"""Anchor-relative party block candidate generation and ranking."""

from __future__ import annotations

import re
from typing import Iterable

from .candidate import Candidate, select
from .layout import Anchor, Cell, Layout, canonical
from .specs import PARTY_FIELDS, SPECS


COUNTRIES = {
    "USA", "US", "UNITED STATES", "CANADA", "MEXICO", "CHINA", "JAPAN", "KOREA",
    "SOUTH KOREA", "TAIWAN", "THAILAND", "VIETNAM", "INDIA", "SINGAPORE", "MALAYSIA",
    "INDONESIA", "PHILIPPINES", "FRANCE", "GERMANY", "ITALY", "SPAIN", "UK", "UNITED KINGDOM",
    "CHILE", "BRAZIL", "AUSTRALIA", "BELGIUM", "NETHERLANDS", "HONG KONG",
}
REJECT = re.compile(r"\b(?:TEL|TELEPHONE|PHONE|FAX|EMAIL|E[- ]?MAIL|WWW|HTTP|ZIP|POSTAL|P[.]?O[.]? BOX|STREET|ROAD|RD[.]?|AVENUE|AVE[.]?|DISTRICT|CITY|COUNTRY|ATTN|CONTACT|ADDRESS|UNLESS|PLEASE|PROVIDE|COMPLETE|ORDER)\b", re.I)
TRANSPORT = re.compile(r"\b(?:VESSEL|VOY(?:AGE)?|PORT|FOB|CIF|CFR|DAF|DDP|DDU|DEQ|CFS|CY|ETD|ETA|B/L|BILL OF LADING)\b", re.I)
HEADING_ONLY = re.compile(r"^(?:SELLER|BUYER|EXPORTER|SHIPPER|CONSIGNEE|CONSIGNED TO|NOTIFY|NOTIFY PARTY|SOLD TO|BILL TO|SHIP TO)$", re.I)
SAME_AS = re.compile(r"^SAME\s+AS\s+(CONSIGNEE|SHIPPER|BUYER|EXPORTER|SELLER)$", re.I)

SAME_AS_COMPATIBILITY = {
    "buyer": {"consignee", "buyer"},
    "consignee": {"buyer", "consignee"},
    "seller": {"exporter", "seller"},
    "exporter": {"seller", "exporter", "shipper"},
    "shipper": {"exporter", "shipper"},
    "notify_party": {"consignee", "buyer", "notify_party"},
}

ROLE_HEADINGS = {
    # Explicit role namespaces are intentionally disjoint. Cross-role
    # relationships are represented only by a complete SAME AS expression.
    "seller": {"SELLER", "SELLER NAME", "SOLD BY"},
    "exporter": {"EXPORTER", "SHIPPER/EXPORTER", "SHIPPED BY", "EXPORTED BY"},
    "shipper": {"SHIPPER", "SHIPPER/EXPORTER", "CONSIGNOR", "CONSIGNOR/SHIPPER"},
    "buyer": {"BUYER", "SOLD TO", "BILL TO", "BUYER IF OTHER THAN CONSIGNEE"},
    "consignee": {"CONSIGNEE", "CONSIGNED TO", "SHIP TO"},
    "notify_party": {"NOTIFY", "NOTIFY PARTY", "ALSO NOTIFY"},
    "carrier": {"CARRIER", "EXPORT CARRIER", "FORWARDER", "FORWARDING AGENT"},
    "bank": {"BANK", "ISSUING BANK", "ADVISING BANK"},
    "manufacturer": {"MANUFACTURER", "MADE BY"},
    "signatory_company": {"AUTHORIZED SIGNATURE", "SIGNED BY", "SIGNATURE"},
}


def _same_as_target(text: str) -> str | None:
    match = SAME_AS.fullmatch(" ".join(str(text or "").split()))
    return match.group(1).lower() if match else None


def _anchor_is_compatible(anchor: Anchor, field: str) -> bool:
    """Reject a fuzzy role collision before candidate generation."""

    raw = " ".join(str(anchor.text or "").split()).strip()
    # AI-Hub forms frequently append a parenthesized qualifier to the role
    # heading, e.g. ``NOTIFY PARTY (COMPLETE NAME, ADDRESS)``.  Treat only
    # the heading prefix as semantic; phone/address text after the prefix is
    # not a party label.  This is layout-independent and does not use values.
    heading_prefix = raw.split("(", 1)[0].strip(" :;-|")
    observed = canonical(heading_prefix)
    allowed = {canonical(item) for item in ROLE_HEADINGS.get(field, ())}
    if observed in allowed:
        return True
    # A heading may be OCR-split or carry a short qualifier without brackets.
    # Accept only a prefix match when the suffix is not a phone/contact marker.
    for item in allowed:
        if observed.startswith(item + " "):
            suffix = observed[len(item):].strip()
            if not re.search(r"\b(?:PHONE|TEL|TELEPHONE|FAX|EMAIL|NO)\b", suffix):
                return True
    # A fuzzy alias such as CONSIGNOR can match the visible CONSIGNEE heading.
    # If the observed heading is an explicit competing role, it is not a
    # candidate for this field even when the string similarity passes.
    competing = {
        "SELLER", "EXPORTER", "SHIPPER", "CONSIGNOR", "BUYER", "CONSIGNEE", "NOTIFY", "NOTIFY PARTY", "ALSO NOTIFY",
        "CARRIER", "EXPORT CARRIER", "FORWARDER", "FORWARDING AGENT", "BANK", "ISSUING BANK",
        "ADVISING BANK", "MANUFACTURER", "MADE BY", "AUTHORIZED SIGNATURE", "SIGNED BY", "SIGNATURE",
    }
    observed_words = set(observed.split())
    allowed_words = set().union(*(set(item.split()) for item in allowed)) if allowed else set()
    return not (observed_words & competing and not observed_words.issubset(allowed_words))


def _organization_like(value: str) -> float:
    upper = canonical(value)
    if not upper or HEADING_ONLY.fullmatch(upper):
        return 0.0
    if upper in COUNTRIES or upper.replace(" ", "") in COUNTRIES:
        return 0.0
    if REJECT.search(upper) or TRANSPORT.search(upper):
        return 0.0
    if SAME_AS.fullmatch(value.strip()):
        return 4.0
    score = 1.0
    if re.search(r"\b(?:CO|COMPANY|CORP|CORPORATION|LTD|LIMITED|INC|LLC|PLC|TRADING|INDUSTRIES|INTERNATIONAL|SA|GMBH)\b", upper):
        score += 2.5
    if re.search(r"[A-Z]{3,}", upper):
        score += 0.5
    if len(upper.split()) >= 2:
        score += 0.5
    return score


def _candidate_value(text: str, alias: str) -> str | None:
    raw = " ".join(text.split()).strip(" :;-|")
    pattern = re.compile(r"^\s*" + re.escape(alias).replace(r"\ ", r"\s+") + r"\s*[:#-]?\s*(.*?)\s*$", re.I)
    match = pattern.match(raw)
    if match:
        value = match.group(1).strip(" :;-|")
        return value or None
    return None


def _dedupe_cells(cells: Iterable[Cell]) -> list[Cell]:
    """Remove only text+geometry duplicate fragments inside one party line.

    OCR commonly emits a large company region and a smaller overlapping
    suffix region (for example ``... CO., LTD.``).  The smaller region is
    discarded only when its normalized text is contained in the larger text
    and the two boxes overlap or touch; unrelated adjacent company/address
    cells remain intact.
    """
    ordered = sorted(cells, key=lambda item: (item.box[0], item.box[1], -len(item.text)))
    kept: list[Cell] = []
    for cell in ordered:
        current = canonical(cell.text)
        if not current:
            continue
        duplicate = False
        for prior in kept:
            previous = canonical(prior.text)
            overlap_x = min(cell.box[2], prior.box[2]) - max(cell.box[0], prior.box[0])
            overlap_y = min(cell.box[3], prior.box[3]) - max(cell.box[1], prior.box[1])
            touching = cell.box[0] <= prior.box[2] + max(cell.height, prior.height) * 0.35
            if (current in previous or previous in current) and (overlap_x > 0 and overlap_y > 0 or touching):
                if len(current) <= len(previous):
                    duplicate = True
                    break
                kept.remove(prior)
        if not duplicate:
            kept.append(cell)
    return kept


def _line_candidates(layout: Layout, anchor: Anchor, all_anchors: list[Anchor], field: str) -> Iterable[Candidate]:
    spec = SPECS[field]
    for cells, relation, distance in layout.adjacent(anchor, all_anchors):
        cells = _dedupe_cells(cells)
        text = layout.text(cells).strip()
        if not text:
            continue
        value = _candidate_value(text, anchor.alias) or text
        same_as_target = _same_as_target(value)
        if same_as_target is not None and same_as_target not in SAME_AS_COMPATIBILITY.get(field, set()):
            continue
        quality = _organization_like(value)
        if quality <= 0:
            continue
        yield Candidate(field, value, text, anchor.text, tuple(cells), anchor, relation,
                        True, "party_block", anchor.strength * 4.0 + quality - distance)

    # A label and value may be emitted as one OCR region.
    for cell in anchor.cells:
        value = _candidate_value(cell.text, anchor.alias)
        if value and _organization_like(value) > 0:
            yield Candidate(field, value, cell.text, anchor.text, (cell,), anchor, "inline",
                            True, "party_block", anchor.strength * 6.0 + _organization_like(value))

    # A party block can be multiline.  Stop at the next competing party label
    # and retain only a coherent text block, never an unbounded page window.
    page = anchor.cells[0].page
    competing = [item for item in all_anchors if item.field in PARTY_FIELDS and item.field != field and item.cells[0].page == page and item.y > anchor.y]
    boundary = min((item.y for item in competing), default=anchor.y + 0.16)
    # Party blocks may be left, right, or stacked.  Use the anchor's
    # normalized column as the reference instead of a page-template x cutoff.
    column_left = max(0.0, anchor.box[0] - 0.03)
    column_right = min(1.0, anchor.box[2] + 0.45)
    lines = [line for line in layout.lines if line and line[0].page == page and anchor.y < sum(x.y for x in line) / len(line) < boundary]
    for line in lines[:4]:
        cells = _dedupe_cells(cell for cell in line if cell.y > anchor.y and column_left <= cell.x <= column_right)
        if not cells:
            continue
        value = layout.text(cells).strip()
        quality = _organization_like(value)
        if quality > 0:
            yield Candidate(field, value, layout.text(cells), anchor.text, tuple(cells), anchor, "party_block_line",
                            True, "party_block", anchor.strength * 3.5 + quality - abs(sum(x.y for x in cells) / len(cells) - anchor.y) * 5.0)


def resolve(
    layout: Layout,
    field: str,
    all_anchors: list[Anchor] | None = None,
    resolved_parties: dict[str, dict] | None = None,
) -> dict:
    aliases = SPECS[field].aliases
    anchors = [anchor for anchor in layout.anchors(field, aliases) if _anchor_is_compatible(anchor, field)]
    all_anchors = all_anchors or layout.all_anchors({name: SPECS[name].aliases for name in PARTY_FIELDS if name in SPECS})
    candidates = [candidate for anchor in anchors for candidate in _line_candidates(layout, anchor, all_anchors, field)]
    # Explicit SAME AS values must survive generic heading filtering, but only
    # when the referenced role is semantically compatible with this field.
    # Otherwise a shipper resolver could incorrectly return SAME AS CONSIGNEE
    # just because it was visible elsewhere on the page.
    for cell in layout.cells:
        target = _same_as_target(cell.text)
        if target is None or target not in SAME_AS_COMPATIBILITY.get(field, set()):
            continue
        target_result = (resolved_parties or {}).get(target)
        target_value = target_result.get("value") if isinstance(target_result, dict) else None
        value = target_value or cell.text.strip()
        candidates.append(Candidate(
            field,
            value,
            cell.text,
            None,
            (cell,),
            None,
            "same_as_role",
            True,
            "party_block",
            6.0 if target_value else 5.0,
        ))
    return select(layout, candidates, method="v2_party_rank")


__all__ = ["resolve"]
