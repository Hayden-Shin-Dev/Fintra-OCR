"""Deterministic normalization of the current MVP field evidence."""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata
from collections.abc import Mapping

from .field_evidence import FieldEvidence


_DATE_FORMATS = (
    "%d-%b-%Y", "%d-%B-%Y", "%b %d, %Y", "%B %d, %Y",
    "%b %d %Y", "%B %d %Y", "%d/%m/%Y", "%m/%d/%Y",
)
_NUMBER_PATTERN = re.compile(r"^\s*([+-]?\d[\d,]*(?:\.\d+)?)")
_WEIGHT_PATTERN = re.compile(
    r"^\s*([+-]?\d[\d,]*(?:\.\d+)?)\s*(KG|KGS|LB|LBS|POUND|POUNDS)\s*$",
    re.IGNORECASE,
)
_PACKAGE_PATTERN = re.compile(
    r"^\s*([+-]?\d[\d,]*(?:\.\d+)?)\s*(PKG|PCS?|CTN?|CT|ST|BOX|BAG|BUNDLES?)\s*$",
    re.IGNORECASE,
)
_CURRENCY_SYMBOLS = re.compile(r"[$€£]")

_DATE_FIELDS = {"date", "on_board_date"}
_AMOUNT_FIELDS = {"amount"}
_CURRENCY_FIELDS = {"currency"}
_QUANTITY_FIELDS = {"quantity"}
_WEIGHT_FIELDS = {"gross_weight"}
_PACKAGE_FIELDS = {"number_of_packages"}
_STRING_FIELDS = {
    "invoice_no", "bl_no", "buyer", "shipper", "consignee", "goods_description",
}
_SUPPORTED_FIELDS = (
    _DATE_FIELDS | _AMOUNT_FIELDS | _CURRENCY_FIELDS | _QUANTITY_FIELDS
    | _WEIGHT_FIELDS | _PACKAGE_FIELDS | _STRING_FIELDS
)


def _clean_string(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _failed(evidence: FieldEvidence, reason: str) -> FieldEvidence:
    return replace(
        evidence,
        normalized=None,
        normalization_status="failed",
        normalization_reason=reason,
    )


def _successful(
    evidence: FieldEvidence, normalized: object, *, ambiguous: bool = False,
    reason: str | None = None,
) -> FieldEvidence:
    return replace(
        evidence,
        normalized=normalized,
        normalization_status="ambiguous" if ambiguous else "normalized",
        normalization_reason=reason,
    )


def _normalize_date(evidence: FieldEvidence) -> FieldEvidence:
    value = _clean_string(evidence.value or "")
    for date_format in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, date_format)
        except ValueError:
            continue
        return _successful(evidence, parsed.date().isoformat())
    return _failed(evidence, "date format is not supported")


def _parse_decimal(value: str) -> Decimal | None:
    match = _NUMBER_PATTERN.match(value)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def _number_value(number: Decimal) -> int | float:
    return int(number) if number == number.to_integral_value() else float(number)


def _normalize_amount(evidence: FieldEvidence) -> FieldEvidence:
    raw_value = evidence.value or ""
    number_text = _CURRENCY_SYMBOLS.sub("", raw_value, count=1)
    number = _parse_decimal(number_text)
    if number is None:
        return _failed(evidence, "amount does not contain a parseable number")
    symbol_match = _CURRENCY_SYMBOLS.search(evidence.value or "")
    return _successful(
        evidence,
        {
            "value": float(number),
            "symbol": symbol_match.group() if symbol_match else None,
            "currency_code": None,
        },
    )


def _normalize_currency(evidence: FieldEvidence) -> FieldEvidence:
    value = _clean_string(evidence.value or "")
    if re.fullmatch(r"[A-Z]{3}", value, re.IGNORECASE):
        return _successful(evidence, {"code": value.upper(), "symbol": None})
    symbol_match = _CURRENCY_SYMBOLS.search(value)
    if symbol_match:
        return _successful(
            evidence,
            {"code": None, "symbol": symbol_match.group()},
            ambiguous=True,
            reason="currency symbol does not identify an ISO currency code",
        )
    return _failed(evidence, "currency code or symbol is not parseable")


def _normalize_quantity(evidence: FieldEvidence) -> FieldEvidence:
    raw_items = [item.strip() for item in (evidence.value or "").split("|")]
    if not raw_items or any(not item for item in raw_items):
        return _failed(evidence, "quantity item separator contains an empty value")
    items: list[dict[str, object | None]] = []
    for item in raw_items:
        number = _parse_decimal(item)
        if number is None:
            return _failed(evidence, "quantity item does not contain a parseable number")
        unit_match = re.match(r"^\s*[+-]?\d[\d,]*(?:\.\d+)?\s*([A-Za-z]+)?\s*$", item)
        unit = unit_match.group(1).upper() if unit_match and unit_match.group(1) else None
        items.append({"value": _number_value(number), "unit": unit})
    return _successful(evidence, {"items": items})


def _normalize_measurement(evidence: FieldEvidence) -> FieldEvidence:
    match = _WEIGHT_PATTERN.fullmatch(evidence.value or "")
    if not match:
        return _failed(evidence, "weight does not contain a supported number and unit")
    number = _parse_decimal(match.group(1))
    if number is None:
        return _failed(evidence, "weight number is not parseable")
    unit = match.group(2).upper()
    unit = {"KGS": "KG", "LBS": "LB", "POUND": "LB", "POUNDS": "LB"}.get(unit, unit)
    return _successful(evidence, {"value": _number_value(number), "unit": unit})


def _normalize_package_count(evidence: FieldEvidence) -> FieldEvidence:
    match = _PACKAGE_PATTERN.fullmatch(evidence.value or "")
    if not match:
        return _failed(evidence, "package count does not contain a supported number and unit")
    number = _parse_decimal(match.group(1))
    if number is None:
        return _failed(evidence, "package count number is not parseable")
    return _successful(
        evidence,
        {"value": _number_value(number), "unit": match.group(2).upper()},
    )


def _normalize_string(evidence: FieldEvidence) -> FieldEvidence:
    value = _clean_string(evidence.value or "")
    if not value:
        return _failed(evidence, "string value is empty")
    return _successful(
        evidence,
        value,
        ambiguous=evidence.status == "ambiguous",
        reason="source field remains ambiguous" if evidence.status == "ambiguous" else None,
    )


def normalize_field(field_name: str, evidence: FieldEvidence) -> FieldEvidence:
    """Add a normalized value without changing source evidence or source status."""
    if field_name not in _SUPPORTED_FIELDS:
        raise ValueError(f"Unsupported normalization field: {field_name!r}")
    if evidence.status == "missing":
        return _failed(evidence, "source field is missing")
    if field_name in _DATE_FIELDS:
        return _normalize_date(evidence)
    if field_name in _AMOUNT_FIELDS:
        return _normalize_amount(evidence)
    if field_name in _CURRENCY_FIELDS:
        return _normalize_currency(evidence)
    if field_name in _QUANTITY_FIELDS:
        return _normalize_quantity(evidence)
    if field_name in _WEIGHT_FIELDS:
        return _normalize_measurement(evidence)
    if field_name in _PACKAGE_FIELDS:
        return _normalize_package_count(evidence)
    return _normalize_string(evidence)


def normalize_fields(
    fields: Mapping[str, FieldEvidence],
) -> dict[str, FieldEvidence]:
    """Normalize the existing field mapping without adding or removing fields."""
    return {
        field_name: normalize_field(field_name, evidence)
        for field_name, evidence in fields.items()
    }
