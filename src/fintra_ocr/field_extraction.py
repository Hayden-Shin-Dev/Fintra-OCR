"""Deterministic MVP field extraction from normalized OCR predictions."""

import re
import unicodedata
from collections.abc import Callable, Sequence

from .field_evidence import FieldEvidence, missing_field, make_field_evidence
from .prediction_parser import OCRPrediction


DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}[-/]\w{3}[-/]\d{2,4}|"
    r"\w{3,9}\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)
ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9./-]*$", re.IGNORECASE)
MONEY_PATTERN = re.compile(r"^(?:[$€£]|USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW)?\s*"
                           r"\d[\d,]*(?:\.\d+)?$", re.IGNORECASE)
WEIGHT_PATTERN = re.compile(
    r"\b\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS)\b", re.IGNORECASE
)
PACKAGE_PATTERN = re.compile(
    r"\b\d[\d,.]*\s*(?:PKG|PCS?|CTN?|CT|ST|BOX|BAG|BUNDLES?)\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"^\d[\d,.]*$")
INTEGER_PATTERN = re.compile(r"^\d[\d,]*$")

_CONTROL_WORDS = {
    "amount", "carrier", "cbm", "collect", "container", "containers",
    "date", "delivery", "description", "destination", "discharge",
    "freight", "gross", "hs", "invoice", "issue", "loading", "marks",
    "measurement", "net", "number", "on", "origin", "packages", "party",
    "payment", "place", "port", "price", "quantity", "receipt", "remark",
    "seal", "shipping", "signature", "signed", "total", "unit", "vessel",
    "voy", "weight",
}


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _has_alias(text: str, aliases: Sequence[str]) -> bool:
    normalized = _normalized(text)
    return any(alias in normalized for alias in aliases)


def _same_row(first: OCRPrediction, second: OCRPrediction) -> bool:
    first_top, first_bottom = min(first.y), max(first.y)
    second_top, second_bottom = min(second.y), max(second.y)
    overlap = max(0, min(first_bottom, second_bottom) - max(first_top, second_top))
    return overlap > 0 or abs((first_top + first_bottom) - (second_top + second_bottom)) <= 20


def _right_or_below(
    predictions: Sequence[OCRPrediction], label_index: int
) -> list[int]:
    label = predictions[label_index]
    label_right = max(label.x)
    label_bottom = max(label.y)
    label_height = max(label.y) - min(label.y)
    candidates: list[tuple[tuple[int, int, int], int]] = []
    for index, prediction in enumerate(predictions):
        if index == label_index:
            continue
        prediction_left = min(prediction.x)
        prediction_top = min(prediction.y)
        if prediction_left >= label_right - 10 and _same_row(label, prediction):
            distance = (0, max(0, prediction_left - label_right), index)
        elif prediction_top >= label_bottom and prediction_top - label_bottom <= max(80, label_height * 3):
            distance = (1, prediction_top - label_bottom, index)
        else:
            continue
        candidates.append((distance, index))
    return [index for _, index in sorted(candidates)]


def _label_indices(predictions: Sequence[OCRPrediction], aliases: Sequence[str]) -> list[int]:
    return [index for index, prediction in enumerate(predictions) if _has_alias(prediction.text, aliases)]


def _visual_order_indices(predictions: Sequence[OCRPrediction]) -> list[int]:
    return sorted(
        range(len(predictions)),
        key=lambda index: (min(predictions[index].y), min(predictions[index].x), index),
    )


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
                return make_field_evidence(field_name, list(predictions), (index,), value)
    return None


def _labeled_value(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    aliases: Sequence[str],
    value_pattern: re.Pattern[str] | Callable[[str], bool],
    *,
    allow_ambiguous: bool = False,
) -> FieldEvidence:
    for label_index in _label_indices(predictions, aliases):
        candidates = [
            index for index in _right_or_below(predictions, label_index)
            if (
                value_pattern.search(predictions[index].text)
                if hasattr(value_pattern, "search")
                else value_pattern(predictions[index].text)
            )
        ]
        if candidates:
            if len(candidates) > 1 and allow_ambiguous:
                value = " | ".join(predictions[index].text.strip() for index in candidates)
                return make_field_evidence(
                    field_name, list(predictions), tuple(candidates), value,
                    status="ambiguous", reason="multiple deterministic candidates",
                )
            index = candidates[0]
            return make_field_evidence(
                field_name, list(predictions), (index,), predictions[index].text.strip()
            )
    return missing_field(field_name, "label and compatible neighboring value not found")


def _table_evidence(
    field_name: str,
    predictions: Sequence[OCRPrediction],
    header_aliases: Sequence[str],
    matcher: Callable[[str], bool],
    *,
    stop_aliases: Sequence[str] = (),
) -> FieldEvidence:
    headers = _label_indices(predictions, header_aliases)
    if not headers:
        return missing_field(field_name, "table header not found")
    ordered_indices = _visual_order_indices(predictions)
    header_position = min(ordered_indices.index(index) for index in headers)
    header_bottom = max(max(predictions[index].y) for index in headers)
    table_indices = [
        index for index in ordered_indices[header_position + 1:]
        if min(predictions[index].y) > header_bottom
    ]
    for position, index in enumerate(table_indices):
        if _has_alias(predictions[index].text, stop_aliases):
            table_indices = table_indices[:position]
            break
    indices = tuple(index for index in table_indices if matcher(predictions[index].text))
    if not indices:
        return missing_field(field_name, "no deterministic table value found")
    value = " | ".join(predictions[index].text.strip() for index in indices)
    return make_field_evidence(field_name, list(predictions), indices, value)


def _party_value(text: str) -> bool:
    normalized = _normalized(text)
    if not any(character.isalpha() for character in text):
        return False
    if normalized in _CONTROL_WORDS or normalized.endswith(":"):
        return False
    if re.search(r"\b(?:tel|fax|reg|no|negotiable|multimodal|transport)\b|\d{3,}", normalized):
        return False
    return True


def _description_value(text: str) -> bool:
    normalized = _normalized(text).strip(" :")
    if not any(character.isalpha() for character in text):
        return False
    if (
        DATE_PATTERN.search(text)
        or MONEY_PATTERN.match(text)
        or WEIGHT_PATTERN.search(text)
        or PACKAGE_PATTERN.search(text)
        or any(word in normalized for word in ("cbm", "pkgs", "marks and no", "container"))
    ):
        return False
    if normalized in _CONTROL_WORDS or normalized in {"pkg", "pcs", "ct", "st", "cbm", "bag", "inch", "pound", "(kgs)", "kgs"}:
        return False
    if re.fullmatch(r"[A-Z0-9-]+", text.strip(), re.IGNORECASE) and any(
        character.isdigit() for character in text
    ):
        return False
    if any(
        phrase in normalized
        for phrase in ("q'ty", "hs code", "unit price", "shipping mark", "po no")
    ):
        return False
    return True


def _identifier_value(text: str) -> bool:
    normalized = _normalized(text)
    return bool(ID_PATTERN.fullmatch(text.strip())) and normalized not in {"and", "date", "no", "number"}


def _first_found(*evidence: FieldEvidence) -> FieldEvidence:
    for candidate in evidence:
        if candidate.status != "missing":
            return candidate
    return evidence[-1]


def _invoice_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    fields = {
        "invoice_no": _embedded(
            "invoice_no", predictions,
            [re.compile(r"invoice\s*(?:no\.?|number)\s*[:#]?\s*(?!and\b|date\b)(?P<value>[A-Z0-9][A-Z0-9./-]*)", re.I)],
        )
        or _labeled_value("invoice_no", predictions, ("invoice no", "invoice number"), _identifier_value),
        "date": _embedded(
            "date", predictions,
            [re.compile(r"(?:date|invoice\s+date)\s*[:#-]?\s*(?P<value>" + DATE_PATTERN.pattern + r")", re.I)],
        )
        or _labeled_value("date", predictions, ("invoice no", "invoice number", "invoice date"), DATE_PATTERN),
        "buyer": _embedded(
            "buyer", predictions,
            [re.compile(r"(?:buyer|sold\s+to)\s*:\s*(?P<value>.+)", re.I)],
        ) or _labeled_value("buyer", predictions, ("buyer", "sold to"), _party_value),
        "amount": _first_found(
            _labeled_value("amount", predictions, ("total",), MONEY_PATTERN),
            _labeled_value("amount", predictions, ("amount",), MONEY_PATTERN),
        ),
        "currency": None,
    }
    fields["goods_description"] = _table_evidence(
        "goods_description", predictions, ("description of good", "description of goods"),
        _description_value, stop_aliases=("total", "remark", "signature"),
    )
    fields["quantity"] = _table_evidence(
        "quantity", predictions, ("q'ty", "qty", "quantity"),
        INTEGER_PATTERN.search, stop_aliases=("total",),
    )
    currency_codes = [
        index for index, prediction in enumerate(predictions)
        if re.fullmatch(r"USD|EUR|GBP|CAD|AUD|JPY|CNY|KRW", prediction.text.strip(), re.I)
    ]
    if currency_codes:
        fields["currency"] = make_field_evidence(
            "currency", list(predictions), (currency_codes[0],), predictions[currency_codes[0]].text.strip()
        )
    else:
        symbols = [
            index for index, prediction in enumerate(predictions)
            if re.search(r"[$€£]", prediction.text)
        ]
        if fields["amount"].source_indices:
            amount_symbols = [
                index for index in fields["amount"].source_indices
                if re.search(r"[$€£]", predictions[index].text)
            ]
            if amount_symbols:
                symbols = amount_symbols
        fields["currency"] = (
            make_field_evidence("currency", list(predictions), (symbols[0],), re.search(r"[$€£]", predictions[symbols[0]].text).group(), status="ambiguous", reason="currency symbol found but ISO code absent")
            if symbols else missing_field("currency", "currency code or symbol not found")
        )
    return fields


def _packing_list_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    return {
        "invoice_no": _embedded(
            "invoice_no", predictions,
            [re.compile(r"invoice\s*(?:no\.?|number)\s*[:#]?\s*(?P<value>[A-Z0-9][A-Z0-9./-]*)", re.I)],
        ) or _labeled_value("invoice_no", predictions, ("invoice no", "invoice number"), _identifier_value),
        "goods_description": _table_evidence(
            "goods_description", predictions, ("description of goods",),
            _description_value, stop_aliases=("signed by", "total",),
        ),
        "quantity": _table_evidence(
            "quantity", predictions, ("quantity",), INTEGER_PATTERN.search, stop_aliases=("signed by",),
        ),
        "number_of_packages": _embedded(
            "number_of_packages", predictions,
            [re.compile(r"number\s+of\s+packages\s*[:#]?\s*(?P<value>\d[\d,.]*\s*[A-Z]+)", re.I)],
        ) or missing_field("number_of_packages", "package total label not found"),
        "gross_weight": _embedded(
            "gross_weight", predictions,
            [re.compile(r"total\s+gross\s+weight\s*[:#]?\s*(?P<value>\d[\d,.]*\s*(?:KG|KGS|LB|LBS|POUND|POUNDS))", re.I)],
        ) or _labeled_value("gross_weight", predictions, ("gross weight",), WEIGHT_PATTERN),
    }


def _bill_of_lading_fields(predictions: Sequence[OCRPrediction]) -> dict[str, FieldEvidence]:
    return {
        "bl_no": _embedded(
            "bl_no", predictions,
            [re.compile(r"b\s*/\s*l\s*(?:no\.?|number)?\s*[:#]?\s*(?P<value>[A-Z0-9][A-Z0-9./-]*)", re.I)],
        ) or _labeled_value("bl_no", predictions, ("b/l no", "bill of lading no"), ID_PATTERN),
        "shipper": _labeled_value("shipper", predictions, ("consignor/shipper", "shipper"), _party_value),
        "consignee": _labeled_value("consignee", predictions, ("consignee",), _party_value),
        "goods_description": _table_evidence(
            "goods_description", predictions, ("description of goods",),
            _description_value, stop_aliases=("total", "freight",),
        ),
        "number_of_packages": _embedded(
            "number_of_packages", predictions,
            [re.compile(r"say\s*:\s*(?P<value>\d[\d,.]*\s*[A-Z]+)", re.I)],
        ) or _table_evidence(
            "number_of_packages", predictions, ("no. & kinds", "pkgs"),
            lambda text: bool(PACKAGE_PATTERN.search(text)), stop_aliases=("total",),
        ),
        "gross_weight": _first_found(
            _labeled_value("gross_weight", predictions, ("total",), WEIGHT_PATTERN),
            _labeled_value("gross_weight", predictions, ("gross weight",), WEIGHT_PATTERN),
        ),
        "on_board_date": _labeled_value(
            "on_board_date", predictions, ("laden on board", "on board"), DATE_PATTERN,
        ),
    }


def extract_fields(
    form_type: str, predictions: Sequence[OCRPrediction]
) -> dict[str, FieldEvidence]:
    """Extract only the current MVP fields for one Fintra target form type."""
    if form_type == "상업송장":
        return _invoice_fields(predictions)
    if form_type == "포장명세서":
        return _packing_list_fields(predictions)
    if form_type == "선하증권":
        return _bill_of_lading_fields(predictions)
    raise ValueError(f"Unsupported Fintra form type: {form_type!r}")
