"""Streaming analysis of Fintra target-document ground-truth labels.

The profiler uses the *same deterministic field extractor* as the OCR pipeline.
GT text/bboxes are converted to perfect-confidence OCRPrediction objects, then
`extract_fields()` is executed. This prevents the analysis rules from drifting
away from the real extractor (the problem that caused the previous 16.5 profile
to over-count format signals and under/over-count semantic fields).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any
from zipfile import BadZipFile, ZipFile

from .common_schema import document_type_from_form_type
from .field_extraction import (
    CURRENCY_CODE_PATTERN,
    DATE_PATTERN,
    MONEY_PATTERN,
    PACKAGE_PATTERN,
    PACKAGE_UNITS,
    QUANTITY_PATTERN,
    QUANTITY_UNITS,
    UNIT_ONLY_PATTERN,
    WEIGHT_PATTERN,
    WEIGHT_UNITS,
    extract_fields,
    find_label_spans,
    _row_groups,
)
from .prediction_parser import OCRPrediction
from .target_selection import TargetArchivePair


DOCUMENT_TYPES = ("commercial_invoice", "packing_list", "bill_of_lading")
FORM_TYPE_BY_DOCUMENT = {
    "commercial_invoice": "상업송장",
    "packing_list": "포장명세서",
    "bill_of_lading": "선하증권",
}

# Keep the historical profile key names where they differ from the public OCR
# schema so existing analysis consumers do not break.
PROFILE_FIELD_MAP: dict[str, dict[str, str]] = {
    "commercial_invoice": {
        "invoice_no": "invoice_no",
        "date": "date",
        "buyer_consignee": "buyer",
        "goods_description": "goods_description",
        "quantity": "quantity",
        "amount_total": "amount",
        "currency": "currency",
    },
    "packing_list": {
        "invoice_no": "invoice_no",
        "goods_description": "goods_description",
        "quantity": "quantity",
        "number_of_packages": "number_of_packages",
        "gross_weight": "gross_weight",
    },
    "bill_of_lading": {
        "bl_no": "bl_no",
        "shipper": "shipper",
        "consignee": "consignee",
        "goods_description": "goods_description",
        "number_of_packages": "number_of_packages",
        "gross_weight": "gross_weight",
        "on_board_date": "on_board_date",
    },
}
FIELD_KEYS_BY_DOCUMENT = {
    document_type: tuple(field_map) for document_type, field_map in PROFILE_FIELD_MAP.items()
}
# Compatibility surface retained for callers/tests that import this symbol.
FIELD_SPECS = {
    profile_name: (extract_name,)
    for field_map in PROFILE_FIELD_MAP.values()
    for profile_name, extract_name in field_map.items()
}

_DATE_PATTERNS = (
    ("iso", re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")),
    ("day_month_name_year", re.compile(r"^\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[- ,]\d{2,4}$", re.I)),
    ("month_name_day_year", re.compile(r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}$", re.I)),
    ("numeric_day_month_year", re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")),
)
_CURRENCY_SYMBOL_RE = re.compile(r"[$€£¥]")
_NUMBER_RE = re.compile(r"^[+-]?\d[\d,]*(?:\.\d+)?$")
_TOTAL_RE = re.compile(r"\b(?:total|subtotal|grand\s+total|say)\b", re.I)
# A unit is often attached directly to a number (``614KG``), so a leading word
# boundary is too strict. Reject only alphabetic prefixes to avoid matching a
# unit inside an ordinary word.
_WEIGHT_UNIT_RE = re.compile(r"(?<![A-Z])(KGS|KG|LBS|LB|POUNDS|POUND)\b", re.I)
_PACKAGE_UNIT_RE = re.compile(r"(?<![A-Z])(PKGS|PKG|CTNS|CTN|BOXES|BOX|BAGS|BAG|BUNDLES|BUNDLE|CARTONS|CARTON|CASES|CASE|PALLETS|PALLET)\b", re.I)
_QUANTITY_UNIT_RE = re.compile(r"(?<![A-Z])(EACH|EA|PCS|PC|PIECES|PIECE|UNITS|UNIT|ST|CT)\b", re.I)
_CURRENCY_CODE_TOKEN_RE = re.compile(r"\b(USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW|HKD|SGD)\b", re.I)
_NON_TARGET_CONTEXT_RE: dict[str, re.Pattern[str]] = {
    "gross_weight": re.compile(r"\b(?:net\s*(?:weight|wt|wgt)|n\s*[./]?\s*w(?:t)?|tare\s*weight)\b", re.I),
    "amount_total": re.compile(r"\b(?:unit\s+price|price\s+per|freight|tax|discount|rate)\b", re.I),
}


@dataclass(frozen=True)
class TargetLabelRecord:
    split: str
    document_type: str
    archive_name: str
    member_name: str
    record: Mapping[str, Any]


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _date_format(text: str) -> str | None:
    candidate = _clean_text(text).strip(" :;,.()")
    for name, pattern in _DATE_PATTERNS:
        if pattern.fullmatch(candidate):
            return name
    return None


def _number(text: str) -> bool:
    return bool(_NUMBER_RE.fullmatch(_clean_text(text).strip(" :;,.()")))


def _unit(text: str) -> str | None:
    candidate = _clean_text(text).strip(" :;,.()")
    match = UNIT_ONLY_PATTERN.fullmatch(candidate)
    if match:
        return match.group(0).upper()
    for pattern in (_WEIGHT_UNIT_RE, _PACKAGE_UNIT_RE, _QUANTITY_UNIT_RE):
        match = pattern.search(candidate)
        if match:
            return match.group(1).upper()
    return None


def _money_format_signal(text: str) -> bool:
    """Conservative unanchored money signal.

    Plain decimals are intentionally *not* treated as amount evidence because
    they can be quantity/weight/price values. A currency symbol/code is needed
    when there is no semantic amount label.
    """
    candidate = _clean_text(text).strip(" :;,.()")
    if WEIGHT_PATTERN.fullmatch(candidate) or PACKAGE_PATTERN.fullmatch(candidate):
        return False
    return bool(MONEY_PATTERN.fullmatch(candidate) and (
        _CURRENCY_SYMBOL_RE.search(candidate) or _CURRENCY_CODE_TOKEN_RE.search(candidate)
    ))


def _format_only_signal(profile_field: str, text: str) -> bool:
    candidate = _clean_text(text).strip(" :;,.()")
    if profile_field in {"date", "on_board_date"}:
        return bool(DATE_PATTERN.search(candidate))
    if profile_field == "amount_total":
        return _money_format_signal(candidate)
    if profile_field == "currency":
        return bool(_CURRENCY_SYMBOL_RE.search(candidate) or _CURRENCY_CODE_TOKEN_RE.search(candidate))
    if profile_field == "gross_weight":
        return bool(WEIGHT_PATTERN.fullmatch(candidate))
    if profile_field == "number_of_packages":
        return bool(PACKAGE_PATTERN.fullmatch(candidate))
    if profile_field == "quantity":
        if not QUANTITY_PATTERN.fullmatch(candidate):
            return False
        unit = _unit(candidate)
        return unit in QUANTITY_UNITS
    return False


def _to_predictions(record: TargetLabelRecord) -> tuple[list[OCRPrediction], int]:
    raw_boxes = record.record.get("bbox")
    if not isinstance(raw_boxes, list):
        raise ValueError("bbox must be a list")
    predictions: list[OCRPrediction] = []
    malformed_boxes = 0
    for raw_box in raw_boxes:
        if not isinstance(raw_box, Mapping):
            malformed_boxes += 1
            continue
        text, x, y = raw_box.get("data"), raw_box.get("x"), raw_box.get("y")
        if (
            not isinstance(text, str)
            or not isinstance(x, list)
            or not isinstance(y, list)
            or len(x) != 4
            or len(y) != 4
            or not all(isinstance(value, int) for value in x + y)
        ):
            malformed_boxes += 1
            continue
        predictions.append(OCRPrediction(_clean_text(text), tuple(x), tuple(y), 1.0))
    return predictions, malformed_boxes


def _field_anchor_data(
    predictions: Sequence[OCRPrediction], document_type: str
) -> tuple[dict[str, list[tuple[int, ...]]], dict[str, Counter[str]]]:
    indices: dict[str, list[tuple[int, ...]]] = defaultdict(list)
    expressions: dict[str, Counter[str]] = defaultdict(Counter)
    for profile_field, extract_field in PROFILE_FIELD_MAP[document_type].items():
        for span in find_label_spans(predictions, extract_field):
            indices[profile_field].append(span.indices)
            expressions[profile_field][span.text] += 1
    return indices, expressions


def _source_rows(predictions: Sequence[OCRPrediction], source_indices: Sequence[int]) -> set[int]:
    rows = _row_groups(predictions)
    index_to_row = {index: row_number for row_number, row in enumerate(rows) for index in row}
    return {index_to_row[index] for index in source_indices if index in index_to_row}


def _split_value_count(
    predictions: Sequence[OCRPrediction], source_indices: Sequence[int], profile_field: str
) -> int:
    if len(source_indices) < 2:
        return 0
    rows = _row_groups(predictions)
    index_to_row = {index: row_number for row_number, row in enumerate(rows) for index in row}
    grouped: dict[int, list[int]] = defaultdict(list)
    for index in source_indices:
        if index in index_to_row:
            grouped[index_to_row[index]].append(index)
    count = 0
    for group in grouped.values():
        if len(group) < 2:
            continue
        text = " ".join(predictions[index].text for index in sorted(group, key=lambda i: min(predictions[i].x)))
        if profile_field == "gross_weight" and WEIGHT_PATTERN.fullmatch(text.strip()):
            count += 1
        elif profile_field == "number_of_packages" and PACKAGE_PATTERN.fullmatch(text.strip()):
            count += 1
        elif profile_field == "quantity" and QUANTITY_PATTERN.fullmatch(text.strip()):
            count += 1
        elif profile_field in {"date", "on_board_date"} and DATE_PATTERN.search(text):
            count += 1
    return count


def _table_metrics(predictions: Sequence[OCRPrediction]) -> tuple[int, int, int]:
    table_like = item_rows = total_rows = 0
    for row in _row_groups(predictions):
        texts = [predictions[index].text for index in row]
        has_number = any(_number(text) or _unit(text) for text in texts)
        has_total = any(_TOTAL_RE.search(text) for text in texts)
        if len(row) >= 3 and has_number:
            table_like += 1
        if has_total:
            total_rows += 1
        elif len(row) >= 2 and has_number:
            item_rows += 1
    return table_like, item_rows, total_rows


def _nearby_unmatched_contexts(
    predictions: Sequence[OCRPrediction], signal_indices: set[int], known_anchor_indices: set[int]
) -> Counter[str]:
    """Collect text immediately left of unanchored format signals for diagnostics.

    These strings are *not* promoted to aliases automatically. They are only a
    review list for discovering real label variants on the full dataset.
    """
    contexts: Counter[str] = Counter()
    for row in _row_groups(predictions):
        for position, index in enumerate(row):
            if index not in signal_indices:
                continue
            for previous in row[max(0, position - 2):position]:
                if previous in known_anchor_indices:
                    continue
                text = _clean_text(predictions[previous].text)
                if text and any(char.isalpha() for char in text) and not _number(text):
                    contexts[text] += 1
    return contexts


def _signal_has_other_semantic_context(
    profile_field: str,
    predictions: Sequence[OCRPrediction],
    signal_index: int,
    anchor_indices: Mapping[str, list[tuple[int, ...]]],
) -> bool:
    """Return true when a format-like value is visibly owned by another label.

    Example: ``NET WEIGHT | 500 KG`` is not a format-only *gross weight*
    candidate. The value has explicit non-target semantics. Likewise a value on
    a row anchored as quantity/package should not be re-used as another field's
    format-only evidence.
    """
    rows = _row_groups(predictions)
    index_to_row = {index: row_no for row_no, row in enumerate(rows) for index in row}
    row_no = index_to_row.get(signal_index)
    if row_no is None:
        return False
    row = rows[row_no]
    row_set = set(row)

    for other_field, spans in anchor_indices.items():
        if other_field == profile_field:
            continue
        if any(row_set.intersection(span) for span in spans):
            return True

    row_text = " ".join(predictions[index].text for index in row)
    context_pattern = _NON_TARGET_CONTEXT_RE.get(profile_field)
    return bool(context_pattern and context_pattern.search(row_text))


def _record_profile(record: TargetLabelRecord) -> dict[str, Any]:
    predictions, malformed_boxes = _to_predictions(record)
    if malformed_boxes:
        # A record can still be profiled with valid boxes, but the malformed box
        # count is surfaced separately instead of silently ignored.
        pass

    fields = extract_fields(FORM_TYPE_BY_DOCUMENT[record.document_type], predictions)
    anchor_indices, expression_counts = _field_anchor_data(predictions, record.document_type)
    table_like_rows, item_rows, total_rows = _table_metrics(predictions)

    date_formats: Counter[str] = Counter()
    unit_counts: Counter[str] = Counter()
    currency_codes: Counter[str] = Counter()
    amount_patterns: Counter[str] = Counter()
    numeric_indices: set[int] = set()
    for prediction_index, prediction in enumerate(predictions):
        text = prediction.text
        date_name = _date_format(text)
        if date_name:
            date_formats[date_name] += 1
        unit = _unit(text)
        if unit:
            unit_counts[unit] += 1
        code = _CURRENCY_CODE_TOKEN_RE.search(text)
        if code:
            currency_codes[code.group(1).upper()] += 1
        if MONEY_PATTERN.fullmatch(text.strip()) and not WEIGHT_PATTERN.fullmatch(text.strip()) and not PACKAGE_PATTERN.fullmatch(text.strip()):
            amount_patterns["numeric_money_shape"] += 1
            amount_patterns["currency_marked"] += int(_money_format_signal(text))
            amount_patterns["with_symbol"] += int(bool(_CURRENCY_SYMBOL_RE.search(text)))
            amount_patterns["with_currency_code"] += int(bool(_CURRENCY_CODE_TOKEN_RE.search(text)))
            amount_patterns["with_thousands_separator"] += int("," in text)
            amount_patterns["with_decimal"] += int("." in text)
        if _number(text):
            numeric_indices.add(prediction_index)

    field_results: dict[str, dict[str, Any]] = {}
    all_known_anchor_indices = {
        index for spans in anchor_indices.values() for span in spans for index in span
    }
    unmatched_contexts: dict[str, Counter[str]] = defaultdict(Counter)

    for profile_field, extract_field in PROFILE_FIELD_MAP[record.document_type].items():
        evidence = fields[extract_field]
        spans = anchor_indices.get(profile_field, [])
        has_anchor = bool(spans)
        has_value = bool(evidence.source_indices) and evidence.status in {"found", "ambiguous"}
        has_anchored_value = has_value and has_anchor
        same_bbox = int(has_anchored_value and any(set(evidence.source_indices) & set(span) for span in spans))
        separate_bbox = int(has_anchored_value and not same_bbox)

        raw_signal_indices = {
            index for index, prediction in enumerate(predictions)
            if index not in evidence.source_indices and _format_only_signal(profile_field, prediction.text)
        }
        non_target_signal_indices = {
            index for index in raw_signal_indices
            if _signal_has_other_semantic_context(
                profile_field, predictions, index, anchor_indices
            )
        }
        signal_indices = raw_signal_indices - non_target_signal_indices
        has_format_only = bool(signal_indices) and not has_value
        if signal_indices:
            unmatched_contexts[profile_field].update(
                _nearby_unmatched_contexts(predictions, signal_indices, all_known_anchor_indices)
            )

        if evidence.status == "ambiguous" and has_anchor:
            exclusive_status = "ambiguous"
        elif has_anchored_value:
            exclusive_status = "anchored_value"
        elif has_value and evidence.status == "ambiguous":
            exclusive_status = "derived_ambiguous"
        elif has_value:
            exclusive_status = "derived_value"
        elif has_anchor:
            exclusive_status = "label_only"
        elif has_format_only:
            exclusive_status = "format_only"
        elif non_target_signal_indices:
            exclusive_status = "non_target_context"
        else:
            exclusive_status = "missing"

        source_rows = _source_rows(predictions, evidence.source_indices)
        rows = _row_groups(predictions)
        total_signal = 0
        item_signal = 0
        table_occurrences = 0
        for row_no in source_rows:
            row = rows[row_no]
            text = " ".join(predictions[index].text for index in row)
            if _TOTAL_RE.search(text) or any(_TOTAL_RE.search(expression) for expression in expression_counts.get(profile_field, ())):
                total_signal += 1
            else:
                item_signal += 1
            if len(row) >= 3:
                table_occurrences += 1

        field_results[profile_field] = {
            "has_anchor": has_anchor,
            "anchor_occurrences": len(spans),
            "has_value": has_value,
            "has_anchored_value": has_anchored_value,
            "value_occurrences": max(1, len(source_rows)) if has_value else 0,
            "evidence_status": evidence.status,
            "same_bbox": same_bbox,
            "separate_bbox": separate_bbox,
            "format_only": has_format_only,
            "format_only_occurrences": len(signal_indices) if has_format_only else 0,
            "non_target_context_occurrences": len(non_target_signal_indices),
            "exclusive_status": exclusive_status,
            "split_value_count": _split_value_count(predictions, evidence.source_indices, profile_field),
            "table_occurrences": table_occurrences,
            "item_signals": item_signal,
            "total_signals": total_signal,
            "source_indices": evidence.source_indices,
        }

    used_numeric_indices = {
        index
        for result in field_results.values()
        for index in result["source_indices"]
        if index in numeric_indices
    }
    unclassified_numeric_count = len(numeric_indices - used_numeric_indices)

    candidate_counts = {
        field_name: int(result["has_anchored_value"])
        for field_name, result in field_results.items()
    }
    return {
        "box_count": len(predictions),
        "malformed_boxes": malformed_boxes,
        "field_results": field_results,
        "field_hits": {key: [index for span in spans for index in span] for key, spans in anchor_indices.items()},
        "expression_counts": expression_counts,
        "date_formats": date_formats,
        "unit_counts": unit_counts,
        "currency_codes": currency_codes,
        "amount_patterns": amount_patterns,
        "table_like_rows": table_like_rows,
        "item_rows": item_rows,
        "total_rows": total_rows,
        "candidate_counts": candidate_counts,
        "unclassified_numeric_count": unclassified_numeric_count,
        "unmatched_contexts": unmatched_contexts,
    }


def _empty_field_stats() -> dict[str, Any]:
    return {
        "documents_with_label_anchor": 0,
        "documents_with_anchored_value": 0,
        "documents_with_extracted_value": 0,
        "documents_with_found_value": 0,
        "documents_with_ambiguous_value": 0,
        "label_anchor_occurrences": 0,
        "anchored_value_occurrences": 0,
        "format_only_unanchored_candidate": 0,
        "format_only_unanchored_occurrences": 0,
        "non_target_context_documents": 0,
        "non_target_context_occurrences": 0,
        "ambiguous_or_unclassified": 0,
        "ambiguous_or_unclassified_occurrences": 0,
        "documents_with_candidate": 0,
        "occurrences": 0,
        "documents_without_candidate": 0,
        "documents_without_label_anchor": 0,
        "documents_with_multiple_occurrences": 0,
        "same_bbox_label_value": 0,
        "separate_bbox_label_value": 0,
        "split_value_across_bboxes": 0,
        "table_like_occurrences": 0,
        "item_value_signals": 0,
        "total_value_signals": 0,
        "label_expressions": Counter(),
        "unmatched_context_expressions": Counter(),
        "exclusive_status_counts": Counter(),
    }


def _representative_features(profile: Mapping[str, Any]) -> dict[str, int]:
    candidates = profile["candidate_counts"]
    return {
        "core_fields": sum(value > 0 for value in candidates.values()),
        "missing_core_fields": sum(value == 0 for value in candidates.values()),
        "table_rows": profile["table_like_rows"],
        "split_values": sum(result["split_value_count"] for result in profile["field_results"].values()),
        "repeated_fields": sum(result["anchor_occurrences"] > 1 for result in profile["field_results"].values()),
        "item_rows": profile["item_rows"],
        "unusual_formats": sum(profile["date_formats"].values()) + sum(profile["unit_counts"].values()),
        "box_count": profile["box_count"],
    }


def _sample_reason(category: str, features: Mapping[str, int]) -> str:
    reasons = {
        "general": f"anchored core fields {features['core_fields']}개, bbox {features['box_count']}개",
        "core_field_rich": f"anchored core field {features['core_fields']}개로 coverage가 높음",
        "missing_core_field": f"미추출 core field {features['missing_core_fields']}개",
        "complex_table": f"table-like row {features['table_rows']}개",
        "split_geometry": f"split value {features['split_values']}건",
        "repeated_field": f"반복 label anchor {features['repeated_fields']}개",
        "many_item_rows": f"item-like row {features['item_rows']}개",
        "unusual_format": f"날짜/단위 표현 {features['unusual_formats']}건",
    }
    return reasons[category]


def _select_representatives(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    categories = (
        "general", "core_field_rich", "missing_core_field", "complex_table",
        "split_geometry", "repeated_field", "many_item_rows", "unusual_format",
    )
    feature_key = {
        "general": "core_fields", "core_field_rich": "core_fields",
        "missing_core_field": "missing_core_fields", "complex_table": "table_rows",
        "split_geometry": "split_values", "repeated_field": "repeated_fields",
        "many_item_rows": "item_rows", "unusual_format": "unusual_formats",
    }
    selected: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    for category in categories:
        key = feature_key[category]
        ranked = sorted(candidates, key=lambda item: (item["features"].get(key, 0), item["features"]["core_fields"], item["features"]["box_count"]), reverse=True)
        for candidate in ranked:
            identity = (candidate["split"], candidate["member_name"])
            if identity in used:
                continue
            selected.append({**candidate, "selection_reason": _sample_reason(category, candidate["features"])})
            used.add(identity)
            break
    if len(selected) < limit:
        ranked = sorted(candidates, key=lambda item: (item["features"]["core_fields"], item["features"]["box_count"]), reverse=True)
        for candidate in ranked:
            identity = (candidate["split"], candidate["member_name"])
            if identity in used:
                continue
            selected.append({**candidate, "selection_reason": _sample_reason("general", candidate["features"])})
            used.add(identity)
            if len(selected) >= limit:
                break
    return selected[:limit]


def analyze_records(records: Iterable[TargetLabelRecord], representatives_per_type: int = 10) -> dict[str, Any]:
    """Analyze GT records using the production field extractor as the oracle path."""
    document_counts = Counter()
    malformed_counts = Counter()
    malformed_box_counts = Counter()
    unclassified_numeric = Counter()
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
                stats = field_stats[item.document_type][field_name]
                stats["documents_without_candidate"] += 1
                stats["exclusive_status_counts"]["malformed"] += 1
            continue

        malformed_box_counts[item.document_type] += profile["malformed_boxes"]
        unclassified_numeric[item.document_type] += profile["unclassified_numeric_count"]
        features = _representative_features(profile)
        candidates_by_type[item.document_type].append({
            "split": item.split,
            "archive_name": item.archive_name,
            "member_name": item.member_name,
            "features": features,
        })

        for field_name in FIELD_KEYS_BY_DOCUMENT[item.document_type]:
            result = profile["field_results"][field_name]
            stats = field_stats[item.document_type][field_name]
            if result["has_anchor"]:
                stats["documents_with_label_anchor"] += 1
                stats["documents_with_candidate"] += 1
                stats["label_anchor_occurrences"] += result["anchor_occurrences"]
                stats["occurrences"] += result["anchor_occurrences"]
                stats["documents_with_multiple_occurrences"] += int(result["anchor_occurrences"] > 1)
            else:
                stats["documents_without_candidate"] += 1
                stats["documents_without_label_anchor"] += 1
            if result["has_value"]:
                stats["documents_with_extracted_value"] += 1
            if result["has_anchored_value"]:
                stats["documents_with_anchored_value"] += 1
                stats["anchored_value_occurrences"] += result["value_occurrences"]
                if result["evidence_status"] == "found":
                    stats["documents_with_found_value"] += 1
                else:
                    stats["documents_with_ambiguous_value"] += 1
            if result["format_only"]:
                stats["format_only_unanchored_candidate"] += 1
                stats["format_only_unanchored_occurrences"] += result["format_only_occurrences"]
            if result["non_target_context_occurrences"]:
                stats["non_target_context_documents"] += 1
                stats["non_target_context_occurrences"] += result["non_target_context_occurrences"]
            if result["exclusive_status"] in {"ambiguous", "derived_ambiguous", "label_only", "non_target_context"}:
                stats["ambiguous_or_unclassified"] += 1
                stats["ambiguous_or_unclassified_occurrences"] += 1
            stats["exclusive_status_counts"][result["exclusive_status"]] += 1
            stats["same_bbox_label_value"] += result["same_bbox"]
            stats["separate_bbox_label_value"] += result["separate_bbox"]
            stats["split_value_across_bboxes"] += result["split_value_count"]
            stats["table_like_occurrences"] += result["table_occurrences"]
            stats["item_value_signals"] += result["item_signals"]
            stats["total_value_signals"] += result["total_signals"]
            stats["label_expressions"].update(profile["expression_counts"].get(field_name, Counter()))
            stats["unmatched_context_expressions"].update(profile["unmatched_contexts"].get(field_name, Counter()))

        type_counters[item.document_type]["date_formats"].update(profile["date_formats"])
        type_counters[item.document_type]["units"].update(profile["unit_counts"])
        type_counters[item.document_type]["currency_codes"].update(profile["currency_codes"])
        type_counters[item.document_type]["amount"].update(profile["amount_patterns"])
        type_counters[item.document_type]["geometry"]["table_like_rows"] += profile["table_like_rows"]
        type_counters[item.document_type]["geometry"]["item_rows"] += profile["item_rows"]
        type_counters[item.document_type]["geometry"]["total_rows"] += profile["total_rows"]
        type_counters[item.document_type]["geometry"]["split_value_rows"] += sum(
            result["split_value_count"] for result in profile["field_results"].values()
        )

    types: dict[str, Any] = {}
    for document_type in DOCUMENT_TYPES:
        total = sum(count for (split, kind), count in document_counts.items() if kind == document_type)
        stats_output: dict[str, Any] = {}
        for field_name, stats in field_stats[document_type].items():
            exclusive = dict(stats["exclusive_status_counts"])
            if sum(exclusive.values()) != total:
                raise AssertionError(
                    f"exclusive status partition failed for {document_type}.{field_name}: "
                    f"{sum(exclusive.values())} != {total}"
                )
            stats_output[field_name] = {
                **{
                    key: value for key, value in stats.items()
                    if key not in {"label_expressions", "unmatched_context_expressions", "exclusive_status_counts"}
                },
                "coverage": stats["documents_with_anchored_value"] / total if total else 0.0,
                "label_anchor_coverage": stats["documents_with_label_anchor"] / total if total else 0.0,
                "anchored_value_coverage": stats["documents_with_anchored_value"] / total if total else 0.0,
                "format_only_rate": stats["format_only_unanchored_candidate"] / total if total else 0.0,
                "ambiguous_or_unclassified_rate": stats["ambiguous_or_unclassified"] / total if total else 0.0,
                "missing_rate": exclusive.get("missing", 0) / total if total else 0.0,
                "exclusive_document_status": exclusive,
                "label_expressions": dict(stats["label_expressions"].most_common(30)),
                "unmatched_context_expressions": dict(stats["unmatched_context_expressions"].most_common(30)),
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
            "malformed_boxes": malformed_box_counts[document_type],
            "unclassified_numeric_occurrences": unclassified_numeric[document_type],
            "representative_samples": _select_representatives(candidates_by_type[document_type], representatives_per_type),
        }

    return {
        "analysis_version": "16.5-v2-extractor-aligned",
        "analysis_scope": "target_ground_truth_labels_only",
        "semantic_policy": "visible_label_anchor_then_geometry; formats_are_secondary_only",
        "metric_definitions": {
            "documents_with_label_anchor": "document contains an explicit visible semantic label for the field",
            "documents_with_anchored_value": "production extractor returned a value and an explicit semantic label exists",
            "documents_with_extracted_value": "production extractor returned found/ambiguous evidence; includes explicitly derived currency evidence",
            "format_only_unanchored_candidate": "field-compatible format exists without an extracted value or explicit semantic anchor",
            "non_target_context_documents": "field-like format is explicitly owned by another semantic context, e.g. NET WEIGHT is not GROSS WEIGHT",
            "unclassified_numeric_occurrences": "plain numeric GT boxes not consumed by any extracted field evidence",
            "exclusive_document_status": "mutually exclusive per-field partition; counts sum to the document count",
            "legacy_documents_with_candidate": "deprecated compatibility alias for documents_with_label_anchor",
            "legacy_documents_without_candidate": "deprecated compatibility alias for documents_without_label_anchor",
        },
        "exclusive_status_definitions": {
            "anchored_value": "explicit label plus extracted value",
            "ambiguous": "explicit label plus extractor ambiguity",
            "derived_value": "self-describing/derived value without explicit target label (primarily currency)",
            "derived_ambiguous": "derived evidence is ambiguous (e.g. currency symbol without ISO code)",
            "label_only": "explicit label exists but no compatible value was deterministically attached",
            "format_only": "compatible value format exists without target semantic label",
            "non_target_context": "compatible format is visibly associated with a different semantic label/context",
            "missing": "no target label, extracted value, or compatible unanchored format",
            "malformed": "record structure could not be profiled",
        },
        "document_count": sum(document_counts.values()),
        "document_counts_by_split": {
            split: {document_type: document_counts[(split, document_type)] for document_type in DOCUMENT_TYPES}
            for split in ("training", "validation")
        },
        "malformed_records": dict(malformed_counts),
        "document_types": types,
    }


def iter_target_label_records(archive_pairs: Mapping[str, Sequence[TargetArchivePair]]) -> Iterable[TargetLabelRecord]:
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
                        yield TargetLabelRecord(split, document_type, pair.label_archive.name, info.filename, record)
                    except (OSError, ValueError, json.JSONDecodeError):
                        yield TargetLabelRecord(split, document_type, pair.label_archive.name, info.filename, {"bbox": None})


def analyze_target_archives(
    archive_pairs: Mapping[str, Sequence[TargetArchivePair]], representatives_per_type: int = 10
) -> dict[str, Any]:
    return analyze_records(iter_target_label_records(archive_pairs), representatives_per_type=representatives_per_type)


def write_analysis_json(result: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

