"""Streaming analysis of target-document ground-truth labels."""

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any
from zipfile import BadZipFile, ZipFile

from .common_schema import document_type_from_form_type
from .target_selection import TargetArchivePair


DOCUMENT_TYPES = (
    "commercial_invoice",
    "packing_list",
    "bill_of_lading",
)

FIELD_SPECS: dict[str, tuple[str, ...]] = {
    "invoice_no": ("invoice", "inv no", "inv number"),
    "date": ("date", "dated", "on board", "laden on board", "shipped"),
    "on_board_date": ("date", "dated", "on board", "laden on board", "shipped"),
    "buyer_consignee": ("buyer", "sold to", "bill to", "seller"),
    "shipper": ("shipper", "consignor", "exporter"),
    "consignee": ("consignee",),
    "goods_description": ("description", "goods", "products", "product", "commodity", "item", "model"),
    "quantity": ("quantity", "qty", "q'ty", "unit", "units", "piece", "pieces", "pcs"),
    "amount_total": ("amount", "total", "subtotal", "grand", "value", "price"),
    "currency": ("currency", "usd", "cad", "eur", "gbp", "jpy", "cny", "krw"),
    "number_of_packages": ("number of packages", "packages", "package", "pkg", "pkgs", "no & kinds", "bundles"),
    "gross_weight": ("gross weight", "gross", "weight", "g.w", "g.wt", "g.weight", "measurement"),
    "bl_no": ("b/l", "b/l no", "bl no", "bill of lading"),
}

FIELD_KEYS_BY_DOCUMENT: dict[str, tuple[str, ...]] = {
    "commercial_invoice": ("invoice_no", "date", "buyer_consignee", "goods_description", "quantity", "amount_total", "currency"),
    "packing_list": ("invoice_no", "goods_description", "quantity", "number_of_packages", "gross_weight"),
    "bill_of_lading": ("bl_no", "shipper", "consignee", "goods_description", "number_of_packages", "gross_weight", "on_board_date"),
}

_DATE_PATTERNS = (
    ("iso", re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")),
    ("day_month_name_year", re.compile(r"^\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[- ]\d{2,4}$", re.I)),
    ("month_name_day_year", re.compile(r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}$", re.I)),
    ("numeric_day_month_year", re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")),
)
_MONEY_PATTERN = re.compile(r"^(?:[$€£¥]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*[A-Z]{3})?$", re.I)
_MONEY_TOKEN_PATTERN = re.compile(r"(?:[$€£¥]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*(?:USD|CAD|EUR|GBP|JPY|CNY|KRW|HKD|AUD|SGD))?", re.I)
_MEASURE_TOKEN_PATTERN = re.compile(
    r"[+-]?\d[\d,]*(?:\.\d+)?\s*(KG|KGS|LB|LBS|PKG|PKGS|PCS?|CTN|CTNS?|BUNDLES?|BOX(?:ES)?|CARTONS?|CASES?|PALLETS?|ST|CT)",
    re.I,
)
_CURRENCY_CODE_PATTERN = re.compile(r"\b(?:USD|CAD|EUR|GBP|JPY|CNY|KRW|HKD|AUD|SGD)\b", re.I)
_NUMBER_PATTERN = re.compile(r"^[+-]?\d[\d,]*(?:\.\d+)?$")
_MEASURE_PATTERN = re.compile(
    r"^[+-]?\d[\d,]*(?:\.\d+)?\s*(KG|KGS|LB|LBS|PKG|PKGS|PCS?|CTN|CTNS?|BUNDLES?|BOX(?:ES)?|CARTONS?|CASES?|PALLETS?|ST|CT)$",
    re.I,
)
_UNIT_ONLY_PATTERN = re.compile(
    r"^(KG|KGS|LB|LBS|PKG|PKGS|PCS?|CTN|CTNS?|BUNDLES?|BOX(?:ES)?|CARTONS?|CASES?|PALLETS?|ST|CT)$",
    re.I,
)
_ID_PATTERN = re.compile(r"^(?=.*\d)[A-Z0-9][A-Z0-9./-]{3,}$", re.I)
_TOTAL_PATTERN = re.compile(r"\b(?:total|subtotal|grand|say)\b", re.I)


@dataclass(frozen=True)
class TargetLabelRecord:
    split: str
    document_type: str
    archive_name: str
    member_name: str
    record: Mapping[str, Any]


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _normalized_expression(text: str) -> str:
    return re.sub(r"[^a-z0-9'/.& #]+", " ", _clean_text(text).lower()).strip()


def _field_hits(text: str) -> set[str]:
    """Return semantic label anchors only, never format-derived field hits."""
    normalized = _normalized_expression(text)
    if not normalized or _number(text) or _MEASURE_PATTERN.fullmatch(normalized) or _unit_only(text):
        return set()

    hits: set[str] = set()
    if re.search(r"\b(?:invoice|inv)\s*(?:no|number|#)\b", normalized):
        hits.add("invoice_no")
    if re.search(r"\b(?:date|dated)\b", normalized):
        hits.update({"date", "on_board_date"})
    if re.search(r"\b(?:on board|laden on board|shipped)\b", normalized):
        hits.update({"date", "on_board_date"})
    if re.search(r"\b(?:buyer|sold to|bill to|seller)\b", normalized):
        hits.add("buyer_consignee")
    if re.search(r"\b(?:shipper|consignor|exporter)\b", normalized):
        hits.add("shipper")
    if re.search(r"\bconsignee\b", normalized):
        hits.add("consignee")
    if re.search(r"\b(?:description|goods|products?|commodity|item|model)\b", normalized):
        hits.add("goods_description")
    if re.search(r"\b(?:quantity|qty|q'ty|unit|units|pieces?|pcs?)\b", normalized):
        hits.add("quantity")
    if re.search(r"\b(?:amount|total|subtotal|grand|value|price)\b", normalized):
        hits.add("amount_total")
    if re.search(r"\b(?:currency|usd|cad|eur|gbp|jpy|cny|krw)\b", normalized):
        hits.add("currency")
    if re.search(r"\b(?:number of packages?|packages?|package|no & kinds|bundles?)\b", normalized):
        hits.add("number_of_packages")
    if re.search(r"\bnet\s+weight\b", normalized):
        # NET WEIGHT is a meaningful anchor, but not a gross-weight anchor.
        hits.add("net_weight_context")
    elif re.search(r"\b(?:gross\s+weight|gross|g\.w|g\.wt|g\.weight)\b", normalized):
        hits.add("gross_weight")
    elif re.fullmatch(r"(?:weight|g\.w|g\.wt|g\.weight)", normalized):
        hits.add("gross_weight")
    if re.search(r"\b(?:b/l|bl)\s*(?:no|number|#)\b", normalized) or re.search(r"\bbill of lading(?:\s+no|\s+number|\s*#)?\b", normalized):
        hits.add("bl_no")
    return hits


def _date_format(text: str) -> str | None:
    candidate = _clean_text(text).strip(" :;,.()")
    for name, pattern in _DATE_PATTERNS:
        if pattern.fullmatch(candidate):
            return name
    return None


def _number(text: str) -> bool:
    return bool(_NUMBER_PATTERN.fullmatch(_clean_text(text).strip(" :;,.()")))


def _measure_unit(text: str) -> str | None:
    candidate = _clean_text(text).strip(" :;,.()")
    match = _MEASURE_PATTERN.fullmatch(candidate) or _MEASURE_TOKEN_PATTERN.search(candidate)
    return match.group(1).upper() if match else None


def _unit_only(text: str) -> str | None:
    match = _UNIT_ONLY_PATTERN.fullmatch(_clean_text(text).strip(" :;,.()"))
    return match.group(1).upper() if match else None


def _money_features(text: str, *, allow_plain_integer: bool = False) -> tuple[bool, str | None, bool, bool]:
    candidate = _clean_text(text).strip(" :;,.()")
    if not _MONEY_PATTERN.fullmatch(candidate):
        return False, None, False, False
    if _MEASURE_PATTERN.fullmatch(candidate) or _UNIT_ONLY_PATTERN.fullmatch(candidate):
        return False, None, False, False
    code_match = re.search(r"\b(USD|CAD|EUR|GBP|JPY|CNY|KRW|HKD|AUD|SGD)\b", candidate, re.I)
    has_currency_marker = bool(code_match or re.search(r"[$€£¥]", candidate))
    if not has_currency_marker and "." not in candidate and not allow_plain_integer:
        return False, None, False, False
    return (
        True,
        code_match.group(1).upper() if code_match else None,
        "," in candidate,
        "." in candidate,
    )


def _line_groups(boxes: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    ordered = sorted(range(len(boxes)), key=lambda index: (min(boxes[index]["y"]), min(boxes[index]["x"])))
    groups: list[list[int]] = []
    current_top: int | None = None
    current_bottom: int | None = None
    for index in ordered:
        top = min(boxes[index]["y"])
        bottom = max(boxes[index]["y"])
        if not groups:
            groups.append([index])
            current_top = top
            current_bottom = bottom
            continue
        assert current_top is not None and current_bottom is not None
        height = max(bottom - top, current_bottom - current_top, 1)
        if top <= current_bottom + height * 0.35:
            groups[-1].append(index)
            current_bottom = max(current_bottom, bottom)
        else:
            groups.append([index])
            current_top = top
            current_bottom = bottom
    for group in groups:
        group.sort(key=lambda index: min(boxes[index]["x"]))
    return groups


def _value_candidate(field_name: str, text: str, *, anchored: bool = False) -> bool:
    candidate = _clean_text(text)
    if field_name in {"date", "on_board_date"}:
        return _date_format(candidate) is not None or bool(
            re.search(r"\b\d{1,4}[-/. ](?:[A-Za-z]{3,9}|\d{1,2})[-/. ,]\d{2,4}\b", candidate)
        )
    if field_name == "amount_total":
        return any(
            _money_features(match.group(0), allow_plain_integer=anchored)[0]
            for match in _MONEY_TOKEN_PATTERN.finditer(candidate)
        )
    if field_name == "currency":
        return bool(_CURRENCY_CODE_PATTERN.search(candidate) or re.search(r"[$€£¥]", candidate))
    if field_name in {"quantity", "number_of_packages", "gross_weight"}:
        if _MEASURE_PATTERN.fullmatch(candidate) or _NUMBER_PATTERN.fullmatch(candidate):
            return True
        return bool(_MEASURE_TOKEN_PATTERN.search(candidate)) or (
            anchored and bool(re.search(r"\b[+-]?\d[\d,]*(?:\.\d+)?\b", candidate))
        )
    if field_name in {"invoice_no", "bl_no"}:
        return bool(_ID_PATTERN.search(candidate))
    return False


def _value_candidate_indices(field_name: str, texts: Sequence[str], index: int, *, anchored: bool = False) -> set[int]:
    """Find value boxes, including the common number + unit split form."""
    candidates: set[int] = set()
    if _value_candidate(field_name, texts[index], anchored=anchored):
        candidates.add(index)
    if field_name not in {"quantity", "number_of_packages", "gross_weight"}:
        return candidates
    unit = _unit_only(texts[index])
    if unit:
        return candidates
    if not _number(texts[index]):
        return candidates
    next_index = index + 1
    if next_index < len(texts) and _unit_only(texts[next_index]):
        combined = f"{texts[index]} {_unit_only(texts[next_index])}"
        if _value_candidate(field_name, combined, anchored=anchored):
            candidates.update({index, next_index})
    return candidates


def _empty_field_stats() -> dict[str, Any]:
    return {
        "documents_with_label_anchor": 0,
        "documents_with_anchored_value": 0,
        "label_anchor_occurrences": 0,
        "anchored_value_occurrences": 0,
        "format_only_unanchored_candidate": 0,
        "format_only_unanchored_occurrences": 0,
        "ambiguous_or_unclassified": 0,
        "ambiguous_or_unclassified_occurrences": 0,
        # Compatibility aliases retained for existing consumers of the profile.
        "documents_with_candidate": 0,
        "occurrences": 0,
        "documents_without_candidate": 0,
        "documents_with_multiple_occurrences": 0,
        "same_bbox_label_value": 0,
        "separate_bbox_label_value": 0,
        "split_value_across_bboxes": 0,
        "table_like_occurrences": 0,
        "item_value_signals": 0,
        "total_value_signals": 0,
        "label_expressions": Counter(),
    }


_WEIGHT_UNITS = {"KG", "KGS", "LB", "LBS"}
_PACKAGE_UNITS = {
    "PKG", "PKGS", "BOX", "BOXES", "CTN", "CTNS", "BUNDLES", "BUNDLE",
    "CARTONS", "CARTON", "CASES", "CASE", "PALLETS", "PALLET",
}
_QUANTITY_UNITS = {"ST", "CT", "PC", "PCS"}


def _format_only_field(field_name: str, text: str) -> bool:
    """Whether a value has a recognizable format but no semantic label."""
    if field_name in {"date", "on_board_date"}:
        return _date_format(text) is not None
    if field_name == "amount_total":
        return _money_features(text)[0]
    if field_name == "currency":
        return bool(_CURRENCY_CODE_PATTERN.search(text) or re.search(r"[$€£¥]", text))
    unit = _measure_unit(text)
    if field_name == "gross_weight":
        return unit in _WEIGHT_UNITS
    if field_name == "number_of_packages":
        return unit in _PACKAGE_UNITS
    if field_name == "quantity":
        return unit in _QUANTITY_UNITS
    return False


def _unclassified_numeric(text: str) -> bool:
    return _number(text) and not _measure_unit(text) and not _unit_only(text) and not _money_features(text)[0]


def _line_index_map(lines: Sequence[Sequence[int]]) -> dict[int, int]:
    return {index: line_number for line_number, line in enumerate(lines) for index in line}


def _record_profile(record: TargetLabelRecord) -> dict[str, Any]:
    raw_boxes = record.record.get("bbox")
    if not isinstance(raw_boxes, list):
        raise ValueError("bbox must be a list")
    boxes: list[dict[str, Any]] = []
    for raw_box in raw_boxes:
        if not isinstance(raw_box, Mapping):
            continue
        text = raw_box.get("data")
        x = raw_box.get("x")
        y = raw_box.get("y")
        if not isinstance(text, str) or not isinstance(x, list) or not isinstance(y, list) or len(x) != 4 or len(y) != 4:
            continue
        if not all(isinstance(value, int) for value in x + y):
            continue
        boxes.append({"text": _clean_text(text), "x": x, "y": y})

    field_hits: dict[str, list[int]] = defaultdict(list)
    expression_counts: dict[str, Counter[str]] = defaultdict(Counter)
    date_formats = Counter()
    unit_counts = Counter()
    currency_codes = Counter()
    amount_count = 0
    amount_with_symbol = 0
    amount_with_thousands = 0
    amount_with_decimal = 0
    total_marker_indices: set[int] = set()
    numeric_indices: set[int] = set()
    measure_indices: set[int] = set()
    value_split_count = Counter()
    box_field_hits: dict[int, set[str]] = {}
    box_date_formats: dict[int, str | None] = {}
    box_measure_units: dict[int, str | None] = {}
    box_money: dict[int, tuple[bool, str | None, bool, bool]] = {}

    for index, box in enumerate(boxes):
        text = box["text"]
        hits = _field_hits(text)
        box_field_hits[index] = hits
        for field_name in hits:
            field_hits[field_name].append(index)
            expression_counts[field_name][text] += 1
        date_name = _date_format(text)
        box_date_formats[index] = date_name
        if date_name:
            date_formats[date_name] += 1
        measure_unit = _measure_unit(text)
        box_measure_units[index] = measure_unit
        if measure_unit:
            unit_counts[measure_unit] += 1
            measure_indices.add(index)
        unit = _unit_only(text)
        if unit:
            unit_counts[unit] += 1
            measure_indices.add(index)
        is_money, code, has_thousands, has_decimal = _money_features(text)
        box_money[index] = (is_money, code, has_thousands, has_decimal)
        if is_money:
            if code or _CURRENCY_CODE_PATTERN.search(text) or re.search(r"[$€£¥]", text):
                pass
            amount_count += 1
            amount_with_symbol += int(bool(re.search(r"[$€£¥]", text)))
            amount_with_thousands += int(has_thousands)
            amount_with_decimal += int(has_decimal)
            if code:
                currency_codes[code] += 1
        code_only = _CURRENCY_CODE_PATTERN.fullmatch(_clean_text(text).strip(" :;,.()"))
        if code_only:
            currency_codes[code_only.group(0).upper()] += 1
        if _number(text):
            numeric_indices.add(index)
        if _TOTAL_PATTERN.search(text):
            total_marker_indices.add(index)

    lines = _line_groups(boxes)
    line_by_index = _line_index_map(lines)
    table_like_rows = 0
    item_rows = 0
    total_rows = 0
    separate_pairs: dict[str, int] = Counter()
    same_bbox: dict[str, int] = Counter()
    anchored_values: dict[str, int] = Counter()
    format_only: dict[str, int] = Counter()
    format_only_occurrences: dict[str, int] = Counter()
    ambiguous: dict[str, int] = Counter()
    ambiguous_occurrences: dict[str, int] = Counter()
    unclassified_numeric_count = 0
    unclassified_numeric_docs = 0
    table_occurrences: dict[str, int] = Counter()
    item_signals: dict[str, int] = Counter()
    total_signals: dict[str, int] = Counter()

    for line in lines:
        line_texts = [boxes[index]["text"] for index in line]
        line_has_total = any(_TOTAL_PATTERN.search(text) for text in line_texts)
        numbers = [index for index in line if index in numeric_indices]
        measures = [index for index in line if index in measure_indices]
        if len(line) >= 3 and numbers:
            table_like_rows += 1
        if len(numbers) >= 2 or (numbers and any(_clean_text(boxes[index]["text"]).isalpha() for index in line)):
            item_rows += 1
        if line_has_total:
            total_rows += 1
        if numbers and measures:
            split_units = [_unit_only(boxes[index]["text"]) for index in measures]
            if any(unit in {"KG", "KGS", "LB", "LBS"} for unit in split_units):
                value_split_count["gross_weight"] += 1
            if any(unit in {"PKG", "PKGS", "BOX", "BOXES", "CTN", "CTNS", "BUNDLES", "BUNDLE", "CARTONS", "CARTON", "CASES", "CASE", "PALLETS", "PALLET"} for unit in split_units):
                value_split_count["number_of_packages"] += 1
            if any(unit in {"ST", "CT", "PC", "PCS"} for unit in split_units):
                value_split_count["quantity"] += 1
            if not split_units:
                value_split_count["quantity"] += 1
        line_has_any_anchor = any(box_field_hits[index] for index in line)
        for index in line:
            for field_name in box_field_hits[index]:
                if field_name not in FIELD_SPECS:
                    continue
                same_indices = _value_candidate_indices(
                    field_name, line_texts, line.index(index), anchored=True
                )
                same_indices = {line[position] for position in same_indices}
                if same_indices:
                    same_bbox[field_name] += 1
                    anchored_values[field_name] += len(same_indices)
                other_indices: set[int] = set()
                for other_index in line:
                    if other_index == index:
                        continue
                    if _value_candidate(field_name, boxes[other_index]["text"], anchored=True):
                        other_indices.add(other_index)
                # A numeric box followed by a unit-only box is one split value.
                for position, other_index in enumerate(line[:-1]):
                    if other_index == index and _number(boxes[other_index]["text"]):
                        if _unit_only(boxes[line[position + 1]]["text"]):
                            combined = f"{boxes[other_index]['text']} {_unit_only(boxes[line[position + 1]]['text'])}"
                            if _value_candidate(field_name, combined, anchored=True):
                                other_indices.update({other_index, line[position + 1]})
                other_indices.difference_update(same_indices)
                if other_indices:
                    separate_pairs[field_name] += 1
                    anchored_values[field_name] += 1
                if len(line) >= 3:
                    table_occurrences[field_name] += 1
                if line_has_total:
                    total_signals[field_name] += int(bool(same_indices or other_indices))
                else:
                    item_signals[field_name] += int(bool(same_indices or other_indices))

        for field_name in FIELD_KEYS_BY_DOCUMENT[record.document_type]:
            if any(field_name in box_field_hits[index] for index in line):
                continue
            for index in line:
                text = boxes[index]["text"]
                if field_name == "gross_weight" and "net_weight_context" in box_field_hits[index]:
                    ambiguous[field_name] += 1
                    ambiguous_occurrences[field_name] += 1
                elif field_name == "gross_weight" and any(
                    "net_weight_context" in box_field_hits[other_index] for other_index in line
                ) and _measure_unit(text) in _WEIGHT_UNITS:
                    ambiguous[field_name] += 1
                    ambiguous_occurrences[field_name] += 1
                elif _format_only_field(field_name, text):
                    format_only[field_name] += 1
                    format_only_occurrences[field_name] += 1
                elif field_name == "amount_total" and _unclassified_numeric(text) and not line_has_any_anchor:
                    ambiguous[field_name] += 1
                    ambiguous_occurrences[field_name] += 1

        if any(_unclassified_numeric(boxes[index]["text"]) for index in line if not line_has_any_anchor):
            unclassified_numeric_docs = 1
            unclassified_numeric_count += sum(
                _unclassified_numeric(boxes[index]["text"])
                for index in line
                if not line_has_any_anchor
            )

    # Value-only annotations may be separated from a label by a line break.
    # Keep this conservative: only the nearest following line is considered.
    for line_number, line in enumerate(lines[:-1]):
        anchor_fields = set().union(*(box_field_hits[index] for index in line))
        next_line = lines[line_number + 1]
        for field_name in anchor_fields & set(FIELD_SPECS):
            if any(_value_candidate(field_name, boxes[index]["text"], anchored=True) for index in line):
                continue
            if any(_value_candidate(field_name, boxes[index]["text"], anchored=True) for index in next_line):
                separate_pairs[field_name] += 1
                anchored_values[field_name] += 1

    candidate_counts: dict[str, int] = {}
    for field_name in FIELD_KEYS_BY_DOCUMENT[record.document_type]:
        candidate_counts[field_name] = len(field_hits.get(field_name, []))

    return {
        "box_count": len(boxes),
        "field_hits": {key: list(value) for key, value in field_hits.items()},
        "expression_counts": expression_counts,
        "date_formats": date_formats,
        "unit_counts": unit_counts,
        "currency_codes": currency_codes,
        "amount_count": amount_count,
        "amount_with_symbol": amount_with_symbol,
        "amount_with_thousands": amount_with_thousands,
        "amount_with_decimal": amount_with_decimal,
        "table_like_rows": table_like_rows,
        "item_rows": item_rows,
        "total_rows": total_rows,
        "value_split_count": dict(value_split_count),
        "same_bbox": same_bbox,
        "separate_pairs": separate_pairs,
        "table_occurrences": table_occurrences,
        "item_signals": item_signals,
        "total_signals": total_signals,
        "candidate_counts": candidate_counts,
        "anchored_values": anchored_values,
        "format_only": format_only,
        "format_only_occurrences": format_only_occurrences,
        "ambiguous": ambiguous,
        "ambiguous_occurrences": ambiguous_occurrences,
        "unclassified_numeric_count": unclassified_numeric_count,
        "unclassified_numeric_docs": unclassified_numeric_docs,
    }


def _merge_counter(target: Counter[str], source: Counter[str]) -> None:
    target.update(source)


def _representative_features(profile: Mapping[str, Any]) -> dict[str, int]:
    candidates = profile["candidate_counts"]
    return {
        "core_fields": sum(value > 0 for value in candidates.values()),
        "missing_core_fields": sum(value == 0 for value in candidates.values()),
        "table_rows": profile["table_like_rows"],
        "split_values": sum(profile["value_split_count"].values()),
        "repeated_fields": sum(len(indices) > 1 for indices in profile["field_hits"].values()),
        "item_rows": profile["item_rows"],
        "unusual_formats": sum(profile["date_formats"].values()) + sum(profile["unit_counts"].values()),
        "box_count": profile["box_count"],
    }


def _sample_reason(category: str, features: Mapping[str, int]) -> str:
    reasons = {
        "general": f"core candidate fields {features['core_fields']}개, bbox {features['box_count']}개",
        "core_field_rich": f"candidate field {features['core_fields']}개로 coverage가 높음",
        "missing_core_field": f"미확인 candidate field {features['missing_core_fields']}개",
        "complex_table": f"table-like row {features['table_rows']}개",
        "split_geometry": f"값 분리 후보 {features['split_values']}건",
        "repeated_field": f"반복 field 후보 {features['repeated_fields']}개",
        "many_item_rows": f"item-like row {features['item_rows']}개",
        "unusual_format": f"날짜/단위 표현 후보 {features['unusual_formats']}건",
    }
    return reasons[category]


def _select_representatives(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    categories = (
        "general", "core_field_rich", "missing_core_field", "complex_table",
        "split_geometry", "repeated_field", "many_item_rows", "unusual_format",
    )
    selected: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    feature_key_by_category = {
        "general": "core_fields",
        "core_field_rich": "core_fields",
        "missing_core_field": "missing_core_fields",
        "complex_table": "table_rows",
        "split_geometry": "split_values",
        "repeated_field": "repeated_fields",
        "many_item_rows": "item_rows",
        "unusual_format": "unusual_formats",
    }
    for category in categories:
        feature_key = feature_key_by_category[category]
        ranked = sorted(candidates, key=lambda item: (item["features"].get(feature_key, 0), item["features"]["core_fields"], item["features"]["box_count"]), reverse=True)
        for candidate in ranked:
            key = (candidate["split"], candidate["member_name"])
            if key not in used:
                selected.append({**candidate, "selection_reason": _sample_reason(category, candidate["features"])})
                used.add(key)
                break
    if len(selected) < limit:
        ranked = sorted(candidates, key=lambda item: (item["features"]["core_fields"], item["features"]["box_count"]), reverse=True)
        for candidate in ranked:
            key = (candidate["split"], candidate["member_name"])
            if key not in used:
                selected.append({**candidate, "selection_reason": _sample_reason("general", candidate["features"])})
                used.add(key)
            if len(selected) >= limit:
                break
    return selected[:limit]


def analyze_records(records: Iterable[TargetLabelRecord], representatives_per_type: int = 10) -> dict[str, Any]:
    """Analyze records already supplied by an iterator; useful for tests."""
    document_counts = Counter()
    malformed_counts = Counter()
    field_stats: dict[str, dict[str, Any]] = defaultdict(lambda: defaultdict(_empty_field_stats))
    type_counters: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    candidates_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in records:
        document_counts[(item.split, item.document_type)] += 1
        try:
            profile = _record_profile(item)
        except (KeyError, TypeError, ValueError):
            malformed_counts[item.document_type] += 1
            for field_name in FIELD_KEYS_BY_DOCUMENT[item.document_type]:
                field_stats[item.document_type][field_name]["documents_without_candidate"] += 1
                field_stats[item.document_type][field_name]["ambiguous_or_unclassified"] += 1
            continue
        features = _representative_features(profile)
        candidates_by_type[item.document_type].append({
            "split": item.split,
            "archive_name": item.archive_name,
            "member_name": item.member_name,
            "features": features,
        })
        for field_name in FIELD_KEYS_BY_DOCUMENT[item.document_type]:
            stats = field_stats[item.document_type][field_name]
            indices = profile["field_hits"].get(field_name, [])
            if indices:
                stats["documents_with_label_anchor"] += 1
                stats["label_anchor_occurrences"] += len(indices)
                stats["documents_with_candidate"] += 1
                stats["occurrences"] += len(indices)
                stats["documents_with_multiple_occurrences"] += int(len(indices) > 1)
            else:
                stats["documents_without_candidate"] += 1
            anchored_count = profile["anchored_values"].get(field_name, 0)
            if anchored_count:
                stats["documents_with_anchored_value"] += 1
                stats["anchored_value_occurrences"] += anchored_count
            format_count = profile["format_only_occurrences"].get(field_name, 0)
            if format_count:
                stats["format_only_unanchored_candidate"] += 1
                stats["format_only_unanchored_occurrences"] += format_count
            ambiguous_count = profile["ambiguous_occurrences"].get(field_name, 0)
            if field_name == "amount_total":
                ambiguous_count += profile["unclassified_numeric_count"]
            if ambiguous_count:
                stats["ambiguous_or_unclassified"] += 1
                stats["ambiguous_or_unclassified_occurrences"] += ambiguous_count
            stats["same_bbox_label_value"] += profile["same_bbox"].get(field_name, 0)
            stats["separate_bbox_label_value"] += profile["separate_pairs"].get(field_name, 0)
            stats["split_value_across_bboxes"] += profile["value_split_count"].get(field_name, 0)
            stats["table_like_occurrences"] += profile["table_occurrences"].get(field_name, 0)
            stats["item_value_signals"] += profile["item_signals"].get(field_name, 0)
            stats["total_value_signals"] += profile["total_signals"].get(field_name, 0)
            _merge_counter(stats["label_expressions"], profile["expression_counts"].get(field_name, Counter()))
        for key, counter in profile["date_formats"].items():
            type_counters[item.document_type]["date_formats"][key] += counter
        for key, counter in profile["unit_counts"].items():
            type_counters[item.document_type]["units"][key] += counter
        for key, counter in profile["currency_codes"].items():
            type_counters[item.document_type]["currency_codes"][key] += counter
        type_counters[item.document_type]["amount"]["annotations"] += profile["amount_count"]
        type_counters[item.document_type]["amount"]["with_symbol"] += profile["amount_with_symbol"]
        type_counters[item.document_type]["amount"]["with_thousands_separator"] += profile["amount_with_thousands"]
        type_counters[item.document_type]["amount"]["with_decimal"] += profile["amount_with_decimal"]
        type_counters[item.document_type]["geometry"]["table_like_rows"] += profile["table_like_rows"]
        type_counters[item.document_type]["geometry"]["item_rows"] += profile["item_rows"]
        type_counters[item.document_type]["geometry"]["total_rows"] += profile["total_rows"]
        type_counters[item.document_type]["geometry"]["split_value_rows"] += sum(profile["value_split_count"].values())

    types: dict[str, Any] = {}
    for document_type in DOCUMENT_TYPES:
        total = sum(count for (split, kind), count in document_counts.items() if kind == document_type)
        stats_output: dict[str, Any] = {}
        for field_name, stats in field_stats[document_type].items():
            stats_output[field_name] = {
                **{key: value for key, value in stats.items() if key != "label_expressions"},
                "coverage": stats["documents_with_candidate"] / total if total else 0.0,
                "label_anchor_coverage": stats["documents_with_label_anchor"] / total if total else 0.0,
                "anchored_value_coverage": stats["documents_with_anchored_value"] / total if total else 0.0,
                "format_only_rate": stats["format_only_unanchored_candidate"] / total if total else 0.0,
                "ambiguous_or_unclassified_rate": stats["ambiguous_or_unclassified"] / total if total else 0.0,
                "missing_rate": stats["documents_without_candidate"] / total if total else 0.0,
                "label_expressions": dict(stats["label_expressions"].most_common(30)),
            }
        types[document_type] = {
            "document_count": total,
            "field_stats": stats_output,
            "date_formats": dict(type_counters[document_type]["date_formats"].most_common()),
            "units": dict(type_counters[document_type]["units"].most_common()),
            "currency_codes": dict(type_counters[document_type]["currency_codes"].most_common()),
            "amount_patterns": dict(type_counters[document_type]["amount"]),
            "geometry": dict(type_counters[document_type]["geometry"]),
            "malformed_records": malformed_counts[document_type],
            "representative_samples": _select_representatives(candidates_by_type[document_type], representatives_per_type),
        }

    return {
        "analysis_scope": "target_ground_truth_labels_only",
        "document_count": sum(document_counts.values()),
        "document_counts_by_split": {
            split: {document_type: document_counts[(split, document_type)] for document_type in DOCUMENT_TYPES}
            for split in ("training", "validation")
        },
        "malformed_records": dict(malformed_counts),
        "document_types": types,
    }


def iter_target_label_records(
    archive_pairs: Mapping[str, Sequence[TargetArchivePair]],
) -> Iterable[TargetLabelRecord]:
    """Yield target label JSON records one at a time directly from ZIP files."""
    for split, pairs in archive_pairs.items():
        for pair in pairs:
            document_type = document_type_from_form_type(pair.form_type)
            try:
                archive = ZipFile(pair.label_archive)
            except (BadZipFile, OSError):
                continue
            with archive:
                for info in archive.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".json"):
                        continue
                    try:
                        with archive.open(info) as member:
                            record = json.load(member)
                        if not isinstance(record, Mapping):
                            raise ValueError("label record is not an object")
                        yield TargetLabelRecord(
                            split=split,
                            document_type=document_type,
                            archive_name=pair.label_archive.name,
                            member_name=info.filename,
                            record=record,
                        )
                    except (OSError, ValueError, json.JSONDecodeError):
                        yield TargetLabelRecord(
                            split=split,
                            document_type=document_type,
                            archive_name=pair.label_archive.name,
                            member_name=info.filename,
                            record={"bbox": None},
                        )


def analyze_target_archives(
    archive_pairs: Mapping[str, Sequence[TargetArchivePair]],
    representatives_per_type: int = 10,
) -> dict[str, Any]:
    """Run the streaming target-label analysis over archive pairs."""
    return analyze_records(
        iter_target_label_records(archive_pairs),
        representatives_per_type=representatives_per_type,
    )


def write_analysis_json(result: Mapping[str, Any], output_path: Path) -> None:
    """Write only the compact aggregate result and representatives."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
