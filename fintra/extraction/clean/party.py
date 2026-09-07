"""Document-independent party-block candidate generation and ranking."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from statistics import median

from fintra.domain.schema import EvidenceField, evidence, missing

from .candidate import FieldCandidate
from .layout import Anchor, Layout, canonical


PARTY_ALIASES = {
    "seller": ("SELLER", "EXPORTER", "SHIPPER EXPORTER", "SHIPPER"),
    "buyer": ("BUYER", "BUYER IF OTHER THAN CONSIGNEE", "CONSIGNEE", "IMPORTER"),
    "exporter": ("EXPORTER", "SELLER", "SHIPPER EXPORTER", "SHIPPER"),
    "consignee": ("CONSIGNEE", "CONSIGNEE NOT NEGOTIABLE", "CONSIGNEE/BUYER", "BUYER"),
    "shipper": ("SHIPPER", "SHIPPER EXPORTER", "CONSIGNOR", "CONSIGNOR SHIPPER", "EXPORTER"),
    "notify_party": ("NOTIFY PARTY", "NOTIFY", "NOTIFY PARTY/ADDRESS"),
}

MARKERS = {"CO", "LTD", "INC", "LLC", "CORP", "CORPORATION", "COMPANY", "LIMITED", "TRADING", "ENTERPRISE", "ENTERPRISES", "INDUSTRIES", "GROUP", "SYSTEMS", "SOLUTIONS"}
COUNTRIES = {"AUSTRALIA", "CANADA", "CHINA", "DENMARK", "EGYPT", "FRANCE", "GERMANY", "INDIA", "ITALY", "JAPAN", "KOREA", "MALAYSIA", "NORWAY", "SINGAPORE", "SPAIN", "TAIWAN", "THAILAND", "TURKEY", "UNITED STATES", "SOUTH AFRICA", "REP OF KOREA"}
NOISE = re.compile(r"\b(?:PHONE|TEL|FAX|EMAIL|TELEX|ADDRESS|PARTICULARS|DESCRIPTION|PACKAGE|PACKAGES|GOODS|WEIGHT|MEASUREMENT|PORT|PLACE|CARRIER|VOY(?:AGE)?|PRE[- ]?CARRIAGE|FREIGHT|LIMITATION|DELIVERY|DESTINATION|CHARGES|TOTAL|INVOICE|NUMBER|DATE|REFERENCE|REMARKS?|CERTIFICATION|COUNTRY|ORIGIN|TERMS|PAYMENT|SHIPPING|MARKS?|VESSEL|EXPORT|IMPORT|YES|NO|MUST|CHECK|BOX|ON BOARD|CLEAN|PREPAID|COLLECT)\b", re.I)

ROLE_WORDS = {
    "shipper": {"CONSIGNEE", "NOTIFY", "BUYER"},
    "exporter": {"CONSIGNEE", "NOTIFY", "BUYER"},
    "seller": {"CONSIGNEE", "NOTIFY", "BUYER"},
    "consignee": {"SHIPPER", "EXPORTER", "SELLER", "NOTIFY"},
    "buyer": {"SHIPPER", "EXPORTER", "SELLER", "NOTIFY"},
    "notify_party": {"SHIPPER", "EXPORTER", "SELLER", "CONSIGNEE", "BUYER"},
}


def _semantic_anchor(anchor: Anchor, field: str) -> bool:
    text = canonical(anchor.text)
    roles = {
        "shipper": ("SHIPPER", "CONSIGNOR", "EXPORTER", "SELLER"),
        "exporter": ("EXPORTER", "SELLER", "SHIPPER"),
        "seller": ("SELLER", "EXPORTER", "SHIPPER"),
        "consignee": ("CONSIGNEE", "BUYER"),
        "buyer": ("BUYER", "CONSIGNEE"),
        "notify_party": ("NOTIFY",),
    }
    if not text or re.search(r"\b(?:PHONE|TEL|FAX)\b", text):
        return False
    # Fuzzy OCR matching is useful for CONSIGNEE/CONSIGNOR-like corruption,
    # but it must not turn a clearly different role heading into this field's
    # anchor.  This is a semantic role guard, not a document/template rule.
    first = text.split()[0] if text else ""
    if first in ROLE_WORDS.get(field, set()):
        return False
    if any(word in text.split()[:3] for word in ROLE_WORDS.get(field, set())):
        return False
    # A value such as ``SHIPPER COMPANY LTD`` can itself contain the role
    # word.  Treat organization markers after the first token as evidence
    # that this is a value line, not a heading anchor.
    if first in {"SHIPPER", "EXPORTER", "SELLER", "CONSIGNEE", "BUYER", "NOTIFY"} and set(text.split()[1:]) & MARKERS:
        return False
    if field in {"consignee", "buyer"} and "OTHER THAN CONSIGNEE" in text:
        return False
    if any(re.match(r"^" + re.escape(role) + r"\b", text) for role in roles.get(field, ())):
        return True
    return bool(first and any(SequenceMatcher(None, first, role).ratio() >= 0.70 for role in roles.get(field, ())))


def _same_as(text: str) -> bool:
    """Recognize a complete SAME-AS party value, including OCR noise.

    The value is meaningful only when the whole line is a party reference.
    Comparing the role token with a small semantic vocabulary lets us retain
    ``SAME AS CONSGNEE`` without using a document-specific literal or
    truncating it during inline-heading cleanup.
    """
    words = canonical(text).split()
    if len(words) < 3 or words[:2] != ["SAME", "AS"]:
        return False
    role = " ".join(words[2:])
    allowed = ("CONSIGNEE", "SHIPPER", "BUYER", "EXPORTER", "SELLER", "ABOVE")
    if role in allowed:
        return True
    return any(
        len(role) >= 5 and SequenceMatcher(None, role, expected).ratio() >= 0.76
        for expected in allowed
    )


def _contextual_heading_rejected(layout: Layout, anchor: Anchor, field: str) -> bool:
    """Reject role-word mentions that are not party-section headings.

    B/L boilerplate often contains ``PARTICULARS FURNISHED BY SHIPPER``.
    ``Layout.anchors`` quite correctly finds the word SHIPPER, but it is a
    cargo-section label, not the start of a shipper block.  Looking at the
    complete normalized OCR line keeps this rule layout-relative and avoids
    a fixed page/template window.
    """
    if field not in {"shipper", "exporter", "seller"}:
        return False
    anchor_ids = {cell.index for cell in anchor.cells}
    for line in layout.lines:
        if not anchor_ids.intersection(cell.index for cell in line):
            continue
        context = canonical(layout.text(line))
        if re.search(r"\b(?:PARTICULARS|FURNISHED|BY)\b", context):
            return True
    return False


def _typed_party(text: str) -> bool:
    value = " ".join(text.split()).strip(" ,:;-&")
    upper = canonical(value)
    if not value or _same_as(value) is False and upper in COUNTRIES:
        return False
    if _same_as(value):
        return True
    if NOISE.search(value) or re.search(r"\bV\.?\s*\d+\b", value, re.I):
        return False
    if re.match(r"^[\d+()/-]", value) or any(word in upper.split() for word in ("TEL", "FAX", "PHONE", "EMAIL")):
        return False
    # OCR frequently corrupts one or two letters in an organization line into
    # digits.  Keep a candidate when strong organization markers are present;
    # reject numeric/address lines that have no such marker.
    if re.search(r"\d", value) and not set(upper.split()) & MARKERS:
        return False
    if "," in value and not set(upper.split()) & MARKERS:
        return False
    return bool(re.search(r"[A-Za-z]{2,}", value))


def _trim_party_value(text: str) -> str:
    """Keep the organization prefix when one OCR cell includes its address.

    This is a typed boundary, not a company-specific rule: organization
    markers followed by a postal/numbered address delimit the party value.
    Address text remains in ``source_text`` and the evidence bbox, while the
    canonical value is the organization itself.
    """
    value = " ".join(str(text).split()).strip(" ,:;-&")
    marker = re.search(
        r"\b(?:CO(?:MPANY)?\.?\s*,?\s*(?:LTD\.?|LIMITED)|"
        r"LTD\.?|LIMITED|INC(?:ORPORATED)?\.?|LLC|CORP(?:ORATION)?\.?|"
        r"GROUP|TRADING|INDUSTR(?:Y|IES)|ENTERPRISES?)\b",
        value,
        re.I,
    )
    if not marker:
        return value
    tail = value[marker.end():]
    if re.search(r"\d|\b(?:ROAD|RD|STREET|ST|AVENUE|AVE|DRIVE|DR|LANE|LN|"
                 r"BOULEVARD|BLVD|HIGHWAY|HWY|FLOOR|UNIT|SUITE|BUILDING|"
                 r"SEOUL|KOREA|JAPAN|AUSTRALIA|CHINA|USA|UNITED STATES)\b", tail, re.I):
        return value[:marker.end()].strip(" ,:;-&")
    return value


def _line_clusters(line, gap: float = 0.055):
    clusters = []
    for cell in line:
        if not clusters or cell.box[0] - clusters[-1][-1].box[2] > gap:
            clusters.append([cell])
        else:
            clusters[-1].append(cell)
    return clusters


def _candidate(layout: Layout, field: str, anchor: Anchor, cells, relation: str, score: float) -> FieldCandidate:
    source_text = layout.text(cells)
    value = _trim_party_value(source_text)
    ev = evidence(value, source_text=source_text, bbox=layout.box(cells), confidence=min((c.confidence for c in cells if c.confidence is not None), default=None), method="clean_party_candidate")
    box = (min(c.box[0] for c in cells), min(c.box[1] for c in cells), max(c.box[2] for c in cells), max(c.box[3] for c in cells))
    return FieldCandidate(field, value, ev.source_text, tuple(c.index for c in cells), ev.bbox, ev.confidence, anchor.alias, relation, box, True, "party_block", score, evidence=ev)


def candidates(layout: Layout, field: str, aliases: tuple[str, ...] | None = None) -> list[FieldCandidate]:
    aliases = aliases or PARTY_ALIASES[field]
    all_anchors = layout.anchors({name: PARTY_ALIASES[name] for name in PARTY_ALIASES})
    anchors = [
        anchor for anchor in all_anchors
        if anchor.field == field
        and _semantic_anchor(anchor, field)
        and not _contextual_heading_rejected(layout, anchor, field)
    ]
    # A lone fuzzy ``EXPORT`` token is often the left edge of an
    # ``EXPORT REFERENCES`` heading, not a shipper/exporter role label.
    if field in {"shipper", "exporter", "seller"}:
        anchors = [anchor for anchor in anchors if not (canonical(anchor.text) == "EXPORT" and any(
            cell.page == anchor.cells[0].page and cell.y >= anchor.y - 0.01 and cell.y <= anchor.y + 0.01 and cell.x > anchor.x and canonical(cell.text).startswith("REFERENC")
            for line in layout.lines for cell in line
        ))]
    # ``Buyer if other than consignee`` is a semantic exclusion, not a
    # consignee anchor.  When that label is the only upper-block role, the
    # consignee is recoverable from the residual organization line in the
    # exporter-side party block bounded by the next transport/party anchor.
    if field == "consignee":
        anchors = [anchor for anchor in anchors if "OTHER THAN CONSIGNEE" not in canonical(anchor.text)]
        if not anchors:
            exporter = next((item for item in all_anchors if item.field == "exporter" and _semantic_anchor(item, "exporter")), None)
            boundary = min((item.box[1] for item in all_anchors if item.box[1] > (exporter.box[3] if exporter else 0.0) and item.field != "exporter" and _semantic_anchor(item, item.field) and exporter is not None and abs(item.x - exporter.x) < 0.25), default=(exporter.box[3] + 0.22 if exporter else 0.25))
            if exporter:
                anchors = [Anchor(field, "residual party block", exporter.cells, max(0.6, exporter.strength))]
                residual_boundary = boundary
            else:
                residual_boundary = 0.0
        else:
            residual_boundary = None
    else:
        residual_boundary = None
    if field == "shipper" and not anchors:
        # If the shipper heading is too corrupted for a role anchor, use the
        # bounded first party block before the next consignee/notify block.
        boundaries = [item.box[1] for item in all_anchors if item.field in {"consignee", "notify_party"} and _semantic_anchor(item, item.field)]
        boundary_y = min(boundaries, default=0.42)
        for line in layout.lines:
            y = median(cell.y for cell in line)
            if not (0.03 < y < boundary_y):
                continue
            for cluster in _line_clusters([cell for cell in line if cell.x < 0.52]):
                text = layout.text(cluster)
                if _typed_party(text):
                    anchor = Anchor(field, "party block start", tuple(cluster), 0.55)
                    return [_candidate(layout, field, anchor, cluster, "party_block_fallback", 1.5 - y)]
    # Only semantic role headings are protected from value generation.  A
    # noisy value line can contain words such as SHIPPER/CONSIGNEE and is
    # intentionally present in ``all_anchors`` for diagnostics, but must not
    # be removed from the candidate pool.
    semantic_anchors = [anchor for anchor in all_anchors if _semantic_anchor(anchor, anchor.field)]
    labels = {cell.index for anchor in semantic_anchors for cell in anchor.cells}
    anchor_cell_ids = {cell.index for anchor in anchors for cell in anchor.cells}
    residual_mode = field == "consignee" and any(anchor.alias == "residual party block" for anchor in anchors)
    result: list[FieldCandidate] = []
    for anchor in anchors:
        boundary = residual_boundary if residual_boundary is not None else min((other.box[1] for other in all_anchors if other is not anchor and _semantic_anchor(other, other.field) and other.box[1] > anchor.box[3] and abs(other.x - anchor.x) < 0.20), default=anchor.box[3] + 0.20)
        for line in layout.lines:
            if not line or line[0].page != anchor.cells[0].page:
                continue
            y = median(cell.y for cell in line)
            if not (y >= anchor.box[3] - 0.01 and y < boundary):
                continue
            clusters = _line_clusters([cell for cell in line if cell.index not in labels])
            for cluster in clusters:
                if not cluster:
                    continue
                # Generate both a compact organization line and short
                # prefixes of OCR cells.  Address/contact cells can be
                # geometrically adjacent to the organization on noisy forms;
                # ranking must see the organization as its own candidate.
                variants = [cluster]
                for stop in range(1, min(4, len(cluster)) + 1):
                    variants.append(cluster[:stop])
                seen: set[tuple[int, ...]] = set()
                for variant in variants:
                    key = tuple(cell.index for cell in variant)
                    if key in seen:
                        continue
                    seen.add(key)
                    # A residual consignee block starts after the exporter
                    # value.  Never return the anchor's own OCR cells as the
                    # next party candidate.
                    if set(key) & anchor_cell_ids:
                        continue
                    # In a residual block the first line after the role
                    # heading is usually the role's own organization value.
                    # Start the next-party search below that line instead of
                    # allowing the exporter to win by proximity.
                    if residual_mode and y <= anchor.y + max(layout.line_height * 2.2, 0.025):
                        continue
                    center = median(cell.x for cell in variant)
                    # Party blocks are column-scoped.  Do not absorb a
                    # same-line/right-column carrier, port, legal-text, or
                    # transport candidate merely because it is below the
                    # role heading.  The bound is normalized page geometry
                    # and applies symmetrically to both sides.
                    if residual_mode and abs(center - anchor.x) > 0.30:
                        continue
                    if not residual_mode and (
                        center < anchor.x - 0.30
                        or cluster[0].box[0] > anchor.box[2] + 0.32
                    ):
                        continue
                    text = layout.text(variant)
                    if not _typed_party(text):
                        continue
                    score = anchor.strength * 4 - abs(y - anchor.y) * 9 - abs(center - anchor.x) * 1.2
                    if y <= anchor.y + max(layout.line_height * 1.8, 0.018):
                        score += 1.4
                    words = set(canonical(text).split())
                    score += 1.5 if words & MARKERS else 0.0
                    score += 2.0 if _same_as(text) else 0.0
                    # Prefer a complete organization line, but penalize
                    # accidental address tails instead of accepting them.
                    score -= max(0, len(variant) - 4) * 0.15
                    result.append(_candidate(layout, field, anchor, variant, "party_block", score))
    return result


def resolve(layout: Layout, field: str) -> EvidenceField:
    values = candidates(layout, field)
    if not values:
        return missing("clean_party_no_candidate")
    # If OCR appends a one-letter initial from an adjacent fragment, retain
    # the complete organization candidate only when its suffix is also
    # independently observed in the same party block.  This is a structural
    # duplicate-fragment rule, not a company-specific exception.
    canonical_values = {canonical(str(item.value)) for item in values}
    def rank(item: FieldCandidate) -> tuple[float, float]:
        text = str(item.value).strip()
        match = re.match(r"^([A-Za-z])\.\s+(.+)$", text)
        suffix_match = re.match(r"^(.+?)\s+([A-Za-z])\.$", text)
        penalty = 0.75 if match and canonical(match.group(2)) in canonical_values else 0.0
        if suffix_match and canonical(suffix_match.group(1)) in canonical_values:
            penalty = max(penalty, 0.75)
        return item.score - penalty, item.ocr_confidence or 0
    values.sort(key=rank, reverse=True)
    return values[0].evidence or missing("clean_party_no_candidate")


__all__ = ["PARTY_ALIASES", "candidates", "resolve"]
