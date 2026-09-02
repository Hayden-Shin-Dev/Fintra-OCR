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
    "bill_of_lading": ("bl_no", "shipper", "consignee", "goods_description", "number_of_packages", "gross_weight", "date"),
}

_DATE_PATTERNS = (
    ("iso", re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")),
    ("day_month_name_year", re.compile(r"^\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[- ]\d{2,4}$", re.I)),
    ("month_name_day_year", re.compile(r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}$", re.I)),
    ("numeric_day_month_year", re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")),
)
_MONEY_PATTERN = re.compile(r"^(?:[$€£¥]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*[A-Z]{3})?$", re.I)
_MONEY_TOKEN_PATTERN = re.compile(r"(?:[$€£¥]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*(?:USD|CAD|EUR|GBP|JPY|CNY|KRW|HKD|AUD|SGD))?", re.I)
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
    normalized = _normalized_expression(text)
    hits: set[str] = set()
    for field_name, expressions in FIELD_SPECS.items():
        if any(
            normalized == expression
            or normalized.startswith(expression + " ")
            or normalized.startswith(expression + ":")
            or (expression in {"invoice", "date", "dated", "gross", "weight", "total", "amount", "price", "value"} and re.search(rf"\b{re.escape(expression)}\b", normalized))
            for expression in expressions
        ):
            hits.add(field_name)
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
    match = _MEASURE_PATTERN.fullmatch(_clean_text(text).strip(" :;,.()"))
    return match.group(1).upper() if match else None


def _unit_only(text: str) -> str | None:
    match = _UNIT_ONLY_PATTERN.fullmatch(_clean_text(text).strip(" :;,.()"))
    return match.group(1).upper() if match else None


def _money_features(text: str) -> tuple[bool, str | None, bool, bool]:
    candidate = _clean_text(text).strip(" :;,.()")
    if not _MONEY_PATTERN.fullmatch(candidate):
        return False, None, False, False
    if _MEASURE_PATTERN.fullmatch(candidate) or _UNIT_ONLY_PATTERN.fullmatch(candidate):
        return False, None, False, False
    code_match = re.search(r"\b(USD|CAD|EUR|GBP|JPY|CNY|KRW|HKD|AUD|SGD)\b", candidate, re.I)
    if not code_match and not re.search(r"[$€£¥]", candidate) and "." not in candidate:
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


def _value_candidate(field_name: str, text: str) -> bool:
    candidate = _clean_text(text)
    if field_name == "date":
        return any(pattern.search(candidate) for _, pattern in _DATE_PATTERNS)
    if field_name == "amount_total":
        return bool(_MONEY_TOKEN_PATTERN.search(candidate)) and _money_features(candidate)[0]
    if field_name == "currency":
        return bool(_CURRENCY_CODE_PATTERN.search(candidate) or re.search(r"[$€£¥]", candidate))
    if field_name in {"quantity", "number_of_packages", "gross_weight"}:
        return bool(_MEASURE_PATTERN.search(candidate) or _NUMBER_PATTERN.search(candidate))
    if field_name in {"invoice_no", "bl_no"}:
        return bool(_ID_PATTERN.search(candidate))
    return False


def _empty_field_stats() -> dict[str, Any]:
    return {
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
            field_hits["date"].append(index)
        measure_unit = _measure_unit(text)
        box_measure_units[index] = measure_unit
        if measure_unit:
            unit_counts[measure_unit] += 1
            measure_indices.add(index)
            if measure_unit in {"KG", "KGS", "LB", "LBS"}:
                field_hits["gross_weight"].append(index)
            elif measure_unit in {"PKG", "PKGS", "BOX", "BOXES", "CTN", "CTNS", "BUNDLES", "BUNDLE", "CARTONS", "CARTON", "CASES", "CASE", "PALLETS", "PALLET"}:
                field_hits["number_of_packages"].append(index)
            elif measure_unit in {"ST", "CT", "PC", "PCS"}:
                field_hits["quantity"].append(index)
        unit = _unit_only(text)
        if unit:
            unit_counts[unit] += 1
            measure_indices.add(index)
        is_money, code, has_thousands, has_decimal = _money_features(text)
        box_money[index] = (is_money, code, has_thousands, has_decimal)
        if is_money:
            field_hits["amount_total"].append(index)
            if code or _CURRENCY_CODE_PATTERN.search(text) or re.search(r"[$€£¥]", text):
                field_hits["currency"].append(index)
            amount_count += 1
            amount_with_symbol += int(bool(re.search(r"[$€£¥]", text)))
            amount_with_thousands += int(has_thousands)
            amount_with_decimal += int(has_decimal)
            if code:
                currency_codes[code] += 1
        if _number(text):
            numeric_indices.add(index)
        if _TOTAL_PATTERN.search(text):
            total_marker_indices.add(index)

    lines = _line_groups(boxes)
    table_like_rows = 0
    item_rows = 0
    total_rows = 0
    separate_pairs: dict[str, int] = Counter()
    same_bbox: dict[str, int] = Counter()
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
        for index in line:
            hits = box_field_hits[index]
            for field_name in hits:
                if _value_candidate(field_name, boxes[index]["text"]):
                    same_bbox[field_name] += 1
                elif any(
                    other_index != index
                    and _value_candidate(field_name, boxes[other_index]["text"])
                    for other_index in line
                ):
                    separate_pairs[field_name] += 1
                if len(line) >= 3:
                    table_occurrences[field_name] += 1
                if line_has_total:
                    total_signals[field_name] += 1
                else:
                    item_signals[field_name] += 1

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
    for category in categories:
        ranked = sorted(candidates, key=lambda item: (item["features"].get(category if category != "unusual_format" else "unusual_formats", 0), item["features"]["core_fields"], item["features"]["box_count"]), reverse=True)
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
                stats["documents_with_candidate"] += 1
                stats["occurrences"] += len(indices)
                stats["documents_with_multiple_occurrences"] += int(len(indices) > 1)
            else:
                stats["documents_without_candidate"] += 1
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
