"""Conservative, evidence-preserving document field extraction rules."""

from __future__ import annotations

import re
import struct
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable

from fintra.domain.schema import (
    BillOfLading,
    CommercialInvoice,
    DocumentMetadata,
    EvidenceField,
    LineItem,
    PackingList,
    ambiguous,
    evidence,
    missing,
)
from fintra.ocr.adapter import OCRRegion, OCRResult


def _canonical(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def _area(region: OCRRegion) -> float:
    x1, y1, x2, y2 = region.bbox
    return max(1.0, (x2 - x1) * (y2 - y1))


def _is_contained_fragment(candidate: OCRRegion, larger: OCRRegion) -> bool:
    """Drop an OCR fragment that duplicates text inside a larger region.

    Paddle may emit a full line and a second, partially overlapping crop of
    the same line.  Keeping both makes party names and table descriptions
    repeat text.  This only removes a smaller region when its box is almost
    contained by the larger box and its canonical text is a substring; two
    adjacent words or independent table cells are left untouched.
    """
    if candidate.page != larger.page or _area(larger) <= _area(candidate) * 1.15:
        return False
    small = _canonical(candidate.text)
    full = _canonical(larger.text)
    # Two-character OCR fragments (for example a duplicated ``LP`` or
    # ``D.`` suffix) are still safe to remove when their box is contained in
    # a larger region.  The decision remains geometric/textual and does not
    # depend on document values.
    if len(small) < 2 and not re.search(r"\d|[^A-Za-z\s]", candidate.text):
        return False
    if not small or small == full:
        return False
    cx1, cy1, cx2, cy2 = candidate.bbox
    lx1, ly1, lx2, ly2 = larger.bbox
    padding = max(5.0, min(candidate.bbox[3] - candidate.bbox[1], larger.bbox[3] - larger.bbox[1]) * 0.25)
    contained = lx1 - padding <= cx1 and cy1 >= ly1 - padding and cx2 <= lx2 + padding and cy2 <= ly2 + padding
    if small in full and contained:
        return True
    # Paddle can emit a crop that extends a few pixels beyond a full line and
    # contains OCR-corrupted text, so substring matching is unavailable.  A
    # small region whose box is mostly covered by a larger region is still a
    # duplicate when it has no independent spatial content.
    ix1, iy1 = max(cx1, lx1), max(cy1, ly1)
    ix2, iy2 = min(cx2, lx2), min(cy2, ly2)
    overlap = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    candidate_area = max(1.0, (cx2 - cx1) * (cy2 - cy1))
    return overlap / candidate_area >= 0.70


def _regions(result: OCRResult) -> list[OCRRegion]:
    ordered = sorted(result.regions, key=lambda item: (item.page, item.bbox[1], item.bbox[0], item.index))
    kept: list[OCRRegion] = []
    for region in sorted(ordered, key=_area, reverse=True):
        if any(_is_contained_fragment(region, existing) for existing in kept):
            continue
        kept.append(region)
    return sorted(kept, key=lambda item: (item.page, item.bbox[1], item.bbox[0], item.index))


# AI-Hub's reference forms use this design canvas.  Resolver rules are written
# in design coordinates, but are projected to the actual OCR page dimensions
# whenever those dimensions are available.  This keeps the semantic zones
# stable under uniform resize/translation without changing the reference
# behavior for results that carry no page metadata.
_TEMPLATE_WIDTH = 1654.0
_TEMPLATE_HEIGHT = 2340.0


def _page_dimensions(result: OCRResult) -> tuple[float, float]:
    metadata = result.metadata or {}
    for width_key, height_key in (("page_width", "page_height"), ("image_width", "image_height")):
        try:
            width = float(metadata[width_key])
            height = float(metadata[height_key])
        except (KeyError, TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            return width, height

    source = Path(result.source_file) if result.source_file else None
    if source and source.is_file():
        try:
            with source.open("rb") as handle:
                header = handle.read(24)
            if header[:8] == b"\x89PNG\r\n\x1a\n" and len(header) >= 24:
                return float(struct.unpack(">II", header[16:24])[0]), float(struct.unpack(">II", header[16:24])[1])
        except (OSError, struct.error):
            pass
    return _TEMPLATE_WIDTH, _TEMPLATE_HEIGHT


def _template_bounds(result: OCRResult, x1: float, x2: float, y1: float, y2: float) -> tuple[float, float, float, float]:
    width, height = _page_dimensions(result)
    try:
        origin_x = float((result.metadata or {}).get("page_origin_x", 0.0))
        origin_y = float((result.metadata or {}).get("page_origin_y", 0.0))
    except (TypeError, ValueError):
        origin_x = origin_y = 0.0
    return (origin_x + x1 * width / _TEMPLATE_WIDTH, origin_x + x2 * width / _TEMPLATE_WIDTH,
            origin_y + y1 * height / _TEMPLATE_HEIGHT, origin_y + y2 * height / _TEMPLATE_HEIGHT)


def _in_template_zone(result: OCRResult, region: OCRRegion, *, x1: float, x2: float, y1: float, y2: float) -> bool:
    left, right, top, bottom = _template_bounds(result, x1, x2, y1, y2)
    return region.bbox[0] >= left and region.bbox[2] <= right and region.bbox[1] >= top and region.bbox[3] <= bottom


def _in_template_window(result: OCRResult, region: OCRRegion, *, x1: float, x2: float, y1: float, y2: float) -> bool:
    """Project legacy top-left window semantics to the actual page."""
    left, right, top, bottom = _template_bounds(result, x1, x2, y1, y2)
    return left <= region.bbox[0] <= right and top <= region.bbox[1] <= bottom


def _template_delta(result: OCRResult, *, x: float = 0.0, y: float = 0.0) -> tuple[float, float]:
    width, height = _page_dimensions(result)
    return x * width / _TEMPLATE_WIDTH, y * height / _TEMPLATE_HEIGHT


def _has_scaled_geometry(result: OCRResult) -> bool:
    width, height = _page_dimensions(result)
    return abs(width - _TEMPLATE_WIDTH) > 0.5 or abs(height - _TEMPLATE_HEIGHT) > 0.5


def _evidence_from_region(region: OCRRegion, value: str) -> EvidenceField:
    return evidence(
        value.strip(),
        source_text=region.text,
        bbox=region.polygon,
        confidence=region.confidence,
    )


def _combined_evidence(regions: list[OCRRegion], *, value: str | None = None) -> EvidenceField:
    if not regions:
        return missing()
    text = value if value is not None else " ".join(region.text.strip() for region in regions if region.text.strip())
    polygon = [[min(region.bbox[0] for region in regions), min(region.bbox[1] for region in regions)],
               [max(region.bbox[2] for region in regions), min(region.bbox[1] for region in regions)],
               [max(region.bbox[2] for region in regions), max(region.bbox[3] for region in regions)],
               [min(region.bbox[0] for region in regions), max(region.bbox[3] for region in regions)]]
    confidences = [region.confidence for region in regions if region.confidence is not None]
    return evidence(text, source_text=" ".join(region.text for region in regions), bbox=polygon,
                    confidence=sum(confidences) / len(confidences) if confidences else None)


def _in_zone(result: OCRResult, *, x1: float, x2: float, y1: float, y2: float) -> list[OCRRegion]:
    return [region for region in _regions(result)
            if _in_template_zone(result, region, x1=x1, x2=x2, y1=y1, y2=y2)]


def _token_value(regions: list[OCRRegion], pattern: str) -> EvidenceField:
    matches = [region for region in regions if re.fullmatch(pattern, region.text.strip(), re.I)]
    if len(matches) == 1:
        return _evidence_from_region(matches[0], matches[0].text)
    if len(matches) > 1:
        unique_values = {_canonical(region.text) for region in matches}
        if len(unique_values) == 1:
            return _combined_evidence(matches, value=matches[0].text)
        return ambiguous(source_text=" | ".join(region.text for region in matches))
    return missing()


def _row_centers(regions: list[OCRRegion], *, minimum: float = 20) -> list[float]:
    centers: list[float] = []
    for region in sorted(regions, key=lambda item: (item.bbox[1], item.bbox[0])):
        center = (region.bbox[1] + region.bbox[3]) / 2
        if not centers or center - centers[-1] > minimum:
            centers.append(center)
    return centers


def _near_row(regions: list[OCRRegion], center: float, tolerance: float = 38) -> list[OCRRegion]:
    return [region for region in regions if abs((region.bbox[1] + region.bbox[3]) / 2 - center) <= tolerance]


def _is_quantity_token(text: str) -> bool:
    """Recognize a numeric quantity, including the common OCR ``1`` -> ``I``."""
    value = text.strip()
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", value) or re.fullmatch(r"[Il]", value))


def _quantity_evidence(regions: list[OCRRegion]) -> EvidenceField:
    if len(regions) == 1 and re.fullmatch(r"[Il]", regions[0].text.strip()):
        return _combined_evidence(regions, value="1")
    return _combined_evidence(regions)


def _description_evidence(regions: list[OCRRegion]) -> EvidenceField:
    # Package marks occasionally fall into the left-side description window
    # (for example ``PKGS`` immediately before the actual item text).  These
    # short markers are structural noise, not an item description.
    selected = [region for region in regions if not re.fullmatch(r"PKG(?:S|A)?", region.text.strip(), re.I)]
    return _combined_evidence(selected)


def _line_groups(regions: list[OCRRegion], tolerance: float = 28) -> list[list[OCRRegion]]:
    """Group nearby OCR regions into reading-order lines."""
    lines: list[list[OCRRegion]] = []
    for region in sorted(regions, key=lambda item: ((item.bbox[1] + item.bbox[3]) / 2, item.bbox[0], item.index)):
        center = (region.bbox[1] + region.bbox[3]) / 2
        if not lines:
            lines.append([region])
            continue
        previous = sum((item.bbox[1] + item.bbox[3]) / 2 for item in lines[-1]) / len(lines[-1])
        if abs(center - previous) <= tolerance:
            lines[-1].append(region)
        else:
            lines.append([region])
    return [sorted(line, key=lambda item: (item.bbox[0], item.index)) for line in lines]


_PARTY_STOP_WORDS = {
    "SHIPPER", "SELLER", "EXPORTER", "BUYER", "CONSIGNEE", "CONSINEE", "NOTIFY", "PARTY",
    "PHONE", "TEL", "FAX", "ADDRESS", "COMPLETE", "NAME", "PROVIDE", "PLEASE", "ACCOUNT",
    "RISK", "ORDER", "OF", "AND", "&", "MESSRS", "IF", "OTHER", "THAN", "NOT", "NEGOTIABLE",
    "UNLESS", "CONSIGNED",
}

_PARTY_HEADING_WORDS = (
    "SHIPPER", "SELLER", "EXPORTER", "BUYER", "CONSIGNEE", "NOTIFY", "PARTY",
)

_PARTY_COMPANY_MARKERS = {
    "CO", "LTD", "INC", "LLC", "CORP", "CORPORATION", "COMPANY", "LIMITED",
    "TRADING", "INDUSTRIES", "ENTERPRISES", "SYSTEMS", "GROUP", "SOLUTIONS",
}
_PARTY_COUNTRY_LINES = {
    "AUSTRALIA", "CANADA", "CHINA", "DENMARK", "EGYPT", "ERITREA", "FRANCE",
    "GERMANY", "INDIA", "ITALY", "JAPAN", "KOREA", "MALAYSIA", "NORWAY",
    "NIGERIA", "SINGAPORE", "SPAIN", "TAIWAN", "THAILAND", "TURKEY",
    "UNITED STATES", "VIET NAM", "VIETNAM", "REP OF KOREA", "REP OF SINGAPORE",
    "SOUTH AFRICA",
}


def _party_word_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _canonical(left), _canonical(right)).ratio()


def _looks_like_party_heading(text: str) -> bool:
    """Recognize OCR-corrupted party headings without using document values.

    AI-Hub recognition commonly returns headings such as ``Shippor/ Exporer``
    and ``Notiyy Party``.  Treating those lines as company names causes the
    fixed template fallback to return a label instead of the party value.
    The test is deliberately limited to lines whose every word resembles a
    known heading, so organization names containing words such as GROUP are
    not discarded.
    """
    words = _canonical(text).split()
    if not words:
        return True
    matches = [
        max(_party_word_similarity(word, heading) for heading in _PARTY_HEADING_WORDS)
        for word in words
    ]
    return len(words) >= 1 and all(score >= 0.72 for score in matches)


def _remove_inline_party_heading(text: str) -> str:
    """Remove a leading OCR party label while preserving the value text."""
    match = re.match(r"\s*([A-Za-z]+)\s*(?::|\||/|#|-)?\s*", text)
    if not match:
        return text.strip()
    word = match.group(1)
    if max(_party_word_similarity(word, heading) for heading in _PARTY_HEADING_WORDS) < 0.82:
        return text.strip()
    remainder = text[match.end():].strip(" |:/#-")
    return remainder


def _is_party_value_candidate(text: str) -> bool:
    """Reject structural party-block lines before choosing an organization.

    The OCR party block is ordered as heading, organization, address, country,
    and contact.  This lexical filter is deliberately value-independent: it
    does not know a document id or any gold value and allows organizations
    without a legal suffix (for example ``NONGS DRUG STORES``).
    """
    upper = text.upper().strip(" ,:;-&")
    canonical = _canonical(upper)
    words = set(canonical.split())
    if not canonical or _looks_like_party_heading(upper):
        return False
    if canonical in _PARTY_COUNTRY_LINES:
        return False
    if re.search(r"NO\s+CLAIM|FAILURE\s+TO\s+NOTIFY|COMPLETE\s+NAME|PLEASE\s+PROVIDE|ACCOUNT\s*(?:&|AND)?\s*RISK", upper):
        return False
    if re.search(r"\bIF\s*['’]?\s*TO\s+ORDER(?:\s+SO\s+INDICATE)?\b", upper):
        return False
    if re.search(r"\b(?:BILL\s+OF\s+LADING|MULTIMODAL\s+OCEAN|IMODAL\s+OCEAN|NOT\s+NEOTIABLE|IF\s+TO\s+ORDER|CONSIGNED\s+TO\s+ORDER|PRE[- ]CARRIAGE|PLACE\s+OF\s+RECEIPT|MODE\s+OF\s+INITIAL\s+CARRIAGE)\b", upper):
        return False
    if re.search(r"\b(?:TEL|FAX|PHONE|EMAIL|ADDRESS|STREET|ROAD|AVENUE|DRIVE|ROOM|DISTRICT|VIC)\b", upper):
        if not words.intersection(_PARTY_COMPANY_MARKERS):
            return False
    if re.search(r"\bV\s*\.?\s*\d+\b", upper):
        return False
    if re.search(r"\b(?:CFS|CY|FOB|CIF|CFR|DAF|DDP|DDU|DEQ)\b", upper):
        return False
    # A place line such as ``CITY, COUNTRY`` is not a party name.  Company
    # markers keep legitimate names containing a country/place word valid.
    if "," in upper and re.search(r"\b(?:AUSTRALIA|CANADA|CHINA|JAPAN|KOREA|NORWAY|SINGAPORE|SPAIN|TAIWAN|TURKEY|UNITED STATES)\b", upper) and not words.intersection(_PARTY_COMPANY_MARKERS):
        return False
    if re.match(r"^\d", upper) and not words.intersection(_PARTY_COMPANY_MARKERS):
        return False
    return len(re.findall(r"[A-Za-z]", upper)) >= 3


def _party_evidence(regions: list[OCRRegion]) -> EvidenceField:
    """Select the first organization line while preserving its OCR evidence.

    Party blocks contain headings, telephone lines and multi-line addresses.
    Selecting a company line is a structural operation; no spelling or
    semantic correction is applied to the recognized text.
    """
    for line in _line_groups(regions):
        raw_text = " ".join(item.text.strip() for item in line if item.text.strip()).strip(" ,:;-&")
        # A value and the next heading can land on one OCR line (for example
        # ``QILGRIM'S PRIDE NOTIFY PARTY ...``). Keep the value prefix.
        trailing_heading = re.search(
            r"\b(?:SHIPPER|SELLER|EXPORTER|BUYER|CONSIGNEE|NOTIFY\s+PARTY)\b",
            raw_text,
            re.I,
        )
        if (trailing_heading and trailing_heading.start() > 0
                and not re.match(r"^SAME\s+AS\s+(?:THE\s+)?(?:CONSIGNEE|SHIPPER|BUYER|EXPORTER|SELLER)\b", raw_text, re.I)):
            raw_text = raw_text[:trailing_heading.start()].strip(" ,:;-&")
        text = _remove_inline_party_heading(raw_text)
        canonical = _canonical(text)
        if (not _is_party_value_candidate(text)
                or set(canonical.split()).issubset(_PARTY_STOP_WORDS)
                or re.search(r"\b(?:ACCOUNT\s*&?\s*RISK|FOR\s+ACCOUNT|NOT\s+NEGOTIABLE)\b", canonical)):
            continue
        if len(re.findall(r"\d", text)) > len(re.findall(r"[A-Za-z]", text)):
            continue
        return _combined_evidence(line, value=text)
    return missing()


def _party_heading_role(text: str) -> str | None:
    """Return a party role anchor, excluding contact/instruction headings."""
    upper = text.upper()
    if re.fullmatch(r"\s*SAME\s+AS\s+(?:THE\s+)?(?:CONSIGNEE|SHIPPER|BUYER|EXPORTER|SELLER)\s*", upper):
        return None
    if re.search(r"\b(?:PHONE|TEL|FAX|EMAIL|FOR\s+DELIVERY)\b", upper):
        return None
    if re.search(r"\bNOTIFY(?:\s+PARTY)?\b", upper):
        return "notify_party"
    if re.search(r"\b(?:SHIPPER|EXPORTER|SELLER)\b", upper):
        return "shipper"
    if re.search(r"\b(?:CONSIGNEE|BUYER)\b", upper):
        return "consignee"
    return None


def _bl_party_evidence(result: OCRResult) -> dict[str, EvidenceField]:
    """Resolve B/L parties from detected left-column sections.

    OCR layouts in this dataset use more than one page scale.  Fixed y
    windows can therefore select the next party or drop the first one.  This
    resolver first finds party-anchor section boundaries, then asks the
    existing typed party filter for a candidate within each section.  A
    duplicated first role is treated as an OCR label error only when the
    complete three-slot party structure is present; no value-specific rule is
    involved.
    """
    left = [region for region in _regions(result)
            if _in_template_zone(result, region, x1=0, x2=800, y1=150, y2=850)]
    lines = _line_groups(left)
    anchors: list[tuple[float, str]] = []
    for line in lines:
        role = _party_heading_role(" ".join(region.text for region in line))
        if role is not None:
            anchors.append((min(region.bbox[1] for region in line), role))
    anchors.sort()

    candidates: list[tuple[int, float, EvidenceField]] = []
    for line in lines:
        candidate = _party_evidence(line)
        if candidate.status != "extracted" or not candidate.bbox:
            continue
        y = min(point[1] for point in candidate.bbox)
        section = sum(y >= boundary for boundary, _ in anchors)
        candidates.append((section, y, candidate))

    if not anchors:
        # Keep the old test/low-information behavior when no structural
        # anchor exists, but restrict it to the first three typed candidates.
        ordered = [field for _, _, field in sorted(candidates, key=lambda item: item[1])]
        return {
            "shipper": ordered[0] if len(ordered) > 0 else missing("party_candidate_not_found"),
            "consignee": ordered[1] if len(ordered) > 1 else missing("party_candidate_not_found"),
            "notify_party": ordered[2] if len(ordered) > 2 else missing("party_candidate_not_found"),
        }

    by_section: dict[int, EvidenceField] = {}
    for section, _, candidate in sorted(candidates, key=lambda item: (item[0], item[1])):
        by_section.setdefault(section, candidate)
    anchor_roles = [role for _, role in anchors]
    role_by_section = {}
    if anchor_roles and anchor_roles[0] == "shipper":
        role_by_section.update({index + 1: role for index, role in enumerate(
            ("shipper", "consignee", "notify_party"))})
    elif anchor_roles and anchor_roles[0] == "consignee" and "shipper" not in anchor_roles:
        # Several AI-Hub B/L templates omit or misrecognize the SHIPPER label,
        # while the following anchors still delimit the three vertical party
        # sections. Interpret those detected sections in template order.
        role_by_section.update({index + 1: role for index, role in enumerate(
            ("shipper", "consignee", "notify_party"))})
    else:
        role_by_section = {index + 1: role for index, (_, role) in enumerate(anchors)}

    resolved = {name: missing("party_candidate_not_found")
                for name in ("shipper", "consignee", "notify_party")}
    for section, candidate in by_section.items():
        role = role_by_section.get(section)
        if role in resolved and resolved[role].status == "missing":
            resolved[role] = candidate
    return resolved


def _date_evidence(regions: list[OCRRegion], field_name: str = "shipment_date") -> EvidenceField:
    from fintra.normalization.values import normalize_date

    def date_text(text: str) -> str | None:
        candidates = re.findall(
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|"
            r"\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ]\d{2,4}|"
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ -]\d{1,2},?[ -]\d{2,4}",
            text,
            re.I,
        )
        return next((candidate for candidate in candidates if normalize_date(candidate)), None)

    candidates = []
    for line in _line_groups(regions):
        valid_regions = [(item, date_text(item.text.strip()) or item.text.strip()) for item in line if date_text(item.text.strip()) or normalize_date(item.text.strip())]
        text = " ".join(item.text.strip() for item in line if item.text.strip())
        line_date = date_text(text) or (text if normalize_date(text) else None)
        if len(valid_regions) == 1:
            candidates.append(([valid_regions[0][0]], valid_regions[0][1]))
        elif line_date:
            candidates.append((line, line_date))
    if len(candidates) == 1:
        line, text = candidates[0]
        return _combined_evidence(line, value=text)
    return missing("date_not_uniquely_parseable")


def _last_line_evidence(regions: list[OCRRegion]) -> EvidenceField:
    lines = _line_groups(regions)
    return _combined_evidence(lines[-1]) if lines else missing()


def _item_from_columns(regions: list[OCRRegion], center: float, columns: tuple[tuple[float, float], ...]) -> LineItem:
    values = []
    for column_index, (x1, x2) in enumerate(columns):
        row_tolerance = 62 if column_index == 2 else 38
        selected = sorted((region for region in _near_row(regions, center, tolerance=row_tolerance)
                           if x1 <= region.bbox[0] <= x2), key=lambda item: item.bbox[0])
        if column_index == 2:
            selected = [region for region in selected
                        if (region.bbox[1] + region.bbox[3]) / 2 >= center - 10
                        and re.fullmatch(r"[A-Za-z][A-Za-z /.-]{0,14}", region.text.strip())]
        values.append(_description_evidence(selected) if x1 < 730 else _combined_evidence(selected))
    return LineItem(description=values[0], quantity=values[1], unit=values[2], unit_price=values[3], amount=values[4])


def _invoice_layout(result: OCRResult) -> dict[str, EvidenceField | list[LineItem]]:
    # Coordinates are the stable 1654x2340 AI-Hub Commercial Invoice template.
    values = _regions(result)
    item_regions = [region for region in values if _in_template_window(result, region, x1=0, x2=_TEMPLATE_WIDTH, y1=1000, y2=1520)]
    centers = _row_centers([region for region in item_regions if _in_template_window(result, region, x1=820, x2=950, y1=0, y2=_TEMPLATE_HEIGHT)
                            and _is_quantity_token(region.text)], minimum=45)
    items = [_item_from_columns(item_regions, center, ((120, 700), (820, 950), (820, 1100), (1100, 1260), (1260, 1520))) for center in centers]
    currency_matches = []
    for region in values:
        match = re.search(r"\b(USD|EUR|GBP|JPY|CNY|KRW)\b", region.text, re.I)
        if match:
            currency_matches.append((region, match.group(1).upper()))
    currency_codes = {code for _, code in currency_matches}
    if len(currency_codes) == 1:
        region, code = max(currency_matches, key=lambda item: item[0].bbox[1])
        currency = _evidence_from_region(region, code)
    else:
        currency = _token_value(values, r"USD|EUR|GBP|JPY|CNY|KRW")
    total_regions = [region for region in values if _in_template_window(result, region, x1=1200, x2=_TEMPLATE_WIDTH, y1=1450, y2=1650) and re.search(r"\d", region.text)]
    return {
        "invoice_number": _combined_evidence(_in_zone(result, x1=850, x2=1320, y1=250, y2=360)),
        "invoice_date": _date_evidence(_in_zone(result, x1=850, x2=1450, y1=360, y2=455), "invoice_date"),
        "seller": _party_evidence(_in_zone(result, x1=100, x2=850, y1=300, y2=650)),
        "buyer": _party_evidence(_in_zone(result, x1=100, x2=850, y1=570, y2=760)),
        "currency": currency,
        "total_amount": _combined_evidence(total_regions),
        "items": items,
    }


def _invoice_number_header(result: OCRResult) -> EvidenceField:
    """Select a unique invoice identifier from the upper-right header.

    Several AI-Hub forms render ``Invoice No. and date`` as one label while
    Paddle may split the identifier and date into separate regions.  The
    identifier resolver only accepts a standalone alphanumeric token and
    excludes parseable dates, preserving the original OCR text as evidence.
    """
    from fintra.normalization.values import normalize_date

    date_like = re.compile(
        r"(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
        r"\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ]\d{2,4}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ -]\d{1,2},?[ -]\d{2,4})",
        re.I,
    )
    candidates = []
    for region in _regions(result):
        x1, y1, x2, y2 = region.bbox
        text = region.text.strip()
        if not _in_template_window(result, region, x1=800, x2=1200, y1=230, y2=410) or len(text) < 4:
            continue
        if normalize_date(text) or date_like.fullmatch(text) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./-]{3,}", text):
            continue
        canonical = _canonical(text)
        if canonical in {"INVOICE", "NUMBER", "NO", "DATE", "AND", "LC"}:
            continue
        candidates.append(region)
    if len(candidates) == 1:
        return _evidence_from_region(candidates[0], candidates[0].text)
    return missing("invoice_number_not_unique_in_header")


def _packing_date_evidence(result: OCRResult) -> EvidenceField:
    """Choose the invoice date when a packing-list header has several dates.

    Packing lists commonly place invoice date and L/C date in the same header
    band.  A broad date scan becomes ambiguous, so when an invoice/date label
    exists, choose only the date nearest that label.  The rule is based on
    layout and label text, not on a document value.
    """
    values = _regions(result)
    date_regions: list[tuple[OCRRegion, EvidenceField]] = []
    for region in values:
        if not _in_template_window(result, region, x1=1150, x2=1500, y1=150, y2=455):
            continue
        candidate = _date_evidence([region], "date")
        if candidate.status == "extracted":
            date_regions.append((region, candidate))
    if len(date_regions) <= 1:
        return date_regions[0][1] if date_regions else _date_evidence(
            _in_zone(result, x1=1150, x2=1500, y1=150, y2=455), "date"
        )

    invoice_labels = [region for region in values
                      if _in_template_window(result, region, x1=760, x2=1200, y1=150, y2=455)
                      and re.search(r"INVOICE", region.text, re.I)
                      and re.search(r"DATE", region.text, re.I)]
    if not invoice_labels:
        return _date_evidence([region for region, _ in date_regions], "date")
    label = min(invoice_labels, key=lambda region: (region.bbox[1], region.bbox[0]))
    selected = min(
        date_regions,
        key=lambda item: (
            abs(((item[0].bbox[1] + item[0].bbox[3]) / 2) - ((label.bbox[1] + label.bbox[3]) / 2)),
            abs(item[0].bbox[0] - label.bbox[2]),
        ),
    )
    return selected[1]


def _packing_layout(result: OCRResult) -> dict[str, EvidenceField | list[LineItem]]:
    values = _regions(result)
    # Packing-list templates use either a separate Unit column or a combined
    # QTY/UNIT column.  In the latter, the unit is often printed one line
    # below the quantity; keep the table window wide enough to include that
    # second line while stopping before the footer totals.
    item_regions = [region for region in values if _in_template_window(result, region, x1=0, x2=_TEMPLATE_WIDTH, y1=1000, y2=1640)]
    centers = _row_centers([region for region in item_regions if _in_template_window(result, region, x1=800, x2=1100, y1=0, y2=_TEMPLATE_HEIGHT)
                            and _is_quantity_token(region.text)], minimum=45)
    unit_headers = [region for region in values
                    if _in_template_window(result, region, x1=760, x2=1250, y1=1000, y2=1140)
                    and re.search(r"\bUNIT\b", region.text, re.I)]
    if unit_headers:
        unit_header = min(unit_headers, key=lambda region: (region.bbox[1], region.bbox[0]))
        unit_left = max(760.0, unit_header.bbox[0] - 60.0)
        unit_right = min(1250.0, unit_header.bbox[2] + 70.0)
    else:
        unit_left, unit_right = 800.0, 1200.0

    unit_noise = {"QUANTITY", "QTY", "QTY UNIT", "UNIT", "NET WEIGHT", "GROSS WEIGHT", "PACKAGES", "PACKAGE"}

    def unit_value(region: OCRRegion) -> bool:
        text = region.text.strip()
        return (
            bool(re.fullmatch(r"[A-Za-z][A-Za-z /.-]{0,14}", text))
            and _canonical(text) not in unit_noise
        )

    items = []
    for center in centers:
        row = _near_row(item_regions, center, tolerance=62)
        description = _description_evidence([region for region in row if _in_template_window(result, region, x1=0, x2=730, y1=0, y2=_TEMPLATE_HEIGHT)])
        quantity = _quantity_evidence([region for region in row
                                       if 800 <= region.bbox[0] <= 1100 and _is_quantity_token(region.text)])
        unit = _combined_evidence([region for region in row
                                   if unit_left <= region.bbox[0] <= unit_right and unit_value(region)])
        items.append(LineItem(description=description, quantity=quantity, unit=unit))
    package_regions = [region for region in values if _in_template_window(result, region, x1=100, x2=650, y1=1650, y2=1825)]
    package_values = []
    for region in package_regions:
        match = re.search(r"(?:NUMBER\s+OF\s+PACKAGES|NO\.?\s+OF\s+PKGS?)\s*[:#-]?\s*(\d+(?:[.,]\d+)?)", region.text, re.I)
        if match:
            package_values.append((region, match.group(1)))
    if len(package_values) == 1:
        package = _evidence_from_region(package_values[0][0], package_values[0][1])
    else:
        package_numbers = [region for region in package_regions if re.fullmatch(r"\d+(?:[.,]\d+)?", region.text.strip())]
        package = _evidence_from_region(package_numbers[0], package_numbers[0].text) if len(package_numbers) == 1 else _combined_evidence(package_regions)
    gross_regions = [region for region in values if _in_template_window(result, region, x1=100, x2=800, y1=1750, y2=1850) and re.search(r"\d", region.text)]
    gross_values = []
    for region in gross_regions:
        match = re.search(r"(?:GROSS\s+WEIGHT).*?(\d+(?:[.,]\d+)?)\s*(KG|KGS|GRAM|G)?\b", region.text, re.I)
        if match and match.group(2):
            gross_values.append((region, match.group(1) + match.group(2)))
    if len(gross_values) == 1:
        gross = _evidence_from_region(gross_values[0][0], gross_values[0][1])
    else:
        gross_candidates = [region for region in gross_regions if re.search(r"(?:KG|KGS|GRAM|\bG\b)", region.text, re.I)]
        gross = _evidence_from_region(gross_candidates[0], gross_candidates[0].text) if len(gross_candidates) == 1 else _combined_evidence(gross_regions)
    weight_unit = _token_value(values, r"KG|KGS|G|GRAM|GRAMS")
    if weight_unit.status == "missing" and gross.status == "extracted":
        match = re.search(r"\b(KG|KGS|G)\b", str(gross.value), re.I)
        if match:
            weight_unit = evidence(match.group(1).upper(), source_text=gross.source_text, bbox=gross.bbox)
    return {
        "packing_list_number": missing("template_field_not_present"),
        # The date field occupies the upper-right header zone.  Paddle boxes
        # can extend below y=280 even when the date is the first header date;
        # use the full template header band while retaining unique-date
        # validation in _date_evidence.
        "date": _packing_date_evidence(result),
        "exporter": _party_evidence(_in_zone(result, x1=100, x2=800, y1=230, y2=650)),
        "consignee": _party_evidence(_in_zone(result, x1=100, x2=800, y1=430, y2=820)),
        "items": items,
        "package_count": package,
        "gross_weight": gross,
        "net_weight": ambiguous(source_text="multiple per-item net weights; no single total"),
        "weight_unit": weight_unit,
    }


def _bl_layout(result: OCRResult) -> dict[str, EvidenceField]:
    values = _regions(result)
    parties = _bl_party_evidence(result)
    number_regions = _in_zone(result, x1=1150, x2=1500, y1=220, y2=360)
    if _has_scaled_geometry(result):
        description_headers = [region for region in values if _in_template_window(result, region, x1=500, x2=1100, y1=1000, y2=1200)
                               and re.search(r"DESCRIPTION|GOODS", region.text, re.I)]
        _, delta_y = _template_delta(result, y=25)
        goods_start = min((region.bbox[3] for region in description_headers), default=_template_bounds(result, 0, 0, 0, 1050)[3]) + delta_y
        table_total_markers = [region for region in values
                               if (_in_template_window(result, region, x1=900, x2=_TEMPLATE_WIDTH, y1=0, y2=_TEMPLATE_HEIGHT)
                                   and _canonical(region.text) == "TOTAL")
                               or (_in_template_window(result, region, x1=0, x2=_TEMPLATE_WIDTH, y1=0, y2=_TEMPLATE_HEIGHT)
                                   and re.search(r"TOTAL.*(?:PKG|PACKAGES)", region.text, re.I))]
        _, end_delta_y = _template_delta(result, y=5)
        default_end = _template_bounds(result, 0, 0, 0, 1550)[3]
        goods_end = min((region.bbox[1] for region in table_total_markers if region.bbox[1] > goods_start), default=default_end) - end_delta_y
        goods_regions = [region for region in values if _in_template_window(result, region, x1=500, x2=1100, y1=0, y2=_TEMPLATE_HEIGHT)
                         and goods_start <= region.bbox[1] <= goods_end]
    else:
        description_headers = [region for region in values if 500 <= region.bbox[0] <= 1100
                               and 1000 <= region.bbox[1] <= 1200
                               and re.search(r"DESCRIPTION|GOODS", region.text, re.I)]
        goods_start = min((region.bbox[3] for region in description_headers), default=1050) + 25
        table_total_markers = [region for region in values
                               if (region.bbox[0] >= 900 and _canonical(region.text) == "TOTAL")
                               or re.search(r"TOTAL.*(?:PKG|PACKAGES)", region.text, re.I)]
        goods_end = min((region.bbox[1] for region in table_total_markers if region.bbox[1] > goods_start), default=1550) - 5
        goods_regions = [region for region in values if 500 <= region.bbox[0] <= 1100
                         and goods_start <= region.bbox[1] <= goods_end]
    goods_lines = []
    for line in _line_groups(goods_regions):
        kept = [region for region in line if _canonical(region.text) not in {"TOTAL", "PKG", "KG", "KGS", "G", "CBM"}
                and not re.search(r"PARTICULARS|DESCRIPTION OF PACKAGE|GROSS WEIGHT|MEASUREMENTS|FREIGHT|CLASS|NO OF|CONTAINER NO", region.text, re.I)
                and not re.fullmatch(r"\d+(?:[.,]\d+)?(?:KG|KGS|G)?", region.text.strip(), re.I)]
        if kept and any(re.search(r"[A-Za-z]", region.text) for region in kept):
            goods_lines.extend(kept)
    # Other totals can occur in the invoice/footer text.  Only a TOTAL inside
    # the B/L item table can define the shipment summary row.
    total_regions = [region for region in values if _canonical(region.text) == "TOTAL"
                     and _in_template_window(result, region, x1=0, x2=_TEMPLATE_WIDTH, y1=1080, y2=1600)]
    total_regions.extend(region for region in values
                         if re.search(r"TOTAL.*(?:PKG|PACKAGES)", region.text, re.I)
                         and _in_template_window(result, region, x1=0, x2=_TEMPLATE_WIDTH, y1=1080, y2=1600))
    package_total = []
    gross_total = []
    if len(total_regions) == 1:
        center = (total_regions[0].bbox[1] + total_regions[0].bbox[3]) / 2
        row = _near_row(values, center, tolerance=42)
        package_total = [region for region in row if _in_template_zone(result, region, x1=220, x2=500, y1=0, y2=_TEMPLATE_HEIGHT) and re.fullmatch(r"\d+(?:[.,]\d+)?", region.text.strip())]
        gross_total = [region for region in row if _in_template_zone(result, region, x1=1100, x2=1300, y1=0, y2=_TEMPLATE_HEIGHT) and re.search(r"\d", region.text)]
    gross_values = [region for region in values if _in_template_window(result, region, x1=1100, x2=1300, y1=1080, y2=1500) and re.search(r"\d", region.text)]
    weight_unit = _token_value(values, r"KG|KGS|G|GRAM|GRAMS")
    if weight_unit.status == "missing":
        kg = [region for region in gross_values if re.search(r"KG", region.text, re.I)]
        if kg:
            weight_unit = evidence("KG", source_text=" ".join(region.text for region in kg), bbox=kg[0].polygon)
    vessel = _find_field(result, ("export carrier (vessel)", "vessel name"), prefer_below=True)
    vessel_value_is_voyage = bool(vessel.value and re.fullmatch(
        r"\s*(?:NO\s*)?V\s*\.?\s*\d+\s*|\s*NO\s*", str(vessel.value), re.I))
    if vessel.status == "missing" or vessel_value_is_voyage:
        anchored_vessel = _vessel_evidence(result)
        if anchored_vessel.status == "extracted":
            vessel = anchored_vessel
    if vessel.status == "missing":
        for region in values:
            match = re.match(r"VESSEL\s*/?\s*VOY\.?\s+(.+)$", region.text.strip(), re.I)
            if match:
                vessel = _evidence_from_region(region, match.group(1).strip())
                break
    loading = _find_field(result, ("port of loading",), prefer_below=True)
    discharge = _find_field(result, ("port of discharge",), prefer_below=True)
    # Some forms omit the port labels from OCR entirely.  Recover a port only
    # when there is exactly one typed place candidate in the transport row;
    # multiple candidates stay missing rather than crossing sections.
    if loading.status == "missing" or discharge.status == "missing":
        place_candidates = [
            region for region in values
            if _in_template_window(result, region, x1=0, x2=_TEMPLATE_WIDTH, y1=750, y2=1080)
            and "," in region.text
            and re.search(r"[A-Za-z]", region.text)
            and not re.search(r"\b(?:FOB|CIF|CFR|DAF|DDP|DDU|CFS|CY|DEQ)\b", region.text, re.I)
            and not re.search(r"\b(?:PORT|PLACE|DESTINATION|VESSEL|VOY|CARRIER)\b", region.text, re.I)
        ]
        if len(place_candidates) == 1:
            if loading.status == "missing":
                loading = _evidence_from_region(place_candidates[0], place_candidates[0].text)
            elif discharge.status == "missing":
                discharge = _evidence_from_region(place_candidates[0], place_candidates[0].text)
    return {
        "bl_number": _bl_number_evidence(result),
        "shipper": parties["shipper"],
        "consignee": parties["consignee"],
        "notify_party": parties["notify_party"],
        "vessel": vessel,
        "port_of_loading": loading,
        "port_of_discharge": discharge,
        "shipment_date": _date_evidence(_in_zone(result, x1=1150, x2=1500, y1=170, y2=290)),
        "package_count": _evidence_from_region(package_total[0], package_total[0].text) if len(package_total) == 1 else ambiguous(source_text="no unique total package count"),
        "gross_weight": _evidence_from_region(gross_total[0], gross_total[0].text) if len(gross_total) == 1 else ambiguous(source_text="no unique total gross weight"),
        "weight_unit": weight_unit,
        "goods_description": _combined_evidence(goods_lines),
    }


def _candidate_after_label(region: OCRRegion, aliases: Iterable[str]) -> str | None:
    text = region.text.strip()
    canonical = _canonical(text)
    # "Buyer's Ref" is a reference-number label, not an inline Buyer value.
    # Treating the possessive as a match for BUYER returns the suffix "'s Ref".
    if re.match(r"^(?:BUYER|CONSIGNEE)\s*['’]?S\s+REF(?:ERENCE)?\b", canonical):
        return None
    # Date headings such as "Date of Issue" are labels, not inline dates.
    if re.match(r"^DATE\s+(?:OF|SHIPPED|ISSUED|ON|FROM)\b", canonical):
        return None
    for alias in aliases:
        alias_canonical = _canonical(alias)
        if canonical == alias_canonical:
            return None
        match = re.match(rf"\s*{re.escape(alias_canonical)}\b\s*[:#-]?\s*(.+)$", canonical)
        if match:
            remainder = match.group(1)
            if any(re.search(rf"\b{re.escape(_canonical(heading))}\b", remainder) for heading in _PARTY_HEADING_WORDS):
                return None
            if alias_canonical in {"BUYER", "CONSIGNEE"} and re.search(r"\bREF(?:ERENCE)?\b", remainder):
                return None
            if alias_canonical == "CONSIGNEE" and re.search(r"ACCOUNT|RISK|OTHER\s+THAN", remainder):
                return None
            raw_match = re.search(r"[:#-]\s*(.+)$", text)
            return (raw_match.group(1) if raw_match else text[len(alias):]).strip()
    if ":" in text:
        left, right = text.split(":", 1)
        if _canonical(left) in {_canonical(alias) for alias in aliases} and right.strip():
            return right.strip()
    return None


def _find_field(result: OCRResult, aliases: tuple[str, ...], *, prefer_below: bool = False) -> EvidenceField:
    ordered = _regions(result)
    exact_regions = []
    for region in ordered:
        inline = _candidate_after_label(region, aliases)
        if inline:
            return _evidence_from_region(region, inline)
        if _canonical(region.text) in {_canonical(alias) for alias in aliases}:
            exact_regions.append(region)
    if len(exact_regions) > 1:
        return ambiguous(source_text=" | ".join(region.text for region in exact_regions))
    if not exact_regions:
        return missing()
    label = exact_regions[0]
    lx1, ly1, lx2, ly2 = label.bbox
    candidates = [
        region for region in ordered
        if region.index != label.index and region.page == label.page and region.text.strip()
    ]
    right = [region for region in candidates if region.bbox[0] >= lx2 - 2 and abs(region.bbox[1] - ly1) <= max(40, ly2 - ly1)]
    below = [region for region in candidates if region.bbox[1] >= ly2 - 2 and abs(region.bbox[0] - lx1) <= max(100, lx2 - lx1)]
    candidates_in_order = (below or right) if prefer_below else (right or below)
    nearest = sorted(candidates_in_order, key=lambda region: (abs(region.bbox[1] - ly1), abs(region.bbox[0] - lx2)))
    return _evidence_from_region(nearest[0], nearest[0].text) if nearest else missing()


def _vessel_evidence(result: OCRResult) -> EvidenceField:
    """Resolve vessel values from a vessel anchor and its own column.

    Some B/L forms render the voyage number in the anchor line and the vessel
    name on the following line.  Generic label lookup returns ``V.091`` in
    that layout, so the resolver explicitly rejects voyage/incoterm tokens and
    selects the first typed value below the vessel anchor in the same column.
    """
    values = _regions(result)
    anchor_pattern = re.compile(r"\b(?:VESSEL\s*/?\s*VOY|VESSEL\s+NAME|OCEAN\s+VESSEL|EXPORT\s+CARRIER)\b", re.I)
    anchors = [region for region in values if anchor_pattern.search(region.text)]

    def is_voyage(text: str) -> bool:
        cleaned = text.strip(" ,:;-\")")
        return bool(re.fullmatch(r"\s*(?:NO\s*)?V\s*\.?\s*\d+\s*|\s*NO\s*", cleaned, re.I))

    def is_value(region: OCRRegion) -> bool:
        text = region.text.strip()
        upper = text.upper()
        if not text or is_voyage(text) or re.fullmatch(r"\d+(?:[.,]\d+)?", text):
            return False
        if re.search(r"\b(?:PORT|PLACE|CARRIER|FREIGHT|INCOTERM|FOB|CIF|CFR|DAF|DDP|DDU|DEQ|CFS|CY)\b", upper):
            return False
        if re.search(r"\b(?:SHIPPER|CONSIGNEE|NOTIFY|PARTY|PACKAGE|GROSS|WEIGHT|DESCRIPTION)\b", upper):
            return False
        return bool(re.search(r"[A-Za-z]", text))

    # Inline vessel names such as ``Vessel/voy. MAERSK SANTANA`` are already
    # complete values unless the remainder is only a voyage number.
    for anchor in anchors:
        inline = re.search(r"(?:VESSEL\s*/?\s*VOY\.?|VESSEL\s+NAME|OCEAN\s+VESSEL|EXPORT\s+CARRIER)\s*[:#-]?\s*(.+)$", anchor.text, re.I)
        if inline and is_value(OCRRegion(anchor.polygon, inline.group(1), anchor.confidence, anchor.page, anchor.index)):
            return _evidence_from_region(anchor, inline.group(1).strip())
        ax1, ay1, ax2, ay2 = anchor.bbox
        _, delta_y = _template_delta(result, y=150)
        below = [region for region in values
                 if region.page == anchor.page and region.bbox[1] >= ay2 - 2
                 and region.bbox[1] <= ay2 + delta_y
                 and abs(((region.bbox[0] + region.bbox[2]) / 2) - ((ax1 + ax2) / 2)) <= 180
                 and is_value(region)]
        if below:
            candidate = min(below, key=lambda region: (region.bbox[1], region.bbox[0]))
            return _evidence_from_region(candidate, candidate.text)
    return missing("vessel_anchor_value_not_found")


def _bl_number_evidence(result: OCRResult) -> EvidenceField:
    """Extract one B/L identifier when the header shares a box with its date."""
    from fintra.normalization.values import normalize_date

    token_pattern = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9][A-Za-z0-9./-]{4,}(?![A-Za-z0-9])")
    candidates: list[tuple[OCRRegion, str]] = []
    for region in _in_zone(result, x1=1150, x2=1500, y1=220, y2=360):
        for token in token_pattern.findall(region.text):
            if re.search(r"[A-Za-z]", token) and re.search(r"\d", token) and not normalize_date(token):
                candidates.append((region, token))
    if len({token.upper() for _, token in candidates}) == 1 and candidates:
        region, token = candidates[0]
        return _evidence_from_region(region, token)
    return _token_value(_in_zone(result, x1=1150, x2=1500, y1=220, y2=360), r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9][A-Za-z0-9.-]{4,}")


def _metadata(result: OCRResult) -> DocumentMetadata:
    return DocumentMetadata(
        document_id=result.document_id,
        document_type=result.document_type,
        source_file=result.source_file,
        extraction_status="extracted",
    )


def _items(result: OCRResult) -> list[LineItem]:
    items = []
    for region in _regions(result):
        match = re.match(r"ITEM\s*[:#-]?\s*(.+?)\s*[|;]\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)?(?:\s*[|;]\s*(.+?))?(?:\s*[|;]\s*(.+))?$", region.text, re.I)
        if not match:
            continue
        description, quantity, unit, unit_price, amount = match.groups()
        common = {"source_text": region.text, "bbox": region.polygon, "confidence": region.confidence}
        items.append(LineItem(
            description=evidence(description, **common),
            quantity=evidence(quantity, **common),
            unit=evidence(unit, **common),
            unit_price=evidence(unit_price, **common),
            amount=evidence(amount, **common),
        ))
    return items


def extract_commercial_invoice_legacy(result: OCRResult) -> CommercialInvoice:
    layout = _invoice_layout(result)
    invoice_number = _invoice_number_header(result)
    if invoice_number.status == "missing":
        invoice_number = _find_field(result, ("invoice no", "invoice number", "inv no"))
    seller = _find_field(result, ("seller", "exporter", "shipper", "shipper/exporter"), prefer_below=True)
    buyer = _find_field(result, ("buyer", "consignee", "importer"), prefer_below=True)
    invoice_date = _find_field(result, ("date", "invoice date"))
    currency = _find_field(result, ("currency", "currency code"))
    total_amount = _find_field(result, ("total", "total amount", "invoice total"))
    return CommercialInvoice(
        metadata=_metadata(result),
        invoice_number=invoice_number if invoice_number.status != "missing" else layout["invoice_number"],
        invoice_date=invoice_date if invoice_date.status != "missing" else layout["invoice_date"],
        seller=seller if seller.status != "missing" else layout["seller"],
        buyer=buyer if buyer.status != "missing" else layout["buyer"],
        currency=currency if currency.status != "missing" else layout["currency"],
        total_amount=total_amount if total_amount.status != "missing" else layout["total_amount"],
        items=_items(result) or layout["items"],
    )


def extract_packing_list_legacy(result: OCRResult) -> PackingList:
    layout = _packing_layout(result)
    return PackingList(
        metadata=_metadata(result),
        packing_list_number=layout["packing_list_number"],
        date=layout["date"],
        exporter=layout["exporter"],
        consignee=layout["consignee"],
        items=layout["items"],
        package_count=layout["package_count"],
        gross_weight=layout["gross_weight"],
        net_weight=layout["net_weight"],
        weight_unit=layout["weight_unit"],
    )


def extract_bill_of_lading_legacy(result: OCRResult) -> BillOfLading:
    layout = _bl_layout(result)
    return BillOfLading(
        metadata=_metadata(result),
        bl_number=layout["bl_number"], shipper=layout["shipper"], consignee=layout["consignee"],
        notify_party=layout["notify_party"], vessel=layout["vessel"], port_of_loading=layout["port_of_loading"],
        port_of_discharge=layout["port_of_discharge"], shipment_date=layout["shipment_date"],
        package_count=layout["package_count"], gross_weight=layout["gross_weight"],
        weight_unit=layout["weight_unit"], goods_description=layout["goods_description"],
    )


def _refine(result, document):
    from .refinement import typed_refinement, ordered_refinement
    refined = ordered_refinement(result, typed_refinement(result, document))
    # Use header-relative tables only when they produce complete, typed rows.
    # The legacy resolver remains the fallback for low-information forms; this
    # prevents a weak header guess from replacing already extracted evidence.
    # Commercial Invoice headers have an explicit price/amount grid that the
    # resolver can validate.  Packing List and B/L tables use different
    # logistics columns; they remain on their existing conservative resolver
    # until a document-specific column contract is available.
    if result.document_type == "Commercial Invoice" and hasattr(refined, "items"):
        from .table import extract_header_relative_items
        items = extract_header_relative_items(result, result.document_type)
    else:
        items = []
    if items and hasattr(refined, "items"):
        required = ("description", "quantity")
        complete = all(
            all(getattr(item, field).status.value == "extracted" and getattr(item, field).value for field in required)
            for item in items
        )
        if complete:
            from dataclasses import replace
            refined = replace(refined, items=items)
    return refined


def extract_commercial_invoice(result: OCRResult) -> CommercialInvoice:
    return _refine(result, extract_commercial_invoice_legacy(result))


def extract_packing_list(result: OCRResult) -> PackingList:
    return _refine(result, extract_packing_list_legacy(result))


def extract_bill_of_lading(result: OCRResult) -> BillOfLading:
    return _refine(result, extract_bill_of_lading_legacy(result))


EXTRACTORS: dict[str, Callable[[OCRResult], object]] = {
    "Commercial Invoice": extract_commercial_invoice,
    "Packing List": extract_packing_list,
    "B/L": extract_bill_of_lading,
}
