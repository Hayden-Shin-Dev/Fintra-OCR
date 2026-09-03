"""Deterministic MVP field extraction from normalized OCR predictions.

The extractor is deliberately label-first. A number, currency symbol, or unit is
never enough to decide a semantic field on its own. Visible labels are located
first, then values are attached using document geometry. This same contract is
used by the target-GT profiler so the profiler cannot drift away from the real
extractor.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from .field_evidence import FieldEvidence, missing_field, make_field_evidence
from .layout_reconstruction import line_groups, reconstruct_layout
from .prediction_parser import OCRPrediction


DATE_PATTERN = re.compile(
    r"\b(?:"
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
    r"\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[A-Za-z]*[- ,]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[A-Za-z]*\s+\d{1,2},?\s+\d{2,4}"
    r")\b",
    re.IGNORECASE,
)


def _repair_date_ocr_text(text: str) -> str:
    """Repair only high-confidence OCR confusions inside English month names."""
    value=text.strip(" ,:;")
    replacements={
        r"\b0ct\b":"Oct", r"\b0CT\b":"Oct", r"\bOCT\b":"Oct",
        r"\b0ec\b":"Dec", r"\b0EC\b":"Dec",
        r"\b5ep\b":"Sep", r"\b5EP\b":"Sep",
    }
    for pattern,replacement in replacements.items():
        value=re.sub(pattern,replacement,value,flags=re.I)
    return value


def _date_candidate(text: str) -> str | None:
    match=DATE_PATTERN.search(text)
    if match:
        return match.group(0)
    repaired=_repair_date_ocr_text(text)
    match=DATE_PATTERN.search(repaired)
    return match.group(0) if match else None

ID_PATTERN = re.compile(r"^(?=.*\d)[A-Z0-9][A-Z0-9./_-]{1,}$", re.IGNORECASE)
MONEY_PATTERN = re.compile(
    r"^(?:(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)\s*|[$€£¥]\s*)?"
    r"[+-]?\d[\d,]*(?:\.\d+)?"
    r"(?:\s*(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD))?$",
    re.IGNORECASE,
)
WEIGHT_PATTERN = re.compile(
    r"^[+-]?\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS)$", re.IGNORECASE
)
PACKAGE_PATTERN = re.compile(
    r"^[+-]?\d[\d,.]*\s*(?:PKG|PKGS|CTN|CTNS|BOX|BOXES|BAG|BAGS|"
    r"BUNDLE|BUNDLES|CARTON|CARTONS|CASE|CASES|PALLET|PALLETS)$",
    re.IGNORECASE,
)
QUANTITY_PATTERN = re.compile(
    r"^[+-]?\d[\d,.]*(?:\s*(?:EA|EACH|PC|PCS|PIECE|PIECES|ST|CT|UNIT|UNITS))?$",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"^[+-]?\d[\d,.]*$")
INTEGER_PATTERN = re.compile(r"^[+-]?\d[\d,]*$")
CURRENCY_CODE_PATTERN = re.compile(r"^(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)$", re.I)
CURRENCY_CODE_TOKEN_PATTERN = re.compile(r"\b(USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)\b", re.I)
UNIT_ONLY_PATTERN = re.compile(
    r"^(?:KG|KGS|LB|LBS|POUND|POUNDS|PKG|PKGS|CTN|CTNS|BOX|BOXES|BAG|BAGS|"
    r"BUNDLE|BUNDLES|CARTON|CARTONS|CASE|CASES|PALLET|PALLETS|EA|EACH|PC|PCS|"
    r"PIECE|PIECES|ST|CT|UNIT|UNITS)$",
    re.I,
)

WEIGHT_UNITS = frozenset({"KG", "KGS", "LB", "LBS", "POUND", "POUNDS"})
PACKAGE_UNITS = frozenset({
    "PKG", "PKGS", "CTN", "CTNS", "BOX", "BOXES", "BAG", "BAGS",
    "BUNDLE", "BUNDLES", "CARTON", "CARTONS", "CASE", "CASES",
    "PALLET", "PALLETS",
})
QUANTITY_UNITS = frozenset({"EA", "EACH", "PC", "PCS", "PIECE", "PIECES", "ST", "CT", "UNIT", "UNITS"})

# These are semantic labels, not value-format tokens. In particular, KG/PKG/PCS
# and currency symbols/codes are intentionally absent.
FIELD_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "invoice_no": (
        "invoice no", "invoice number", "invoice #", "invoice nr", "invoice no and date of invoice",
        "invoice no and date", "invoice no & date", "no and date of invoice", "no & date of invoice", "no date of invoice",
        "inv no", "inv number", "inv #", "inv nr", "invoice reference", "invoice ref",
    ),
    "date": ("date of invoice", "invoice date", "inv date", "invoice no and date of invoice", "invoice no and date", "invoice no & date", "no and date of invoice", "no & date of invoice", "date of issue", "date", "dated"),
    "buyer": ("buyer if not consignee", "buyer (if not consignee)", "buyer", "sold to", "bill to", "buyer consignee", "purchaser", "customer", "purchaser name"),
    "seller": ("seller", "exporter", "supplier", "vendor", "sold by", "shipped by"),
    "goods_description": (
        "description of goods", "description of good", "goods description",
        "description of commodity", "commodity description", "description of articles",
        "description of merchandise", "description of contents", "goods and description",
        "description of packages and goods", "description of package and goods",
        "item description", "product description", "description/model",
    ),
    "quantity": ("quantity", "qty", "q'ty", "q ty", "qnty", "order qty", "quantity or weight", "qty unit", "q ty unit"),
    "amount": (
        "total amount", "invoice amount", "total invoice amount", "invoice total",
        "grand total", "total value", "invoice value", "total invoice value",
        "total price", "amount", "value", "total",
    ),
    "currency": ("currency",),
    "number_of_packages": (
        "number of packages", "no of packages", "no packages", "total packages",
        "no of pkgs", "number of pkgs", "packages", "package",
        "no & kinds of packages", "no and kinds of packages", "number & kind of packages",
        "number and kind of packages", "number of containers or packages", "total number of pkgs", "total number of packages", "no & kinds", "pkgs",
    ),
    "gross_weight": (
        "total gross weight", "gross weight", "gross wt", "gross wgt", "grossweight",
        "gross mass", "gross weight kgs", "gross weight kg", "g weight", "gross/w", "g w", "g wt", "g wgt", "g/w", "g/wt", "g/wgt", "gw", "gwt",
    ),
    "bl_no": (
        "b/l no", "b/l number", "b/l #", "bl no", "bl number", "bl #",
        "bill of lading no", "bill of lading number", "b/l serial no", "bill of lading number",
    ),
    "shipper": ("shipper exporter complete name address", "shipper/exporter complete name address", "consignor/shipper", "consignor shipper", "shipper/exporter", "shipper exporter", "shipper", "consignor", "exporter"),
    "consignee": ("consignee provide complete name and address", "consignee complete name address", "consignee",),
    "on_board_date": (
        "laden on board", "laden on board date", "shipped on board", "shipped on board date",
        "on board date", "onboard date", "date on board", "date shipped", "shipped date",
        "date of shipment", "date shipped on board", "on board",
    ),
}

_CONTROL_WORDS = {
    "amount", "carrier", "cbm", "collect", "container", "containers", "currency",
    "date", "delivery", "description", "destination", "discharge", "freight", "gross",
    "hs", "invoice", "issue", "loading", "marks", "measurement", "net", "number",
    "on", "origin", "packages", "package", "party", "payment", "place", "port", "price",
    "quantity", "receipt", "remark", "seal", "shipping", "signature", "signed", "total",
    "unit", "vessel", "voy", "weight", "buyer", "shipper", "consignee",
    "other", "reference", "references",
}


@dataclass(frozen=True)
class LabelSpan:
    field_name: str
    indices: tuple[int, ...]
    text: str


def _normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"\b([a-z]+)'s\b", r"\1", text)
    text = re.sub(r"\bb\s*/\s*l\s*(?:no|number)\b", "b/l no", text)
    text = re.sub(r"\bb\s*/\s*l\b", "b/l", text)
    text = re.sub(r"\bg\s*\.\s*w(?:\s*\.\s*t|\s*\.\s*g\s*t)?\b", "g wt", text)
    text = re.sub(r"[^a-z0-9/'#]+", " ", text)
    return " ".join(text.split())


@lru_cache(maxsize=256)
def _normalize_alias(alias: str) -> str:
    return _normalized(alias)


def _has_alias(text: str, aliases: Sequence[str]) -> bool:
    normalized = f" {_normalized(text)} "
    for alias in aliases:
        target = _normalize_alias(alias)
        if target and f" {target} " in normalized:
            return True
    return False


def _fuzzy_has_alias(text: str, aliases: Sequence[str]) -> bool:
    """Recover labels with small OCR errors while resisting semantic collisions.

    Multi-word labels are compared token-by-token. Short functional tokens such
    as ``to``, ``of`` and ``no`` must remain exact, preventing dangerous matches
    such as ``Bill of`` -> ``Bill to``.
    """
    candidate_tokens = _normalized(text).split()
    if not candidate_tokens:
        return False
    for alias in aliases:
        target = _normalize_alias(alias)
        if len(target) < 5:
            continue
        target_tokens = target.split()
        if len(target_tokens) == 1:
            token_target = target_tokens[0]
            if len(token_target) < 6:
                continue
            for token in candidate_tokens:
                if len(token_target) >= 8 and len(token) < len(token_target) - 1:
                    continue
                if abs(len(token) - len(token_target)) > max(2, len(token_target) // 3):
                    continue
                # Longer labels tolerate two OCR substitutions because the
                # surrounding geometry and field-specific value validator are
                # still required before extraction. Short labels stay strict
                # to avoid collisions such as ``Date``/``Dated``.
                minimum_ratio = 0.80 if len(token_target) >= 8 else 0.86
                if SequenceMatcher(None, token, token_target).ratio() >= minimum_ratio:
                    return True
            continue
        window_size = len(target_tokens)
        if window_size > len(candidate_tokens):
            continue
        for start in range(len(candidate_tokens) - window_size + 1):
            window_tokens = candidate_tokens[start:start + window_size]
            token_scores: list[float] = []
            valid = True
            for candidate, expected in zip(window_tokens, target_tokens):
                if len(expected) <= 3:
                    if candidate != expected:
                        valid = False
                        break
                    token_scores.append(1.0)
                    continue
                score = SequenceMatcher(None, candidate, expected).ratio()
                if score < 0.72:
                    valid = False
                    break
                token_scores.append(score)
            if not valid:
                continue
            window = " ".join(window_tokens)
            if sum(token_scores) / len(token_scores) >= 0.86 and SequenceMatcher(None, window, target).ratio() >= 0.82:
                return True
    return False


def _has_semantic_alias(text: str, aliases: Sequence[str]) -> bool:
    return _has_alias(text, aliases) or _fuzzy_has_alias(text, aliases)


def _equals_alias(text: str, aliases: Sequence[str]) -> bool:
    normalized = _normalized(text)
    return any(normalized == _normalize_alias(alias) for alias in aliases)


def _bounds(prediction: OCRPrediction) -> tuple[int, int, int, int]:
    return min(prediction.x), min(prediction.y), max(prediction.x), max(prediction.y)


def _span_bounds(predictions: Sequence[OCRPrediction], indices: Sequence[int]) -> tuple[int, int, int, int]:
    selected = [_bounds(predictions[index]) for index in indices]
    return (
        min(item[0] for item in selected), min(item[1] for item in selected),
        max(item[2] for item in selected), max(item[3] for item in selected),
    )


def _same_row(first: OCRPrediction, second: OCRPrediction) -> bool:
    _, first_top, _, first_bottom = _bounds(first)
    _, second_top, _, second_bottom = _bounds(second)
    overlap = max(0, min(first_bottom, second_bottom) - max(first_top, second_top))
    first_h = max(1, first_bottom - first_top)
    second_h = max(1, second_bottom - second_top)
    min_h = min(first_h, second_h)
    first_center = (first_top + first_bottom) / 2
    second_center = (second_top + second_bottom) / 2
    center_distance = abs(first_center - second_center)
    # A low overlap threshold caused tall OCR boxes from table headers to
    # bridge two real rows (e.g. the header row merged with the address row
    # above it).  Require both substantial vertical overlap and aligned centers.
    return overlap / min_h >= 0.60 and center_distance <= max(14, min_h * 0.90)


def _row_groups(predictions: Sequence[OCRPrediction]) -> list[list[int]]:
    # Keep this compatibility function because the extractor has several
    # specialized table routines, but source its rows from the shared derived
    # layout.  Raw OCRPrediction objects and their indices are untouched.
    return line_groups(predictions)


def _pure_value_token(text: str) -> bool:
    candidate = text.strip(" :;,.()[]")
    return bool(
        NUMBER_PATTERN.fullmatch(candidate)
        or DATE_PATTERN.fullmatch(candidate)
        or MONEY_PATTERN.fullmatch(candidate)
        or WEIGHT_PATTERN.fullmatch(candidate)
        or PACKAGE_PATTERN.fullmatch(candidate)
        or UNIT_ONLY_PATTERN.fullmatch(candidate)
        or CURRENCY_CODE_PATTERN.fullmatch(candidate)
    )


def find_label_spans(
    predictions: Sequence[OCRPrediction], field_name: str, *, max_span: int = 4,
    aliases: Sequence[str] | None = None,
) -> list[LabelSpan]:
    """Find visible semantic labels, including labels split across OCR boxes.

    The function deliberately does not infer labels from units or value formats.
    """
    aliases = tuple(aliases or FIELD_LABEL_ALIASES[field_name])
    matches: list[LabelSpan] = []
    seen: set[tuple[int, ...]] = set()
    for row in _row_groups(predictions):
        for start in range(len(row)):
            for size in range(1, min(max_span, len(row) - start) + 1):
                indices = tuple(row[start:start + size])
                # A split label may contain punctuation-only/no tokens, but once a
                # clear numeric/value box begins it is no longer a label span.
                if size > 1 and any(_pure_value_token(predictions[index].text) for index in indices):
                    break
                text = " ".join(predictions[index].text for index in indices)
                if field_name == "gross_weight" and "net weight" in _normalized(text) and "gross" not in _normalized(text):
                    continue
                span_aliases = aliases if size == 1 else tuple(
                    alias for alias in aliases if len(_normalize_alias(alias).split()) > 1
                )
                if span_aliases and _has_semantic_alias(text, span_aliases):
                    if indices not in seen:
                        matches.append(LabelSpan(field_name, indices, text))
                        seen.add(indices)
                    break
    # Vertical split labels are common in narrow table headers (e.g. GROSS / WEIGHT),
    # but joining party labels vertically would merge unrelated blocks such as
    # SHIPPER and CONSIGNEE. Restrict vertical joins to composite labels.
    if field_name not in {"gross_weight", "invoice_no", "bl_no", "number_of_packages", "on_board_date", "goods_description"}:
        return sorted(matches, key=lambda span: (min(min(predictions[index].y) for index in span.indices), min(min(predictions[index].x) for index in span.indices)))
    rows = _row_groups(predictions)
    for row_index, row in enumerate(rows[:-1]):
        next_row = rows[row_index + 1]
        for first in row:
            left1, top1, right1, bottom1 = _bounds(predictions[first])
            width1 = max(1, right1 - left1)
            for second in next_row:
                left2, top2, right2, bottom2 = _bounds(predictions[second])
                overlap = max(0, min(right1, right2) - max(left1, left2))
                width2 = max(1, right2 - left2)
                gap = top2 - bottom1
                if overlap / min(width1, width2) < 0.35 or gap < -5 or gap > max(60, (bottom1 - top1) * 2):
                    continue
                indices = (first, second)
                if any(_pure_value_token(predictions[index].text) for index in indices):
                    continue
                text = f"{predictions[first].text} {predictions[second].text}"
                # Vertical composition must form the label itself. Using the
                # looser substring matcher here can accidentally combine an
                # unrelated row with a real label/value below it (e.g.
                # ``INV.DATE`` + ``Goods`` or ``Goods`` + ``ABC-123``).
                if (_equals_alias(text, aliases) or _fuzzy_has_alias(text, aliases)) and indices not in seen:
                    matches.append(LabelSpan(field_name, indices, text))
                    seen.add(indices)
    # Prefer the shortest/most specific label span when a larger span only wraps
    # the same label with unrelated neighboring words. Example: GT/OCR may yield
    # ``Taiwan | Invoice | Number``; ``Invoice Number`` is the real anchor.
    filtered: list[LabelSpan] = []
    for span in matches:
        superseded = False
        span_set = set(span.indices)
        for other in matches:
            if other is span:
                continue
            other_set = set(other.indices)
            if other_set < span_set and _has_semantic_alias(other.text, aliases):
                superseded = True
                break
        if not superseded:
            filtered.append(span)
    return sorted(filtered, key=lambda span: (min(min(predictions[index].y) for index in span.indices), min(min(predictions[index].x) for index in span.indices), len(span.indices)))


def _visual_order_indices(predictions: Sequence[OCRPrediction]) -> list[int]:
    return sorted(range(len(predictions)), key=lambda index: (min(predictions[index].y), min(predictions[index].x), index))


def _embedded(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    patterns: Sequence[re.Pattern[str]],
) -> FieldEvidence | None:
    for index, prediction in enumerate(predictions):
        for pattern in patterns:
            match = pattern.search(prediction.text)
            if match:
                value = match.group("value").strip(" ,:;")
                if value:
                    return make_field_evidence(field_name, list(predictions), (index,), value)
    return None


def _combine_text(predictions: Sequence[OCRPrediction], indices: Sequence[int]) -> str:
    return " ".join(predictions[index].text.strip() for index in indices if predictions[index].text.strip())


def _line_embedded(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    patterns: Sequence[re.Pattern[str]],
    value_pattern: re.Pattern[str] | Callable[[str], bool],
) -> FieldEvidence | None:
    """Read a key/value expression reconstructed from several OCR boxes.

    MMOCR/ViTSTR frequently returns ``TOTAL | GROSS | WEIGHT | 89 | KG``
    instead of one prediction.  The line is a derived view only; evidence still
    points to the original prediction indices and never replaces raw OCR.
    """
    for line in reconstruct_layout(predictions).lines:
        for pattern in patterns:
            match = pattern.search(line.text)
            if not match:
                continue
            value = match.group("value").strip(" ,:;")
            if not value or _matched_value(value_pattern, value) is None:
                continue
            value_start, value_end = match.span("value")
            offsets: list[tuple[int, int, int]] = []
            cursor = 0
            for index in line.indices:
                token_text = predictions[index].text.strip()
                token_start = line.text.find(token_text, cursor)
                if token_start < 0:
                    token_start = cursor
                token_end = token_start + len(token_text)
                offsets.append((index, token_start, token_end))
                cursor = token_end + 1
            value_indices = tuple(
                index for index, token_start, token_end in offsets
                if token_end > value_start and token_start < value_end
            ) or line.indices
            return make_field_evidence(
                field_name, list(predictions), value_indices, value,
                reason="value reconstructed from scale-aware OCR line",
            )
    return None


def _candidate_groups_near_span(
    predictions: Sequence[OCRPrediction], span: LabelSpan, *, max_group: int = 6
) -> list[tuple[tuple[int, int, int], tuple[int, ...]]]:
    """Return contiguous value groups near a label, sorted by geometric priority."""
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    anchor_left, anchor_top, anchor_right, anchor_bottom = _span_bounds(predictions, span.indices)
    anchor_center = (anchor_left + anchor_right) / 2
    anchor_width = max(1, anchor_right - anchor_left)
    anchor_rows = sorted({index_to_row[index] for index in span.indices})
    anchor_row = anchor_rows[0]
    occupied = set(span.indices)
    results: list[tuple[tuple[int, int, int], tuple[int, ...]]] = []
    layout = reconstruct_layout(predictions)
    token_by_index = {token.index: token for token in layout.tokens}
    # Adjacent words in a reconstructed line may be separated by a document
    # scale-dependent gap.  Do not let a value candidate span into the next
    # table column merely because all boxes share the same y coordinate.
    max_join_gap = max(24.0, layout.median_height * 4.0)

    def contiguous(group: Sequence[int]) -> bool:
        ordered = sorted(group, key=lambda index: token_by_index[index].left)
        return all(
            token_by_index[second].left - token_by_index[first].right <= max_join_gap
            for first, second in zip(ordered, ordered[1:])
        )

    # Same-row values to the right. Composite labels can be split vertically,
    # so inspect every row occupied by the label rather than only its first row.
    for label_row_no in anchor_rows:
        row = rows[label_row_no]
        row_label_indices = [index for index in span.indices if index_to_row[index] == label_row_no]
        local_right = max(max(predictions[index].x) for index in row_label_indices)
        right_positions = [
            index for index in row
            if index not in occupied and min(predictions[index].x) >= local_right - 5
        ]
        for pos in range(len(right_positions)):
            for size in range(1, min(max_group, len(right_positions) - pos) + 1):
                group = tuple(right_positions[pos:pos + size])
                if not contiguous(group):
                    continue
                gap = max(0, min(min(predictions[index].x) for index in group) - local_right)
                results.append(((label_row_no - anchor_row, int(gap), size), group))

    # Values below, prioritizing the same column / x-overlap.
    for row_no in range(anchor_row + 1, min(len(rows), anchor_row + 8)):
        below_row = rows[row_no]
        row_top = min(min(predictions[index].y) for index in below_row)
        vertical_gap = max(0, row_top - anchor_bottom)
        if vertical_gap > 600:
            break
        aligned: list[int] = []
        for index in below_row:
            left, _, right, _ = _bounds(predictions[index])
            center = (left + right) / 2
            overlap = max(0, min(anchor_right, right) - max(anchor_left, left))
            if overlap > 0 or abs(center - anchor_center) <= max(70, anchor_width * 0.75):
                aligned.append(index)
        if not aligned:
            continue
        aligned.sort(key=lambda index: min(predictions[index].x))
        for pos in range(len(aligned)):
            for size in range(1, min(max_group, len(aligned) - pos) + 1):
                group = tuple(aligned[pos:pos + size])
                if not contiguous(group):
                    continue
                group_center = sum((min(predictions[index].x) + max(predictions[index].x)) / 2 for index in group) / len(group)
                horizontal = int(abs(group_center - anchor_center))
                results.append(((1 + row_no - anchor_row, vertical_gap + horizontal, size), group))

    dedup: dict[tuple[int, ...], tuple[int, int, int]] = {}
    for score, group in results:
        if group not in dedup or score < dedup[group]:
            dedup[group] = score
    return sorted((score, group) for group, score in dedup.items())


def _call_matcher(matcher: re.Pattern[str] | Callable[[str], bool], text: str) -> bool:
    if hasattr(matcher, "search"):
        return bool(matcher.search(text))  # type: ignore[union-attr]
    return bool(matcher(text))


def _matched_value(matcher: re.Pattern[str] | Callable[[str], bool], text: str) -> str | None:
    if hasattr(matcher, "search"):
        match = matcher.search(text)  # type: ignore[union-attr]
        if not match:
            return None
        try:
            value = match.group("value")
        except (IndexError, KeyError):
            value = match.group(0)
        return value.strip(" ,:;")
    return text if matcher(text) else None


def _labeled_value(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    aliases: Sequence[str] | None,
    value_pattern: re.Pattern[str] | Callable[[str], bool],
    *,
    allow_ambiguous: bool = False,
) -> FieldEvidence:
    # aliases is retained for backward-compatible callers; semantic label spans
    # use the central field contract when available.
    spans = find_label_spans(predictions, field_name) if field_name in FIELD_LABEL_ALIASES else []
    if aliases is not None and not spans:
        # fallback for an internal/special field with caller-supplied aliases
        temp_aliases = tuple(aliases)
        spans = [
            LabelSpan(field_name, (index,), prediction.text)
            for index, prediction in enumerate(predictions)
            if _has_alias(prediction.text, temp_aliases)
        ]
    matches: list[tuple[tuple[int, int, int], tuple[int, ...], str]] = []
    for span in spans:
        for score, group in _candidate_groups_near_span(predictions, span):
            text = _combine_text(predictions, group)
            value = _matched_value(value_pattern, text)
            if value is not None:
                matches.append((score, group, value))
                break
    if not matches:
        return missing_field(field_name, "semantic label and compatible neighboring value not found")
    matches.sort(key=lambda item: item[0])
    best_score = matches[0][0]
    best = [item for item in matches if item[0][:2] == best_score[:2]]
    if allow_ambiguous and len(best) > 1:
        indices = tuple(index for _, group, _ in best for index in group)
        values = [text for _, _, text in best]
        return make_field_evidence(
            field_name, list(predictions), indices, " | ".join(values),
            status="ambiguous", reason="multiple equally plausible anchored values",
        )
    _, indices, text = matches[0]
    return make_field_evidence(field_name, list(predictions), indices, text)



def _alias_rank(text: str, aliases: Sequence[str]) -> tuple[int, int, int]:
    """Rank a label span by alias priority, exactness, and specificity."""
    normalized = _normalized(text)
    for index, alias in enumerate(aliases):
        target = _normalize_alias(alias)
        if target and f" {target} " in f" {normalized} ":
            return (index, 0, -len(target))
    for index, alias in enumerate(aliases):
        if _fuzzy_has_alias(text, (alias,)):
            return (index, 1, -len(_normalize_alias(alias)))
    return (len(aliases), 2, 0)


def _ranked_labeled_value(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    aliases: Sequence[str],
    matcher: re.Pattern[str] | Callable[[str], bool],
    *,
    prefer_bottom: bool = False,
    max_y_ratio: float | None = None,
) -> FieldEvidence:
    """Extract a value while ranking semantic labels instead of first-hit order.

    This is used for fields such as invoice totals/dates where a document can
    contain many generic ``Amount``/``Date`` labels.  Strong aliases win before
    geometry, and bottom-most labels can be preferred for document totals.
    """
    spans = find_label_spans(predictions, field_name, aliases=aliases)
    if not spans:
        return missing_field(field_name, "semantic label not found")
    page_bottom = max((max(item.y) for item in predictions), default=1)
    candidates: list[tuple[tuple[object, ...], tuple[int, ...], str]] = []
    for span in spans:
        _, span_top, _, span_bottom = _span_bounds(predictions, span.indices)
        if max_y_ratio is not None and span_top > page_bottom * max_y_ratio:
            continue
        for geometric_score, group in _candidate_groups_near_span(predictions, span):
            text = _combine_text(predictions, group)
            value = _matched_value(matcher, text)
            if value is None:
                continue
            alias_score = _alias_rank(span.text, aliases)
            vertical_score = -span_bottom if prefer_bottom else span_top
            confidence = sum(predictions[index].score for index in group) / len(group)
            # Alias identity remains primary, while the remaining terms make
            # the decision reproducible across detector order: line relation,
            # relative distance and OCR confidence all contribute.
            score = (*alias_score, vertical_score, *geometric_score, -round(confidence, 4))
            candidates.append((score, group, value))
    if not candidates:
        return missing_field(field_name, "semantic label found but compatible neighboring value not found")
    candidates.sort(key=lambda item: item[0])
    best_score, indices, text = candidates[0]
    if len(candidates) > 1:
        second_score, second_indices, second_text = candidates[1]
        # Two distinct values attached to the same semantic label and with the
        # same local geometry are not safely resolvable.  Keep both as evidence
        # so callers can route the document to review instead of silently
        # selecting a nearby number.
        same_label = best_score[:5] == second_score[:5]
        close_geometry = best_score[5:7] == second_score[5:7]
        if same_label and close_geometry and _normalized(text) != _normalized(second_text):
            return make_field_evidence(
                field_name,
                list(predictions),
                tuple(index for index in (*indices, *second_indices)),
                f"{text} | {second_text}",
                status="ambiguous",
                reason="multiple semantically valid values have indistinguishable label geometry",
            )
    return make_field_evidence(field_name, list(predictions), indices, text)


def _embedded_candidates(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    patterns: Sequence[tuple[int, re.Pattern[str]]],
    *,
    prefer_bottom: bool = False,
) -> FieldEvidence | None:
    """Return the best embedded semantic key/value candidate.

    ``priority`` is lower-is-better.  This avoids the old first-hit behaviour
    where an arbitrary line-item ``Amount``/``Date`` could beat a document-level
    total/date that appears later on the page.
    """
    found: list[tuple[tuple[int, int], int, str]] = []
    for index, prediction in enumerate(predictions):
        top = min(prediction.y)
        bottom = max(prediction.y)
        for priority, pattern in patterns:
            match = pattern.search(prediction.text)
            if not match:
                continue
            value = match.group("value").strip(" ,:;")
            if not value:
                continue
            vertical = -bottom if prefer_bottom else top
            found.append(((priority, vertical), index, value))
    if not found:
        return None
    found.sort(key=lambda item: item[0])
    _, index, value = found[0]
    return make_field_evidence(field_name, list(predictions), (index,), value)


def _header_column_bounds(
    predictions: Sequence[OCRPrediction],
    span: LabelSpan,
) -> tuple[float, float]:
    """Infer the horizontal cell occupied by a header from peers on its row."""
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    row_no = min(index_to_row[index] for index in span.indices if index in index_to_row)
    left, _, right, _ = _span_bounds(predictions, span.indices)
    center = (left + right) / 2
    peers = []
    for index in rows[row_no]:
        if index in span.indices:
            continue
        l, _, r, _ = _bounds(predictions[index])
        c = (l + r) / 2
        # Ignore tiny OCR fragments that are likely duplicate tile detections.
        if r - l < 8:
            continue
        peers.append(c)
    left_peer = max((c for c in peers if c < center), default=None)
    right_peer = min((c for c in peers if c > center), default=None)
    column_left = (left_peer + center) / 2 if left_peer is not None else left - max(40, right - left)
    column_right = (right_peer + center) / 2 if right_peer is not None else right + max(320, (right - left) * 1.5)
    return column_left, column_right


def _date_below_invoice_header(
    predictions: Sequence[OCRPrediction],
    aliases: Sequence[str],
) -> FieldEvidence | None:
    """Recover dates from compound headers such as ``Invoice No. and date``."""
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    candidates: list[tuple[tuple[int, int], int, str]] = []
    for span in find_label_spans(predictions, "date", aliases=aliases):
        anchor_row = min(index_to_row[index] for index in span.indices if index in index_to_row)
        left, _, right, bottom = _span_bounds(predictions, span.indices)
        # Compound invoice/date cells are often wide.  The date is normally in
        # the right half of that cell, while the invoice number is on the left.
        cell_left, cell_right = _header_column_bounds(predictions, span)
        split = left + (right - left) * 0.45
        search_left = max(cell_left, split - 40)
        search_right = max(cell_right, right + 360)
        for row_no in range(anchor_row, min(len(rows), anchor_row + 5)):
            for index in rows[row_no]:
                if index in span.indices:
                    continue
                l, t, r, _ = _bounds(predictions[index])
                if t < bottom - 8 or l < search_left or l > search_right:
                    continue
                match = DATE_PATTERN.search(predictions[index].text)
                if match:
                    vertical_gap = max(0, t - bottom)
                    # Prefer the closest date and, within the row, the rightmost
                    # date because L/C date is usually in a lower separate cell.
                    candidates.append(((vertical_gap, -l), index, match.group(0)))
        if candidates:
            break
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    _, index, value = candidates[0]
    return make_field_evidence("date", list(predictions), (index,), value)


def _invoice_date_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    embedded = _embedded_candidates(
        "date",
        predictions,
        [
            (0, re.compile(r"(?:date\s+of\s+invoice|invoice\s+date|inv\.?\s*date|date\s+of\s+issue)\s*[:#-]?\s*(?P<value>" + DATE_PATTERN.pattern + r")", re.I)),
            (2, re.compile(r"^\s*(?:date|dated)\s*[:#-]\s*(?P<value>" + DATE_PATTERN.pattern + r")\s*$", re.I)),
        ],
    )
    if embedded is not None:
        return embedded

    compound_aliases = (
        "invoice no and date of invoice", "invoice no and date", "invoice no & date",
        "no and date of invoice", "no & date of invoice", "no date of invoice",
    )
    compound = _date_below_invoice_header(predictions, compound_aliases)
    if compound is not None:
        return compound

    strong = _ranked_labeled_value(
        "date",
        predictions,
        ("date of invoice", "invoice date", "inv date", "date of issue"),
        DATE_PATTERN,
        max_y_ratio=0.60,
    )
    if strong.status != "missing":
        return strong

    # OCR month confusions such as ``22-0ct-2007`` are common in otherwise
    # correctly detected Date-of-Issue cells. Repair only the month token.
    for label_index,label in enumerate(predictions):
        norm=_normalized(label.text)
        if norm not in {"date of issue","invoice date","date of invoice","inv date"}:
            continue
        ll,lt,lr,lb=_bounds(label); lc=(ll+lr)/2
        for i,item in enumerate(predictions):
            if i==label_index: continue
            il,it,ir,_=_bounds(item); ic=(il+ir)/2
            if it < lt-10 or it > lb+140 or abs(ic-lc)>350:
                continue
            value=_date_candidate(item.text)
            if value:
                return make_field_evidence("date",list(predictions),(i,),value,reason="minor OCR month confusion repaired" if value != item.text.strip(" ,:;") else None)

    # Some simple invoices print just ``Date``.  Accept this only in the upper
    # header area and reject known shipping/payment date contexts.
    aliases = ("date", "dated")
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    rejected_date_contexts = (
        "date of departure", "date of shipment", "date of loading", "date of delivery",
        "date shipped", "on board", "payment due", "due date", "l/c", "letter of credit",
    )
    spans = []
    for span in find_label_spans(predictions, "date", aliases=aliases):
        if _normalized(span.text) not in {_normalize_alias(alias) for alias in aliases}:
            continue
        row_no = index_to_row.get(span.indices[0])
        row_text = " ".join(predictions[index].text for index in rows[row_no]) if row_no is not None else span.text
        if any(context in _normalized(row_text) for context in rejected_date_contexts):
            continue
        spans.append(span)
    page_bottom = max((max(item.y) for item in predictions), default=1)
    candidates: list[tuple[tuple[int, int, int], tuple[int, ...], str]] = []
    for span in spans:
        if min(min(predictions[index].y) for index in span.indices) > page_bottom * 0.42:
            continue
        for score, group in _candidate_groups_near_span(predictions, span):
            value = _matched_value(DATE_PATTERN, _combine_text(predictions, group))
            if value is not None:
                candidates.append((score, group, value))
                break
    if not candidates:
        return missing_field("date", "invoice date not printed or not recoverable")
    candidates.sort(key=lambda item: item[0])
    _, indices, value = candidates[0]
    return make_field_evidence("date", list(predictions), indices, value)


def _invoice_total_amount_column(predictions: Sequence[OCRPrediction]) -> tuple[bool, FieldEvidence | None]:
    """Read a table-style ``TOTAL AMOUNT`` column without crossing columns.

    This intentionally uses a compact exact/near-exact header scan instead of
    the general fuzzy label engine because it runs on every invoice and should
    stay cheap even on dense OCR output.
    """
    rows = _row_groups(predictions)
    page_bottom = max((max(item.y) for item in predictions), default=1)
    strong_headers = {
        "total amount", "total invoice amount", "invoice total amount",
        "total value", "total price",
    }
    saw_header = False
    for anchor_row, row in enumerate(rows):
        candidates: list[LabelSpan] = []
        for pos, index in enumerate(row):
            text = _normalized(predictions[index].text)
            if text in strong_headers:
                candidates.append(LabelSpan("amount", (index,), predictions[index].text))
            if pos + 1 < len(row):
                pair=(index,row[pos+1])
                joined=_normalized(_combine_text(predictions,pair))
                if joined in strong_headers:
                    candidates.append(LabelSpan("amount", pair, _combine_text(predictions,pair)))
        for span in candidates:
            left, top, right, bottom = _span_bounds(predictions, span.indices)
            if top > page_bottom * 0.80:
                continue
            row_text = _normalized(" ".join(predictions[index].text for index in row))
            if not any(marker in row_text for marker in ("qty", "q ty", "quantity", "price", "description", "goods")):
                continue
            saw_header = True
            center=(left+right)/2
            peer_centers=[]
            for i in row:
                if i in span.indices:
                    continue
                l,_,r,_=_bounds(predictions[i])
                if r-l >= 8:
                    peer_centers.append((l+r)/2)
            left_peer=max((c for c in peer_centers if c<center),default=None)
            right_peer=min((c for c in peer_centers if c>center),default=None)
            col_left=(left_peer+center)/2 if left_peer is not None else left-max(25,(right-left)*0.2)
            col_right=(right_peer+center)/2 if right_peer is not None else right+max(80,(right-left)*0.8)
            # Never expand left far enough to swallow the adjacent unit-price cell.
            col_left=max(col_left,left-max(25,(right-left)*0.2))
            col_right=min(col_right,right+max(80,(right-left)*0.8))
            values=[]
            for row_no in range(anchor_row+1,len(rows)):
                current=rows[row_no]
                row_top=min(min(predictions[i].y) for i in current)
                if row_top-bottom>1800:
                    break
                norm=_normalized(" ".join(predictions[i].text for i in current))
                if any(marker in norm for marker in ("saying in", "signed by", "remark", "terms and conditions")):
                    break
                row_is_total=_has_semantic_alias(norm,("total","grand total"))
                for pos,i in enumerate(current):
                    l,_,r,_=_bounds(predictions[i]); c=(l+r)/2
                    if not (col_left<=c<=col_right):
                        continue
                    groups=[(i,)]
                    if pos+1<len(current): groups.append((i,current[pos+1]))
                    if pos>0: groups.append((current[pos-1],i))
                    for group in groups:
                        value=_matched_value(_money_value,_combine_text(predictions,group))
                        if value is not None:
                            gc=sum((min(predictions[j].x)+max(predictions[j].x))/2 for j in group)/len(group)
                            values.append(((0 if row_is_total else 1,row_top,abs(gc-center)),group,value))
                            break
            if values:
                totals=[item for item in values if item[0][0]==0]
                if totals:
                    totals.sort(key=lambda item:item[0]); _,group,value=totals[-1]
                    return True,make_field_evidence("amount",list(predictions),group,value)
                unique=[]
                for item in values:
                    if item[2] not in unique: unique.append(item[2])
                if len(unique)==1:
                    _,group,value=values[0]
                    return True,make_field_evidence("amount",list(predictions),group,value)
                return True,None
    return saw_header,None


def _semantic_party_guard(field_name: str, evidence: FieldEvidence) -> FieldEvidence:
    """Downgrade obvious form captions/address labels instead of emitting them."""
    if evidence.status == "missing" or not evidence.value:
        return evidence
    norm = _normalized(evidence.value)
    forbidden_exact = {
        "address", "address adpec", "address adpec ", "bill", "bill o",
        "description of packages and goods", "description of package and goods",
        "consignee", "shipper", "buyer", "exporter", "seller", "notify party",
    }
    forbidden_contains = (
        "invoice no", "invoice number", "booking no", "bill of lading",
        "gross weight", "measurement", "description of packages",
        "particulars furnished", "port of loading", "port of discharge",
        "country of origin", "country of final destination", "date shipped",
        "negotiable", "multimodal", "transport document", "fbl",
    )
    if norm.rstrip(":") in {item.rstrip(":") for item in forbidden_exact} or any(x in norm for x in forbidden_contains):
        return missing_field(field_name, "candidate was a form caption/control label, not a party name")
    # Logistics templates frequently print an empty party-cell instruction such
    # as ``Please provide complete name and address``.  AI-Hub may split or
    # distort that caption (for example ``Tlease proydde compleee name``), so
    # use the stable semantic anchors rather than requiring an exact phrase.
    if (
        ("provide" in norm or "proydde" in norm or "pryvde" in norm)
        and ("complete" in norm or "compleee" in norm)
        and "name" in norm
    ):
        return missing_field(field_name, "candidate was an empty-party instruction caption")
    if norm.startswith("address") and len(norm.split()) <= 4:
        return missing_field(field_name, "address label is not a party name")
    return evidence


def _invoice_amount_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    column_header_seen, column_amount = _invoice_total_amount_column(predictions)
    if column_header_seen:
        if column_amount is not None:
            return column_amount
        return missing_field("amount", "TOTAL AMOUNT column is present but no safe document-total value was recovered")

    # Prefer embedded invoice-level totals.  This directly handles the common
    # Fintra templates: ``TOTAL: $39,583.47``, ``Total $3,985.55`` and similar.
    total_money = re.compile(
        r"(?:grand\s+total|total\s+invoice\s+amount|total\s+amount|invoice\s+total|"
        r"total\s+invoice\s+value|invoice\s+value|total\s+value|total\s+price|total)"
        r"\s*[:#=-]?\s*(?P<value>(?:(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)\s*|[$€£¥]\s*)?"
        r"[+-]?\d[\d,]*(?:\.\d+)?(?:\s*(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD))?)",
        re.I,
    )
    embedded = _embedded_candidates(
        "amount", predictions,
        [
            (0, re.compile(r"(?:grand\s+total|total\s+invoice\s+amount|invoice\s+total)\s*[:#=-]?\s*(?P<value>(?:(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)\s*|[$€£¥]\s*)?[+-]?\d[\d,]*(?:\.\d+)?(?:\s*(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD))?)", re.I)),
            (1, total_money),
        ],
        prefer_bottom=True,
    )
    if embedded is not None:
        return embedded

    # Next use a strong semantic total label with a neighbouring money value.
    strong = _ranked_labeled_value(
        "amount",
        predictions,
        (
            "grand total", "total invoice amount", "invoice total", "total amount",
            "total invoice value", "invoice value", "total value", "total price", "total",
        ),
        _money_value,
        prefer_bottom=True,
    )
    if strong.status != "missing":
        # A generic ``Total`` caption can sit beside a one-character table
        # fragment while the real monetary tokens are elsewhere on a dense
        # AI-Hub page.  Keep a legitimate bare total (e.g. ``Total: 5``), but
        # fail closed when an explicit currency token makes that fragment
        # ambiguous.  This prevents a clearly unrelated ``4`` from becoming
        # the document total.
        value = (strong.value or "").strip()
        if re.fullmatch(r"\d{1,2}", value) and any(
            _explicit_money_token(item.text)
            for index, item in enumerate(predictions)
            if index not in strong.source_indices
        ):
            return missing_field(
                "amount",
                "generic total label matched a small bare number while another explicit money token was present",
            )
        return strong
    return missing_field("amount", "invoice-level total amount not recovered")


def _consignee_as_buyer(predictions: Sequence[OCRPrediction], *, explicit_reference: bool) -> FieldEvidence:
    aliases = (
        "consignee for account risk of messrs", "consignee", "consignee name",
    )
    # Party blocks must be read below/inside the consignee cell, not with the
    # generic right-neighbour matcher (which can grab Port & Country etc.).
    evidence = _party_block_below_label("buyer", predictions, aliases, max_y_ratio=0.72)
    if evidence.status == "missing":
        return evidence
    return make_field_evidence(
        "buyer",
        list(predictions),
        evidence.source_indices,
        evidence.value,
        status="found" if explicit_reference else "ambiguous",
        reason=(
            "buyer explicitly refers to consignee; resolved from consignee block"
            if explicit_reference
            else "buyer label absent; consignee retained as a counterparty proxy requiring review"
        ),
    )



def _expand_party_evidence(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    evidence: FieldEvidence,
) -> FieldEvidence:
    """Expand a party's first OCR token to the complete company-name line.

    Geometry matching intentionally anchors on the first token near the label;
    this second step then walks right on that same line.  It stops at large cell
    gaps, phone/address-heavy tokens, or semantic control labels so neighboring
    table cells are not swallowed.
    """
    if evidence.status == "missing" or not evidence.source_indices:
        return evidence
    # Embedded key/value OCR boxes (e.g. ``Buyer: ACME LTD``) already carry
    # a deliberately sliced value. Expanding from the original box would put
    # the label text back into the extracted value.
    if len(evidence.source_indices) == 1 and evidence.value and evidence.raw_text.strip() != evidence.value.strip():
        return evidence
    rows = _row_groups(predictions)
    seed = evidence.source_indices[0]
    row = next((item for item in rows if seed in item), None)
    if row is None:
        return evidence
    positions = [row.index(index) for index in evidence.source_indices if index in row]
    if not positions:
        return evidence
    start = min(positions)
    end = max(positions)
    selected = list(row[start:end + 1])
    previous_right = max(_bounds(predictions[index])[2] for index in selected)
    base_height = max(1, max(_bounds(predictions[index])[3] - _bounds(predictions[index])[1] for index in selected))
    for position in range(end + 1, min(len(row), end + 7)):
        index = row[position]
        left, _, right, _ = _bounds(predictions[index])
        gap = left - previous_right
        if gap > max(70, base_height * 4):
            break
        token = predictions[index].text.strip()
        normalized = _normalized(token)
        if not token:
            continue
        if normalized in _CONTROL_WORDS or _has_semantic_alias(token, tuple(alias for values in FIELD_LABEL_ALIASES.values() for alias in values)):
            break
        if re.search(r"\b(?:tel|fax|zip|code)\b", normalized) or re.search(r"\d{4,}", normalized):
            break
        selected.append(index)
        previous_right = right
    selected = list(_dedupe_party_indices(predictions, selected))
    value = _combine_text(predictions, selected)
    if not _party_value(value):
        return evidence
    return make_field_evidence(
        field_name,
        list(predictions),
        tuple(selected),
        value,
        status=evidence.status,
        reason=evidence.reason,
    )


def _buyer_candidate_value(text: str) -> bool:
    normalized = _normalized(text)
    if normalized in {"same to consignee", "same as consignee", "same consignee"}:
        return True
    return _party_value(text)



def _buyer_labeled_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    spans = find_label_spans(predictions, "buyer")
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    candidates: list[tuple[tuple[int, int, int], tuple[int, ...], str]] = []
    for span in spans:
        row_no = index_to_row.get(span.indices[0])
        if row_no is not None:
            row_text = _normalized(" ".join(predictions[index].text for index in rows[row_no]))
            if any(marker in row_text for marker in ("buyer reference", "buyer ref", "buyers ref", "buyer s ref")):
                continue
        for score, group in _candidate_groups_near_span(predictions, span):
            value = _combine_text(predictions, group)
            if _buyer_candidate_value(value):
                candidates.append((score, group, value))
                break
    if not candidates:
        return missing_field("buyer", "buyer/sold-to/bill-to label and compatible value not recovered")
    candidates.sort(key=lambda item: item[0])
    _, indices, value = candidates[0]
    return make_field_evidence("buyer", list(predictions), indices, value)


def _invoice_buyer_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    explicit = _embedded(
        "buyer", predictions,
        [re.compile(r"(?:buyer|sold\s+to|bill\s+to)\s*[:#-]\s*(?P<value>.+)", re.I)],
    ) or _buyer_labeled_value(predictions)
    if explicit.status != "missing":
        normalized = _normalized(explicit.value or "")
        if normalized in {"same to consignee", "same as consignee", "same consignee"}:
            resolved = _consignee_as_buyer(predictions, explicit_reference=True)
            if resolved.status != "missing":
                return resolved
            return make_field_evidence(
                "buyer", list(predictions), explicit.source_indices, explicit.value,
                status="ambiguous", reason="buyer references consignee but consignee value was not recovered",
            )
        return _expand_party_evidence("buyer", predictions, explicit)
    proxy = _consignee_as_buyer(predictions, explicit_reference=False)
    if proxy.status != "missing":
        return proxy
    return missing_field("buyer", "buyer/sold-to/bill-to label and consignee proxy not found")


def _invoice_seller_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    """Extract an explicitly labelled invoice seller/exporter/supplier only."""
    aliases = FIELD_LABEL_ALIASES["seller"]
    embedded = _embedded(
        "seller", predictions,
        [re.compile(r"(?:seller|exporter|supplier|vendor|sold\s+by)\s*[:#-]\s*(?P<value>.+)", re.I)],
    )
    evidence = embedded or _party_block_below_label(
        "seller", predictions, aliases, max_y_ratio=0.55
    )
    if evidence.status == "missing":
        return evidence
    return _semantic_party_guard("seller", _expand_party_evidence("seller", predictions, evidence))


def _column_value_groups(
    predictions: Sequence[OCRPrediction], header: LabelSpan, matcher: Callable[[str], bool],
    *, stop_aliases: Sequence[str] = (), max_rows: int = 100,
) -> list[tuple[int, ...]]:
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    header_row = min(index_to_row[index] for index in header.indices)
    left, _, right, bottom = _span_bounds(predictions, header.indices)
    center = (left + right) / 2
    width = max(1, right - left)

    # Infer table-column boundaries from other semantic headers on the same
    # header row. This prevents a description column from swallowing the
    # adjacent quantity/amount token when OCR boxes are close together.
    peer_centers: list[float] = []
    for peer_field in ("goods_description", "quantity", "amount", "number_of_packages", "gross_weight"):
        for peer in find_label_spans(predictions, peer_field):
            peer_rows = {index_to_row[index] for index in peer.indices if index in index_to_row}
            if header_row not in peer_rows or set(peer.indices) == set(header.indices):
                continue
            peer_left, _, peer_right, _ = _span_bounds(predictions, peer.indices)
            peer_centers.append((peer_left + peer_right) / 2)
    left_peers = [value for value in peer_centers if value < center]
    right_peers = [value for value in peer_centers if value > center]
    column_left = (max(left_peers) + center) / 2 if left_peers else float("-inf")
    column_right = (min(right_peers) + center) / 2 if right_peers else float("inf")

    def group_in_column(group: Sequence[int]) -> bool:
        for index in group:
            token_left, _, token_right, _ = _bounds(predictions[index])
            token_center = (token_left + token_right) / 2
            if not (column_left <= token_center <= column_right):
                return False
        return True

    results: list[tuple[int, ...]] = []

    # Some documents use a key/value row instead of a conventional table, e.g.
    # ``QUANTITY | 5000``. Treat a compatible value immediately to the right of
    # the semantic header as an anchored value before scanning rows below. This
    # is still label-first; a bare 5000 elsewhere is not a quantity.
    if header.field_name == "quantity":
        header_members = set(header.indices)
        same_row = rows[header_row]
        right_side = [
            index for index in same_row
            if index not in header_members and min(predictions[index].x) >= right - 5
        ]
        for position in range(len(right_side)):
            for size in range(1, min(3, len(right_side) - position) + 1):
                group = tuple(right_side[position:position + size])
                if group_in_column(group) and matcher(_combine_text(predictions, group)):
                    return [group]

    for row_no in range(header_row + 1, min(len(rows), header_row + 1 + max_rows)):
        row = rows[row_no]
        if any(_has_alias(predictions[index].text, stop_aliases) for index in row):
            break
        row_top = min(min(predictions[index].y) for index in row)
        if row_top - bottom > 2500:
            break
        ranked = sorted(
            row,
            key=lambda index: abs(((min(predictions[index].x) + max(predictions[index].x)) / 2) - center),
        )
        if not ranked:
            continue
        # Try the nearest token and its immediate neighbors so `614` + `KG`
        # or split dates can be reconstructed.
        nearest_pos = row.index(ranked[0])
        candidate_groups: list[tuple[int, ...]] = []
        for start in range(max(0, nearest_pos - 1), min(len(row), nearest_pos + 2)):
            for size in range(1, min(3, len(row) - start) + 1):
                group = tuple(row[start:start + size])
                if not group_in_column(group):
                    continue
                group_center = sum((min(predictions[i].x) + max(predictions[i].x)) / 2 for i in group) / len(group)
                if abs(group_center - center) > max(120, width * 1.25):
                    continue
                candidate_groups.append(group)
        chosen = None
        for group in sorted(candidate_groups, key=lambda g: (len(g), abs(sum((min(predictions[i].x)+max(predictions[i].x))/2 for i in g)/len(g)-center))):
            if matcher(_combine_text(predictions, group)):
                chosen = group
                break
        if chosen:
            results.append(chosen)
    return results



def _table_prefer_total_value(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    matcher: Callable[[str], bool],
    *,
    stop_aliases: Sequence[str] = (),
) -> FieldEvidence:
    """Return the explicit TOTAL-row value from a labeled table column.

    If a column contains multiple values and no total row can be identified,
    retain the last value as *ambiguous* instead of pretending a line-item value
    is the document total.  This is important for gross-weight audit evidence.
    """
    spans = find_label_spans(predictions, field_name)
    if not spans:
        return missing_field(field_name, "table header not found")
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    for header in spans:
        groups = _column_value_groups(predictions, header, matcher, stop_aliases=stop_aliases)
        if not groups:
            continue
        total_groups: list[tuple[int, ...]] = []
        for group in groups:
            row_no = index_to_row.get(group[0])
            if row_no is None:
                continue
            row_text = " ".join(predictions[index].text for index in rows[row_no])
            if _has_semantic_alias(row_text, ("total", "grand total")):
                total_groups.append(group)
        chosen = total_groups[-1] if total_groups else groups[-1]
        value = _combine_text(predictions, chosen)
        if total_groups or len(groups) == 1:
            return make_field_evidence(field_name, list(predictions), chosen, value)
        return make_field_evidence(
            field_name,
            list(predictions),
            chosen,
            value,
            status="ambiguous",
            reason="multiple table values found but no explicit total row was recovered",
        )
    return missing_field(field_name, "no compatible value found in the labeled table column")


def _table_evidence(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    header_aliases: Sequence[str] | None,
    matcher: Callable[[str], bool],
    *,
    stop_aliases: Sequence[str] = (),
) -> FieldEvidence:
    spans = find_label_spans(predictions, field_name) if field_name in FIELD_LABEL_ALIASES else []
    if field_name == "goods_description" and not spans:
        generic_headers = {"description", "goods", "commodity", "product", "products", "item", "model"}
        rows = _row_groups(predictions)
        index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
        spans = []
        for index, prediction in enumerate(predictions):
            token = _normalized(prediction.text)
            if token not in generic_headers:
                continue
            row_no = index_to_row.get(index)
            row_text = _normalized(" ".join(predictions[item].text for item in rows[row_no])) if row_no is not None else token
            if token in {"goods", "commodity"} and any(word in row_text for word in ("origin", "country", "type of goods")):
                continue
            if token == "description" and any(word in row_text for word in ("port description", "payment description")):
                continue
            spans.append(LabelSpan(field_name, (index,), prediction.text))
    if header_aliases is not None and not spans:
        spans = [
            LabelSpan(field_name, (index,), prediction.text)
            for index, prediction in enumerate(predictions)
            if _has_alias(prediction.text, header_aliases)
        ]
    if not spans:
        return missing_field(field_name, "table header not found")
    # Prefer the first header in visual order, then its column only.
    for header in spans:
        groups = _column_value_groups(predictions, header, matcher, stop_aliases=stop_aliases)
        if not groups:
            continue
        indices = tuple(index for group in groups for index in group)
        values = [_combine_text(predictions, group) for group in groups]
        return make_field_evidence(field_name, list(predictions), indices, " | ".join(values))
    return missing_field(field_name, "no deterministic value found in the labeled table column")


def _party_value(text: str) -> bool:
    normalized = _normalized(text)
    if not any(character.isalpha() for character in text):
        return False
    if normalized in _CONTROL_WORDS or normalized.endswith(":"):
        return False
    if normalized in {
        "if", "not", "if not", "consignee", "buyer", "seller", "shipper",
        "exporter", "importer", "notify", "notiyy", "notiy", "notification",
    } or (normalized.startswith("noti") and len(normalized) <= 10):
        return False
    if "not consignee" in normalized or "other than consignee" in normalized or "if other than" in normalized or normalized in {"other than", "if other", "same to consignee", "same as consignee"}:
        return False
    # Phone/address captions are common false neighbours in B/L party cells.
    # A bare legal suffix is not enough evidence of a company block either.
    if normalized in {"co", "co ltd", "co limited", "ltd", "limited", "inc", "inc co", "llc", "corp"}:
        return False
    if re.search(r"\b(?:tel|fax|phone|reg|no|negotiable|multimodal|transport)\b|\d{4,}", normalized):
        return False
    return True


def _description_value(text: str) -> bool:
    normalized = _normalized(text).strip(" :")
    if not any(character.isalpha() for character in text):
        return False
    if (
        DATE_PATTERN.search(text)
        or MONEY_PATTERN.fullmatch(text.strip())
        or WEIGHT_PATTERN.search(text.strip())
        or PACKAGE_PATTERN.search(text.strip())
        or any(word in normalized for word in ("cbm", "marks and no", "container", "unit price", "hs code"))
    ):
        return False
    if normalized in _CONTROL_WORDS or UNIT_ONLY_PATTERN.fullmatch(text.strip()):
        return False
    # Alphanumeric model/item codes (e.g. ABC-123) are valid descriptions when
    # they are geometrically anchored to a Description/Item/Model column. The
    # label+column context is stronger evidence than the token shape alone.
    return True


def _identifier_value(text: str) -> bool:
    normalized = _normalized(text)
    return bool(ID_PATTERN.fullmatch(text.strip())) and normalized not in {"and", "date", "no", "number"}


def _quantity_value(text: str) -> bool:
    return bool(QUANTITY_PATTERN.fullmatch(text.strip()))


def _package_value(text: str) -> bool:
    return bool(PACKAGE_PATTERN.fullmatch(text.strip()))


def _weight_value(text: str) -> bool:
    return bool(WEIGHT_PATTERN.fullmatch(text.strip()))


def _money_value(text: str) -> bool:
    return bool(MONEY_PATTERN.fullmatch(text.strip())) and not bool(
        WEIGHT_PATTERN.fullmatch(text.strip()) or PACKAGE_PATTERN.fullmatch(text.strip()) or QUANTITY_PATTERN.fullmatch(text.strip()) and UNIT_ONLY_PATTERN.search(text.strip())
    )


def _explicit_money_token(text: str) -> bool:
    """Return whether a token visibly carries a currency marker."""
    candidate = text.strip()
    return bool(
        _money_value(candidate)
        and (
            re.search(r"[$??Ｂ?]", candidate)
            or CURRENCY_CODE_TOKEN_PATTERN.search(candidate)
        )
    )


def _currency_value(text: str) -> bool:
    candidate = text.strip()
    return bool(
        CURRENCY_CODE_PATTERN.fullmatch(candidate)
        or re.fullmatch(r"[$€£¥]", candidate)
    )


def _first_found(*evidence: FieldEvidence) -> FieldEvidence:
    for candidate in evidence:
        if candidate.status != "missing":
            return candidate
    return evidence[-1]



def _invoice_no_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    embedded = _embedded_candidates(
        "invoice_no", predictions,
        [(0, re.compile(r"(?:invoice|inv)\s*(?:no\.?|number|#)\s*[:#-]?\s*(?!and\b|date\b)(?P<value>[A-Z0-9][A-Z0-9./_-]*)", re.I))],
    )
    if embedded is not None and _identifier_value(embedded.value or ""):
        return embedded

    direct = _ranked_labeled_value(
        "invoice_no", predictions,
        ("invoice number", "invoice no", "invoice #", "inv number", "inv no", "inv #"),
        _identifier_value,
        max_y_ratio=0.60,
    )
    if direct.status != "missing":
        return direct

    compound_aliases = (
        "invoice no and date of invoice", "invoice no and date", "invoice no & date",
        "no and date of invoice", "no & date of invoice", "no date of invoice",
    )
    spans = find_label_spans(predictions, "invoice_no", aliases=compound_aliases)
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    candidates: list[tuple[tuple[int, int], int, str]] = []
    for span in spans:
        anchor_row = min(index_to_row[index] for index in span.indices if index in index_to_row)
        left, _, right, bottom = _span_bounds(predictions, span.indices)
        cell_left, cell_right = _header_column_bounds(predictions, span)
        # Invoice number sits in the left portion of the compound cell.
        search_right = right + max(80, (right - left) * 0.35)
        for row_no in range(anchor_row, min(len(rows), anchor_row + 5)):
            for index in rows[row_no]:
                if index in span.indices:
                    continue
                l, t, _, _ = _bounds(predictions[index])
                if t < bottom - 8 or l < cell_left or l > min(cell_right, search_right):
                    continue
                value = predictions[index].text.strip(" :;,.()[]")
                if DATE_PATTERN.fullmatch(value) or not _identifier_value(value):
                    continue
                candidates.append(((max(0, t - bottom), l), index, value))
        if candidates:
            break
    if not candidates:
        return missing_field("invoice_no", "invoice number label/value not recovered")
    candidates.sort(key=lambda item: item[0])
    _, index, value = candidates[0]
    return make_field_evidence("invoice_no", list(predictions), (index,), value)


def _overlap_ratio(first: OCRPrediction, second: OCRPrediction) -> float:
    l1,t1,r1,b1=_bounds(first); l2,t2,r2,b2=_bounds(second)
    iw=max(0,min(r1,r2)-max(l1,l2)); ih=max(0,min(b1,b2)-max(t1,t2))
    inter=iw*ih
    return inter/max(1,min((r1-l1)*(b1-t1),(r2-l2)*(b2-t2)))


def _dedupe_party_indices(predictions: Sequence[OCRPrediction], indices: Sequence[int]) -> tuple[int, ...]:
    """Remove overlapping tile fragments from a party/company line."""
    kept: list[int] = []
    for index in indices:
        text = _normalized(predictions[index].text)
        if not text:
            continue
        duplicate = False
        for kept_index in kept:
            other = _normalized(predictions[kept_index].text)
            if _overlap_ratio(predictions[index], predictions[kept_index]) >= 0.35:
                if text in other or other in text or SequenceMatcher(None, text, other).ratio() >= 0.72:
                    # Keep the more complete text box.
                    if len(text) > len(other):
                        kept[kept.index(kept_index)] = index
                    duplicate = True
                    break
            if len(text) >= 6 and len(other) >= 6 and (text.endswith(other) or other.endswith(text)):
                duplicate = True
                if len(text) > len(other):
                    kept[kept.index(kept_index)] = index
                break
        if not duplicate:
            kept.append(index)
    return tuple(sorted(kept, key=lambda i: (min(predictions[i].x), min(predictions[i].y), i)))


def _party_block_below_label(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    aliases: Sequence[str],
    *,
    max_y_ratio: float = 0.65,
) -> FieldEvidence:
    """Extract party name from the rectangular cell directly below its label.

    Party fields are not ordinary key/value rows: on trade forms, another static
    label often sits to the right on the same row.  The old generic neighbour
    search therefore returned ``BILL`` or a table caption.  This routine ignores
    same-row candidates and reads the first plausible company-name line below.
    """
    spans = find_label_spans(predictions, field_name, aliases=aliases)
    if not spans:
        return missing_field(field_name, "party label not found")
    spans = sorted(spans, key=lambda span: (_alias_rank(span.text, aliases), min(min(predictions[i].y) for i in span.indices)))
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    page_bottom = max((max(item.y) for item in predictions), default=1)
    candidates: list[tuple[tuple[int,int], tuple[int,...], str]]=[]
    forbidden = (
        "bill of lading", "description of packages", "particulars furnished", "booking no",
        "export references", "forwarding agent", "consignee phone", "shipper phone",
        "freight", "marks and no", "gross weight", "measurement", "notify party",
        "for delivery to", "for delivery of goods", "delivery to", "port and country",
        "other reference", "other references", "l/c", "country of origin", "country of final destination",
        "terms", "date of departure", "departure date", "vessel", "port of loading", "port of discharge",
    )
    for span in spans:
        span_norm=_normalized(span.text)
        if span_norm in {"same to consignee", "same as consignee", "same consignee"} or "same to consignee" in span_norm or "same as consignee" in span_norm:
            continue
        if field_name == "shipper" and ("particulars furnished by shipper" in span_norm or span_norm.startswith("by shipper")):
            continue
        left, top, right, bottom = _span_bounds(predictions, span.indices)
        if top > page_bottom * max_y_ratio:
            continue
        anchor_row=min(index_to_row[i] for i in span.indices if i in index_to_row)
        # Use the label cell width.  If the label is in the left half, cap the
        # region before the nearest header to the right on the same row.
        same_row=rows[anchor_row]
        # Use only *semantic headers* to delimit the party cell. A company-name
        # OCR box itself must never become the right boundary.
        all_aliases=tuple(alias for values in FIELD_LABEL_ALIASES.values() for alias in values)
        boundary_candidates=[]
        for i in same_row:
            if i in span.indices:
                continue
            l,_,_,_=_bounds(predictions[i])
            if l <= right + 20:
                continue
            txt=predictions[i].text
            norm=_normalized(txt)
            if _has_semantic_alias(txt, all_aliases) or any(marker in norm for marker in (
                "booking no", "export references", "forwarding agent", "bill of lading",
                "for delivery to", "third party", "notify party", "point and country", "port and country",
            )):
                boundary_candidates.append(l)
        page_right=max((max(item.x) for item in predictions), default=right+800)
        region_right=min(boundary_candidates)-10 if boundary_candidates else min(page_right, right + max(800,(right-left)*4.0))
        region_left=max(0,left-20)

        # Compact key/value layouts place the company on the same row to the
        # right. Accept it only when it looks like a party value and not another
        # form caption.
        same_candidates=[]
        for i in same_row:
            if i in span.indices:
                continue
            l,_,r,_=_bounds(predictions[i])
            if l < right-5 or l > region_right:
                continue
            txt=predictions[i].text.strip(); norm=_normalized(txt)
            if not txt or any(x in norm for x in forbidden):
                continue
            if _party_value(txt):
                same_candidates.append(i)
        if same_candidates:
            same_candidates=list(_dedupe_party_indices(predictions,same_candidates))
            value=_combine_text(predictions,same_candidates)
            if _party_value(value) and _normalized(value) not in {"bill","bill o","description of packages and goods","description of package and goods"}:
                candidates.append(((0,min(_bounds(predictions[i])[0] for i in same_candidates)),tuple(same_candidates),value))
                continue

        for row_no in range(anchor_row+1,min(len(rows),anchor_row+7)):
            row=rows[row_no]
            row_top=min(min(predictions[i].y) for i in row)
            if row_top-bottom>280: break
            row_indices=[]
            for i in row:
                l,_,r,_=_bounds(predictions[i]); c=(l+r)/2
                if region_left<=c<=region_right:
                    txt=predictions[i].text.strip(); norm=_normalized(txt)
                    if not txt or any(x in norm for x in forbidden): continue
                    if re.search(r"\b(?:tel|fax|phone|zip|code)\b",norm): continue
                    if _party_value(txt): row_indices.append(i)
            if not row_indices: continue
            row_indices=list(_dedupe_party_indices(predictions,row_indices))
            value=_combine_text(predictions,row_indices)
            if not _party_value(value): continue
            # Reject tiny form-caption remnants such as BILL/BILL O.
            norm=_normalized(value)
            if norm in {"bill","bill o","description of packages and goods","description of package and goods"}:
                continue
            alpha=sum(ch.isalpha() for ch in value)
            if alpha<4: continue
            candidates.append(((row_top-bottom,min(_bounds(predictions[i])[0] for i in row_indices)),tuple(row_indices),value))
            break
    if not candidates:
        return missing_field(field_name,"party company-name line not recovered below semantic label")
    candidates.sort(key=lambda item:item[0])
    _,indices,value=candidates[0]
    return make_field_evidence(field_name,list(predictions),indices,value)


def _embedded_total_package(predictions: Sequence[OCRPrediction]) -> FieldEvidence | None:
    """Recover an explicit shipment-level package total only.

    Line-item package counts are deliberately not promoted to a document total.
    """
    rows=_row_groups(predictions)
    found: list[tuple[int, tuple[int,...], str]]=[]
    unit_re=r"(?:PKGS?|CTNS?|BOX(?:ES)?|BAGS?|BUNDLES?|CARTONS?|CASES?|PALLETS?)"
    direct_patterns=[
        re.compile(rf"total\s+(?:ctns?|cartons?|packages?|pkgs?)\s*[:#=-]?\s*(?P<num>\d[\d,.]*)(?:\s*(?P<unit>{unit_re}))?",re.I),
        re.compile(rf"say\s*[:#=-]?\s*(?P<num>\d[\d,.]*)\s*(?P<unit>{unit_re})",re.I),
    ]
    for i,pred in enumerate(predictions):
        for pat in direct_patterns:
            m=pat.search(pred.text)
            if not m: continue
            num=m.group('num'); unit=m.groupdict().get('unit')
            norm=_normalized(pred.text)
            if not unit:
                if 'ctn' in norm or 'carton' in norm: unit='CTN'
                elif 'pkg' in norm or 'package' in norm: unit='PKG'
            if unit:
                found.append((-max(pred.y),(i,),f"{num} {unit}"))

    # Labels such as ``TOTAL NUMBER OF PKGS.`` often have ``22`` + ``PKG``
    # as separate OCR boxes on the same row.
    for row in rows:
        row_text=' '.join(predictions[i].text for i in row)
        norm=_normalized(row_text)
        if not any(marker in norm for marker in ('total number of pkgs','total number of packages','total number of containers or packages')):
            continue
        others=[i for i in row if 'total' not in _normalized(predictions[i].text) and 'number' not in _normalized(predictions[i].text)]
        # Try every short contiguous combination so split ``22`` + ``PKG`` works.
        others=sorted(others,key=lambda i:min(predictions[i].x))
        for pos in range(len(others)):
            for size in range(1,min(4,len(others)-pos)+1):
                group=tuple(others[pos:pos+size])
                text=_combine_text(predictions,group)
                m=re.search(rf"(?P<num>\d[\d,.]*)\s*(?P<unit>{unit_re})\b",text,re.I)
                if m:
                    found.append((-max(max(predictions[j].y) for j in group),group,f"{m.group('num')} {m.group('unit')}") )
        # Also inspect the next three visual rows for in-words totals such as
        # ``56 BUNDLES ONLY ...``.
        row_no=rows.index(row)
        for nr in range(row_no+1,min(len(rows),row_no+4)):
            for i in rows[nr]:
                m=re.search(rf"(?P<num>\d[\d,.]*)\s*(?P<unit>{unit_re})\b",predictions[i].text,re.I)
                if m:
                    found.append((-max(predictions[i].y),(i,),f"{m.group('num')} {m.group('unit')}") )
                    break
    if not found:
        return None
    found.sort(key=lambda item:item[0])
    _,indices,value=found[0]
    return make_field_evidence('number_of_packages',list(predictions),indices,value)


def _embedded_total_gross_weight(predictions: Sequence[OCRPrediction]) -> FieldEvidence | None:
    """Recover explicit document-level gross weight, including table TOTAL rows."""
    rows=_row_groups(predictions)
    found: list[tuple[int, tuple[int,...], str]]=[]
    # One-box labels such as TOTAL GROSS WEIGHT : 53 KG.
    pat=re.compile(r"total\s+gross\s+weight\s*[:#=-]?\s*(?P<num>[0-9OoIl][0-9OoIl,.:]*)\s*(?P<unit>KG|KGS|LB|LBS)",re.I)
    for i,pred in enumerate(predictions):
        m=pat.search(pred.text)
        if not m: continue
        raw=m.group('num').translate(str.maketrans({'O':'0','o':'0','I':'1','l':'1'})).rstrip('.,:')
        value=f"{raw}{m.group('unit')}"
        if _weight_value(value):
            found.append((-max(pred.y),(i,),value))
    if found:
        found.sort(key=lambda item:item[0]); _,indices,value=found[0]
        return make_field_evidence('gross_weight',list(predictions),indices,value)

    # Infer the gross-weight column center from a complete or vertically split
    # header (GROSS / WEIGHT*).
    centers=[]
    for i,pred in enumerate(predictions):
        norm=_normalized(pred.text)
        l,t,r,b=_bounds(pred)
        if 'gross weight' in norm or norm in {'gross wt','gross wgt','g wt','g wgt'}:
            centers.append(((l+r)/2,b))
        elif norm in {'gross','gros'}:
            for j,other in enumerate(predictions):
                if j==i: continue
                onorm=_normalized(other.text); ol,ot,or_,ob=_bounds(other)
                if onorm.startswith('weight') and -15 <= ot-b <= 90 and max(0,min(r,or_)-max(l,ol)) > 0:
                    centers.append((((l+r+ol+or_)/4),ob))
    # Continue to the structural TOTAL-row fallback when the header itself
    # was missed by OCR.
    # Search explicit TOTAL rows below the header. The nearest weight-shaped
    # value to the gross column is the shipment total.
    for center,header_bottom in centers:
        for row in rows:
            row_top=min(min(predictions[i].y) for i in row)
            if row_top <= header_bottom: continue
            row_text=' '.join(predictions[i].text for i in row)
            if not _has_semantic_alias(row_text,('total','grand total')): continue
            candidates=[]
            for i in row:
                txt=predictions[i].text.strip()
                if _weight_value(txt):
                    c=(min(predictions[i].x)+max(predictions[i].x))/2
                    candidates.append((abs(c-center),i,txt))
            if candidates:
                candidates.sort(); _,i,value=candidates[0]
                return make_field_evidence('gross_weight',list(predictions),(i,),value)
    # Some B/L templates omit the gross-weight header from OCR but retain a
    # clear shipment table signature: package/unit and CBM columns plus one
    # unambiguous weight in the TOTAL row. Use only that structural evidence;
    # never promote an arbitrary standalone weight to a shipment total.
    has_volume_column = any(_normalized(item.text) == "cbm" for item in predictions)
    package_token_count = sum(
        1 for item in predictions
        if _normalized(item.text) in {"pkg", "pkgs", "ctn", "ctns", "carton", "cartons"}
    )
    has_package_column = package_token_count >= 2
    if has_volume_column:
        has_package_column = package_token_count >= 1
    has_package_column = has_package_column or any(
        _normalized(item.text) in {"pkg", "pkgs", "ctn", "ctns", "carton", "cartons"}
        for item in predictions
    )
    if has_volume_column and has_package_column:
        for row in rows:
            row_text = " ".join(predictions[index].text for index in row)
            if not _has_semantic_alias(row_text, ("total", "grand total")):
                continue
            weights = [
                (index, predictions[index].text)
                for index in row
                if _weight_value(predictions[index].text)
            ]
            if len(weights) == 1:
                index, value = weights[0]
                return make_field_evidence("gross_weight", list(predictions), (index,), value)
    return None


def _shipment_date_value(predictions: Sequence[OCRPrediction]) -> FieldEvidence:
    """Extract explicit shipped/on-board date without using generic dates."""
    # Same-box forms first.
    embedded=_embedded_candidates(
        'on_board_date',predictions,
        [(0,re.compile(r"(?:laden\s+on\s+board|shipped\s+on\s+board|on\s+board\s+date|date\s+shipped|date\s+of\s+shipment)\s*[:#-]?\s*(?P<value>"+DATE_PATTERN.pattern+r")",re.I))],
    )
    if embedded is not None:
        return embedded
    aliases=('laden on board date','laden on board','shipped on board date','shipped on board','on board date','date shipped','date of shipment')
    spans=find_label_spans(predictions,'on_board_date',aliases=aliases)
    rows=_row_groups(predictions); idxrow={i:r for r,row in enumerate(rows) for i in row}
    candidates=[]
    for span in spans:
        row_no=min(idxrow[i] for i in span.indices if i in idxrow)
        l,_,r,b=_span_bounds(predictions,span.indices); center=(l+r)/2
        # Compact forms put the date on the same row to the right.
        for i in rows[row_no]:
            if i in span.indices:
                continue
            il,it,ir,_=_bounds(predictions[i])
            if il < r - 5:
                continue
            value=_date_candidate(predictions[i].text)
            if value:
                candidates.append(((0,max(0,il-r)),i,value))
        for nr in range(row_no+1,min(len(rows),row_no+4)):
            for i in rows[nr]:
                if i in span.indices: continue
                il,it,ir,_=_bounds(predictions[i]); ic=(il+ir)/2
                if it < b-8 or abs(ic-center)>max(240,(r-l)*2.5): continue
                value=_date_candidate(predictions[i].text)
                if value:
                    candidates.append(((max(0,it-b),abs(ic-center)),i,value))
    if not candidates:
        # Paddle can split DATE SHIPPED into duplicate boxes that defeat label
        # span grouping. Fall back to a direct semantic-label scan, still never
        # using a generic date.
        for label_index,label in enumerate(predictions):
            norm=_normalized(label.text)
            if not any(marker in norm for marker in ('date shipped','shipped on board','laden on board','on board date','date of shipment')):
                continue
            ll,lt,lr,lb=_bounds(label); lc=(ll+lr)/2
            for i,item in enumerate(predictions):
                if i==label_index: continue
                il,it,ir,_=_bounds(item); ic=(il+ir)/2
                if it < lt-10 or it > lb+180 or abs(ic-lc)>350:
                    continue
                value=_date_candidate(item.text)
                if value:
                    candidates.append(((max(0,it-lb),abs(ic-lc)),i,value))
        if not candidates:
            return missing_field('on_board_date','explicit shipped/on-board date not recovered')
    candidates.sort(key=lambda x:x[0]); _,i,value=candidates[0]
    return make_field_evidence('on_board_date',list(predictions),(i,),value)


def _invoice_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    buyer = _semantic_party_guard("buyer", _invoice_buyer_value(predictions))
    seller = _invoice_seller_value(predictions)

    invoice_no = _invoice_no_value(predictions)

    date = _invoice_date_value(predictions)
    amount = _invoice_amount_value(predictions)

    fields = {
        "invoice_no": invoice_no,
        "date": date,
        "buyer": buyer,
        "seller": seller,
        "amount": amount,
        "currency": None,
    }
    fields["goods_description"] = _table_evidence(
        "goods_description", predictions, None, _description_value,
        stop_aliases=("total", "remark", "signature", "signed by"),
    )
    fields["quantity"] = _table_evidence(
        "quantity", predictions, None, _quantity_value,
        stop_aliases=("total", "grand total", "subtotal"),
    )

    explicit_currency = _labeled_value("currency", predictions, None, _currency_value)
    if explicit_currency.status != "missing":
        if re.fullmatch(r"[$€£¥]", explicit_currency.value or ""):
            explicit_currency = make_field_evidence(
                "currency", list(predictions), explicit_currency.source_indices,
                explicit_currency.value, status="ambiguous",
                reason="currency symbol found but ISO code absent",
            )
        fields["currency"] = explicit_currency
        return fields

    # Without a Currency label, derive currency only from the extracted amount
    # first. This prevents a random currency token elsewhere in the document
    # from overriding the amount's own evidence.
    amount_indices = fields["amount"].source_indices
    for index in amount_indices:
        code_match = CURRENCY_CODE_TOKEN_PATTERN.search(predictions[index].text)
        if code_match:
            fields["currency"] = make_field_evidence(
                "currency", list(predictions), (index,), code_match.group(1).upper()
            )
            return fields
    for index in amount_indices:
        symbol_match = re.search(r"[$€£¥]", predictions[index].text)
        if symbol_match:
            fields["currency"] = make_field_evidence(
                "currency", list(predictions), (index,), symbol_match.group(),
                status="ambiguous", reason="currency symbol found but ISO code absent",
            )
            return fields

    # An ISO code is self-describing even when embedded in another OCR box
    # (e.g. ``USD 5000``), so keep it as derived evidence. Symbols are not
    # self-identifying enough to do this globally.
    for index, prediction in enumerate(predictions):
        code_match = CURRENCY_CODE_TOKEN_PATTERN.search(prediction.text)
        if code_match:
            fields["currency"] = make_field_evidence(
                "currency", list(predictions), (index,), code_match.group(1).upper()
            )
            return fields
    fields["currency"] = missing_field("currency", "currency code or symbol not found")
    return fields


def _packing_list_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    invoice_no = _invoice_no_value(predictions)

    package_total = _embedded_total_package(predictions)
    if package_total is None:
        package_total = _line_embedded(
            "number_of_packages", predictions,
            [re.compile(
                r"(?:total\s+)?(?:number\s+of\s+)?(?:packages?|pkgs?|ctns?|cartons?)"
                r"\s*[:#=-]?\s*(?P<value>\d[\d,.]*\s*(?:PKGS?|CTNS?|BOX(?:ES)?|"
                r"BAGS?|BUNDLES?|CARTONS?|CASES?|PALLETS?))", re.I,
            )],
            _package_value,
        )
    if package_total is None:
        package_total = _embedded(
            "number_of_packages", predictions,
            [re.compile(r"(?:number|no\.?)\s+of\s+packages?\s*[:#-]?\s*(?P<value>\d[\d,.]*\s*(?:PKGS?|CTNS?|BOX(?:ES)?|BAGS?|BUNDLES?|CARTONS?|CASES?|PALLETS?))", re.I)],
        ) or _labeled_value("number_of_packages", predictions, None, _package_value)

    if package_total.status == "found" and _embedded_total_package(predictions) is None:
        spans = find_label_spans(predictions, "number_of_packages")
        if spans:
            groups = _column_value_groups(predictions, spans[0], _package_value, stop_aliases=("signed by", "remark"))
            if len(groups) > 1:
                indices = tuple(index for group in groups for index in group)
                values = [_combine_text(predictions, group) for group in groups]
                package_total = make_field_evidence(
                    "number_of_packages", list(predictions), indices, " | ".join(values),
                    status="ambiguous", reason="multiple line-item package counts and no explicit packing-list total",
                )

    gross_weight = _embedded(
        "gross_weight", predictions,
        [re.compile(r"(?:total\s+)?gross\s*(?:weight|wt\.?|wgt\.?)\s*[:#-]?\s*(?P<value>\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS))", re.I)],
    )
    if gross_weight is None:
        gross_weight = _line_embedded(
            "gross_weight", predictions,
            [re.compile(
                r"(?:total\s+)?gross\s*(?:weight|wt\.?|wgt\.?)\s*[:#=-]?\s*"
                r"(?P<value>\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS))", re.I,
            )],
            _weight_value,
        )
    if gross_weight is None:
        gross_weight = _ranked_labeled_value(
            "gross_weight",
            predictions,
            ("total gross weight", "gross weight", "gross wt", "gross wgt", "g wt", "g wgt"),
            _weight_value,
            prefer_bottom=True,
        )
    explicit_total_weight = _embedded_total_gross_weight(predictions)
    if explicit_total_weight is not None:
        gross_weight = explicit_total_weight
    elif gross_weight.status == "missing":
        gross_weight = _table_prefer_total_value(
            "gross_weight", predictions, _weight_value,
            stop_aliases=("signed by", "remark"),
        )

    return {
        "invoice_no": invoice_no,
        "goods_description": _table_evidence(
            "goods_description", predictions, None, _description_value,
            stop_aliases=("signed by", "total", "remark"),
        ),
        "quantity": _table_evidence(
            "quantity", predictions, None, _quantity_value,
            stop_aliases=("signed by", "total", "grand total"),
        ),
        "number_of_packages": package_total,
        "gross_weight": gross_weight,
    }


def _bill_of_lading_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    bl_no = _embedded(
        "bl_no", predictions,
        [re.compile(r"(?:b\s*/\s*l|bl|bill\s+of\s+lading)\s*(?:no\.?|number|#)\s*[:#-]?\s*(?P<value>[A-Z0-9][A-Z0-9./_-]*)", re.I)],
    ) or _labeled_value("bl_no", predictions, None, _identifier_value)
    if bl_no.status == "missing":
        bl_no = _line_embedded(
            "bl_no", predictions,
            [re.compile(
                r"(?:b\s*/\s*l|bl|bill\s+of\s+lading)\s*(?:no\.?|number|#)\s*"
                r"[:#-]?\s*(?P<value>[A-Z0-9][A-Z0-9./_-]*)", re.I,
            )],
            _identifier_value,
        ) or bl_no

    package_total = _embedded_total_package(predictions)
    if package_total is None:
        package_total = _line_embedded(
            "number_of_packages", predictions,
            [re.compile(
                r"(?:total\s+)?(?:number\s+of\s+)?(?:packages?|pkgs?|ctns?|cartons?)"
                r"\s*[:#=-]?\s*(?P<value>\d[\d,.]*\s*(?:PKGS?|CTNS?|BOX(?:ES)?|"
                r"BAGS?|BUNDLES?|CARTONS?|CASES?|PALLETS?))", re.I,
            )],
            _package_value,
        )
    if package_total is None:
        package_total = _labeled_value("number_of_packages", predictions, None, _package_value)
        # Multiple line-item package counts without an explicit total are not a
        # shipment-level package total.  Keep them reviewable rather than false.
        if package_total.status == "found":
            spans = find_label_spans(predictions, "number_of_packages")
            if spans:
                groups = _column_value_groups(predictions, spans[0], _package_value)
                if len(groups) > 1:
                    package_total = make_field_evidence(
                        "number_of_packages", list(predictions), package_total.source_indices, package_total.value,
                        status="ambiguous", reason="multiple package rows and no explicit shipment total",
                    )

    shipper_aliases = ("shipper/exporter complete name address", "shipper exporter complete name address", "consignor/shipper", "consignor shipper", "shipper/exporter", "shipper exporter", "shipper", "consignor", "exporter")
    consignee_aliases = ("consignee not negotiable unless consigned to order", "consignee please provide complete name and address", "consignee provide complete name and address", "consignee complete name address", "consignee",)
    shipper = _semantic_party_guard("shipper", _party_block_below_label("shipper", predictions, shipper_aliases, max_y_ratio=0.55))
    consignee = _semantic_party_guard("consignee", _party_block_below_label("consignee", predictions, consignee_aliases, max_y_ratio=0.62))

    gross_weight = _ranked_labeled_value(
        "gross_weight", predictions,
        ("total gross weight", "gross weight", "gross wt", "gross wgt", "g weight", "g wt", "g wgt"),
        _weight_value,
        prefer_bottom=True,
    )
    if gross_weight.status == "missing":
        gross_weight = _line_embedded(
            "gross_weight", predictions,
            [re.compile(
                r"(?:total\s+)?gross\s*(?:weight|wt\.?|wgt\.?)\s*[:#=-]?\s*"
                r"(?P<value>\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS))", re.I,
            )],
            _weight_value,
        ) or gross_weight
    explicit_total_weight = _embedded_total_gross_weight(predictions)
    table_weight = _table_prefer_total_value(
        "gross_weight", predictions, _weight_value,
        stop_aliases=("freight", "liability information", "signed by"),
    )
    if explicit_total_weight is not None:
        gross_weight = explicit_total_weight
    elif table_weight.status == "ambiguous":
        gross_weight = table_weight
    elif gross_weight.status == "missing" or (
        gross_weight.status == "found" and table_weight.status == "found"
        and min(table_weight.source_indices or (10**9,)) > min(gross_weight.source_indices or (10**9,))
    ):
        gross_weight = table_weight

    on_board_date = _shipment_date_value(predictions)

    return {
        "bl_no": bl_no,
        "shipper": shipper,
        "consignee": consignee,
        "goods_description": _table_evidence(
            "goods_description", predictions, None, _description_value,
            stop_aliases=("total", "freight", "signed by"),
        ),
        "number_of_packages": package_total,
        "gross_weight": gross_weight,
        "on_board_date": on_board_date,
    }


def extract_fields(form_type: str, predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    """Extract the current Fintra MVP fields for one target form type."""
    if form_type == "상업송장":
        return _invoice_fields(predictions)
    if form_type == "포장명세서":
        return _packing_list_fields(predictions)
    if form_type == "선하증권":
        return _bill_of_lading_fields(predictions)
    raise ValueError(f"Unsupported Fintra form type: {form_type!r}")
