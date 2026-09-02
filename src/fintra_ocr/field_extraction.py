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
from functools import lru_cache

from .field_evidence import FieldEvidence, missing_field, make_field_evidence
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
        "invoice no", "invoice number", "invoice #", "invoice nr",
        "inv no", "inv number", "inv #", "inv nr",
    ),
    "date": ("invoice date", "inv date", "date", "dated"),
    "buyer": ("buyer", "sold to", "bill to", "buyer consignee", "purchaser", "customer"),
    "goods_description": (
        "description of goods", "description of good", "goods description", "description",
        "description of commodity", "commodity description", "description of articles",
        "description of merchandise", "goods", "commodity", "products", "product", "item", "model",
    ),
    "quantity": ("quantity", "qty", "q'ty", "q ty", "qnty", "order qty"),
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
        "number and kind of packages", "no & kinds", "pkgs",
    ),
    "gross_weight": (
        "total gross weight", "gross weight", "gross wt", "gross wgt", "grossweight",
        "gross mass", "g weight", "gross/w", "g w", "g wt", "g wgt", "g/w", "g/wt", "g/wgt", "gw", "gwt",
    ),
    "bl_no": (
        "b/l no", "b/l number", "b/l #", "bl no", "bl number", "bl #",
        "bill of lading no", "bill of lading number",
    ),
    "shipper": ("consignor/shipper", "consignor shipper", "shipper/exporter", "shipper exporter", "shipper", "consignor", "exporter"),
    "consignee": ("consignee",),
    "on_board_date": (
        "laden on board", "laden on board date", "shipped on board", "shipped on board date",
        "on board date", "onboard date", "date on board", "date shipped", "shipped date",
        "date of shipment", "on board",
    ),
}

_CONTROL_WORDS = {
    "amount", "carrier", "cbm", "collect", "container", "containers", "currency",
    "date", "delivery", "description", "destination", "discharge", "freight", "gross",
    "hs", "invoice", "issue", "loading", "marks", "measurement", "net", "number",
    "on", "origin", "packages", "package", "party", "payment", "place", "port", "price",
    "quantity", "receipt", "remark", "seal", "shipping", "signature", "signed", "total",
    "unit", "vessel", "voy", "weight", "buyer", "shipper", "consignee",
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
    return overlap / min(first_h, second_h) >= 0.25 or abs(
        (first_top + first_bottom) - (second_top + second_bottom)
    ) <= max(20, min(first_h, second_h))


_ROW_GROUP_CACHE_SOURCE: Sequence[OCRPrediction] | None = None
_ROW_GROUP_CACHE_RESULT: list[list[int]] | None = None


def _row_groups(predictions: Sequence[OCRPrediction]) -> list[list[int]]:
    global _ROW_GROUP_CACHE_SOURCE, _ROW_GROUP_CACHE_RESULT
    if predictions is _ROW_GROUP_CACHE_SOURCE and _ROW_GROUP_CACHE_RESULT is not None:
        return _ROW_GROUP_CACHE_RESULT
    ordered = sorted(range(len(predictions)), key=lambda index: (min(predictions[index].y), min(predictions[index].x), index))
    groups: list[list[int]] = []
    for index in ordered:
        placed = False
        for group in reversed(groups[-3:]):
            if any(_same_row(predictions[index], predictions[other]) for other in group):
                group.append(index)
                placed = True
                break
        if not placed:
            groups.append([index])
    for group in groups:
        group.sort(key=lambda index: (min(predictions[index].x), index))
    groups.sort(key=lambda group: min(min(predictions[index].y) for index in group))
    _ROW_GROUP_CACHE_SOURCE = predictions
    _ROW_GROUP_CACHE_RESULT = groups
    return groups


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


def _find_label_spans_uncached(
    predictions: Sequence[OCRPrediction], field_name: str, *, max_span: int = 4
) -> list[LabelSpan]:
    """Find visible semantic labels, including labels split across OCR boxes.

    The function deliberately does not infer labels from units or value formats.
    """
    aliases = FIELD_LABEL_ALIASES[field_name]
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
                if _has_alias(text, aliases):
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
                if _equals_alias(text, aliases) and indices not in seen:
                    matches.append(LabelSpan(field_name, indices, text))
                    seen.add(indices)
    return sorted(matches, key=lambda span: (min(min(predictions[index].y) for index in span.indices), min(min(predictions[index].x) for index in span.indices)))


_LABEL_SPAN_CACHE_SOURCE: Sequence[OCRPrediction] | None = None
_LABEL_SPAN_CACHE: dict[tuple[str, int], list[LabelSpan]] = {}


def find_label_spans(
    predictions: Sequence[OCRPrediction], field_name: str, *, max_span: int = 4
) -> list[LabelSpan]:
    """Find label spans once per prediction sequence and field."""
    global _LABEL_SPAN_CACHE_SOURCE, _LABEL_SPAN_CACHE
    if predictions is not _LABEL_SPAN_CACHE_SOURCE:
        _LABEL_SPAN_CACHE_SOURCE = predictions
        _LABEL_SPAN_CACHE = {}
    key = (field_name, max_span)
    if key not in _LABEL_SPAN_CACHE:
        _LABEL_SPAN_CACHE[key] = _find_label_spans_uncached(
            predictions, field_name, max_span=max_span
        )
    return _LABEL_SPAN_CACHE[key]


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


def _candidate_groups_near_span(
    predictions: Sequence[OCRPrediction], span: LabelSpan, *, max_group: int = 3
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
            if _call_matcher(value_pattern, text):
                matches.append((score, group, text))
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


def _table_evidence(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    header_aliases: Sequence[str] | None,
    matcher: Callable[[str], bool],
    *,
    stop_aliases: Sequence[str] = (),
) -> FieldEvidence:
    spans = find_label_spans(predictions, field_name) if field_name in FIELD_LABEL_ALIASES else []
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
    if re.search(r"\b(?:tel|fax|reg|no|negotiable|multimodal|transport)\b|\d{4,}", normalized):
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


def _invoice_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    buyer = _embedded(
        "buyer", predictions,
        [re.compile(r"(?:buyer|sold\s+to|bill\s+to)\s*[:#-]\s*(?P<value>.+)", re.I)],
    ) or _labeled_value("buyer", predictions, None, _party_value)
    if buyer.status == "found" and _normalized(buyer.value or "") in {"same to consignee", "same as consignee"}:
        buyer = make_field_evidence(
            "buyer", list(predictions), buyer.source_indices, buyer.value,
            status="ambiguous", reason="buyer is expressed as a consignee reference",
        )

    invoice_no = _embedded(
        "invoice_no", predictions,
        [
            re.compile(r"(?:invoice|inv)\s*(?:no\.?|number|#)\s*[:#-]?\s*(?!and\b|date\b)(?P<value>[A-Z0-9][A-Z0-9./_-]*)", re.I),
        ],
    ) or _labeled_value("invoice_no", predictions, None, _identifier_value)

    date = _embedded(
        "date", predictions,
        [re.compile(r"(?:invoice\s+date|date|dated)\s*[:#-]?\s*(?P<value>" + DATE_PATTERN.pattern + r")", re.I)],
    ) or _labeled_value("date", predictions, None, DATE_PATTERN)

    amount = _embedded(
        "amount", predictions,
        [
            re.compile(r"(?:total\s+amount|invoice\s+amount|invoice\s+total|grand\s+total|total\s+value|invoice\s+value|amount|total)\s*[:#-]?\s*(?P<value>(?:(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)\s*|[$€£¥]\s*)?[+-]?\d[\d,]*(?:\.\d+)?(?:\s*(?:USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD))?)", re.I)
        ],
    ) or _labeled_value("amount", predictions, None, _money_value)

    fields = {
        "invoice_no": invoice_no,
        "date": date,
        "buyer": buyer,
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
    invoice_no = _embedded(
        "invoice_no", predictions,
        [re.compile(r"(?:invoice|inv)\s*(?:no\.?|number|#)\s*[:#-]?\s*(?P<value>[A-Z0-9][A-Z0-9./_-]*)", re.I)],
    ) or _labeled_value("invoice_no", predictions, None, _identifier_value)

    package_total = _embedded(
        "number_of_packages", predictions,
        [
            re.compile(r"(?:number|no\.?)\s+of\s+packages?\s*[:#-]?\s*(?P<value>\d[\d,.]*\s*(?:PKGS?|CTNS?|BOX(?:ES)?|BAGS?|BUNDLES?|CARTONS?|CASES?|PALLETS?))", re.I),
        ],
    ) or _labeled_value("number_of_packages", predictions, None, _package_value)

    gross_weight = _embedded(
        "gross_weight", predictions,
        [re.compile(r"(?:total\s+)?gross\s*(?:weight|wt\.?|wgt\.?)\s*[:#-]?\s*(?P<value>\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS))", re.I)],
    ) or _labeled_value("gross_weight", predictions, None, _weight_value)

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

    package_total = _embedded(
        "number_of_packages", predictions,
        [re.compile(r"say\s*:\s*(?P<value>\d[\d,.]*\s*(?:PKGS?|CTNS?|BOX(?:ES)?|BAGS?|BUNDLES?|CARTONS?|CASES?|PALLETS?))", re.I)],
    ) or _labeled_value("number_of_packages", predictions, None, _package_value)

    return {
        "bl_no": bl_no,
        "shipper": _labeled_value("shipper", predictions, None, _party_value),
        "consignee": _labeled_value("consignee", predictions, None, _party_value),
        "goods_description": _table_evidence(
            "goods_description", predictions, None, _description_value,
            stop_aliases=("total", "freight", "signed by"),
        ),
        "number_of_packages": package_total,
        "gross_weight": _labeled_value("gross_weight", predictions, None, _weight_value),
        "on_board_date": _embedded(
            "on_board_date", predictions,
            [re.compile(r"(?:laden\s+on\s+board|shipped\s+on\s+board|on\s+board\s+date|date\s+shipped)\s*[:#-]?\s*(?P<value>" + DATE_PATTERN.pattern + r")", re.I)],
        ) or _labeled_value("on_board_date", predictions, None, DATE_PATTERN),
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
