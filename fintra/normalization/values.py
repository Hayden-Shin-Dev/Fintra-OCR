"""Conservative value normalization for cross-document comparison."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


def _text(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value)).strip()


def normalize_company(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = _text(value).upper()
    text = re.sub(r"[.,;:/\\()\[\]{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_currency(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = _text(value).upper()
    codes = {"USD", "EUR", "GBP", "JPY", "CNY", "KRW", "HKD", "SGD", "AUD", "CAD"}
    found = re.findall(r"\b[A-Z]{3}\b", text)
    if found and found[0] in codes:
        return found[0]
    symbols = {"$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₩": "KRW"}
    for symbol, code in symbols.items():
        if symbol in text:
            return code
    return None


def parse_amount(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    text = _text(value).replace(" ", "")
    text = re.sub(r"[^0-9,().+-]", "", text)
    if not re.search(r"\d", text):
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        pieces = text.split(",")
        text = "".join(pieces) if len(pieces[-1]) == 3 else ".".join(pieces)
    try:
        result = Decimal(text)
    except InvalidOperation:
        return None
    return -result if negative else result


def normalize_quantity(value: Any, unit: Any = None) -> tuple[Decimal, str | None] | None:
    amount = parse_amount(value)
    if amount is None:
        return None
    normalized_unit = _text(unit).upper() if unit not in (None, "") else None
    return amount, normalized_unit


def normalize_weight(value: Any, unit: Any = None) -> tuple[Decimal, str | None] | None:
    parsed = normalize_quantity(value, unit)
    if parsed is None:
        return None
    amount, raw_unit = parsed
    aliases = {"KG": "KG", "KGS": "KG", "KILOGRAM": "KG", "KILOGRAMS": "KG", "G": "G", "GRAM": "G", "GRAMS": "G"}
    normalized_unit = aliases.get(raw_unit or "", raw_unit)
    if normalized_unit == "G":
        return amount / Decimal(1000), "KG"
    return amount, normalized_unit


def normalize_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = _text(value)
    # Explicit English month names are unambiguous and locale independent.
    months = {name: i for i, name in enumerate(
        ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'), 1)}
    year_first = re.fullmatch(r'(\d{4})[\s-]+([A-Za-z]{3,9})[\s,-]+(\d{1,2})', text)
    named = re.fullmatch(r'(\d{1,2})[\s-]+([A-Za-z]{3,9})[\s,-]+(\d{4})', text)
    month_first = re.fullmatch(r'([A-Za-z]{3,9})[\s-]+(\d{1,2})[\s,-]+(\d{4})', text)
    if year_first or named or month_first:
        day, month_name, year = (year_first[3], year_first[2], year_first[1]) if year_first else named.groups() if named else (month_first[2], month_first[1], month_first[3])
        full_names = ('JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER')
        if month_name.upper() not in set(months) | set(full_names):
            return None
        try:
            return date(int(year), months[month_name[:3].upper()], int(day)).isoformat()
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", text)
    if match:
        # DD/MM and MM/DD cannot be safely inferred when both components <= 12.
        first, second, year = map(int, match.groups())
        if first <= 12 and second <= 12:
            return None
        day, month = (first, second) if first > 12 else (second, first)
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def compare_values(left: Any, right: Any, *, kind: str = "text", tolerance: Decimal | None = None) -> tuple[str, Any]:
    """Return ``match``, ``mismatch``, or ``insufficient_evidence`` plus diff."""

    if left in (None, "") or right in (None, ""):
        return "insufficient_evidence", None
    if kind == "amount":
        lvalue, rvalue = parse_amount(left), parse_amount(right)
        if lvalue is None or rvalue is None:
            return "insufficient_evidence", None
        difference = lvalue - rvalue
        return ("match" if abs(difference) <= (tolerance or Decimal("0.01")) else "mismatch", str(difference))
    if kind == "company":
        left, right = normalize_company(left), normalize_company(right)
    elif kind == "currency":
        left, right = normalize_currency(left), normalize_currency(right)
    elif kind == "date":
        left, right = normalize_date(left), normalize_date(right)
    else:
        left, right = _text(left).casefold(), _text(right).casefold()
    if left is None or right is None:
        return "insufficient_evidence", None
    return ("match" if left == right else "mismatch", None)
