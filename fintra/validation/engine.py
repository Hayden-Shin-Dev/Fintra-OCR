"""Deterministic cross-document validation rules."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from fintra.domain.schema import (
    BillOfLading,
    CommercialInvoice,
    EvidenceField,
    LedgerTransaction,
    PackingList,
    Severity,
    ValidationFinding,
    ValidationStatus,
)
from fintra.normalization.values import compare_values, normalize_weight, parse_amount


def _field_state(field: EvidenceField) -> str:
    value = getattr(field.status, "value", field.status)
    return str(value)


def _value(field: EvidenceField) -> Any:
    return field.value if _field_state(field) == "extracted" else None


def _finding(
    rule_id: str,
    title: str,
    left_document: str,
    left_field: str,
    left: EvidenceField,
    right_document: str,
    right_field: str,
    right: EvidenceField,
    *,
    kind: str = "text",
    severity: Severity = Severity.WARNING,
    tolerance: Decimal | None = None,
) -> ValidationFinding:
    if _field_state(left) == "ambiguous" or _field_state(right) == "ambiguous":
        status, difference = "review_required", None
    else:
        status, difference = compare_values(_value(left), _value(right), kind=kind, tolerance=tolerance)
    status_enum = ValidationStatus(status)
    severity = Severity.INFO if status_enum == ValidationStatus.MATCH else severity
    message = {
        "match": "Values match after conservative normalization.",
        "mismatch": "Values differ and require review.",
        "review_required": "At least one source value is ambiguous.",
        "insufficient_evidence": "One or both source values are missing or unparseable.",
    }[status]
    return ValidationFinding(
        rule_id=rule_id,
        title=title,
        status=status_enum,
        severity=severity,
        left_document=left_document,
        left_field=left_field,
        left_value=_value(left),
        right_document=right_document,
        right_field=right_field,
        right_value=_value(right),
        difference=difference,
        evidence=[item for item in (left.to_dict(), right.to_dict()) if item.get("status") == "extracted"],
        message=message,
    )


def _weight_finding(
    rule_id: str,
    title: str,
    left_document: str,
    left_value: EvidenceField,
    left_unit: EvidenceField,
    right_document: str,
    right_value: EvidenceField,
    right_unit: EvidenceField,
) -> ValidationFinding:
    left_weight = normalize_weight(_value(left_value), _value(left_unit))
    right_weight = normalize_weight(_value(right_value), _value(right_unit))
    if _field_state(left_value) == "ambiguous" or _field_state(right_value) == "ambiguous":
        status, difference = ValidationStatus.REVIEW_REQUIRED, None
    elif left_weight is None or right_weight is None or left_weight[1] != right_weight[1]:
        status, difference = ValidationStatus.INSUFFICIENT_EVIDENCE, None
    else:
        difference = str(left_weight[0] - right_weight[0])
        status = ValidationStatus.MATCH if abs(left_weight[0] - right_weight[0]) <= Decimal("0.01") else ValidationStatus.MISMATCH
    return ValidationFinding(
        rule_id=rule_id,
        title=title,
        status=status,
        severity=Severity.INFO if status == ValidationStatus.MATCH else Severity.WARNING,
        left_document=left_document,
        left_field="gross_weight",
        left_value=_value(left_value),
        right_document=right_document,
        right_field="gross_weight",
        right_value=_value(right_value),
        difference=difference,
        evidence=[item for item in (left_value.to_dict(), right_value.to_dict()) if item.get("status") == "extracted"],
        message="Gross weights match after unit normalization." if status == ValidationStatus.MATCH else "Gross weights need review.",
    )


def validate_transaction(
    ledger: LedgerTransaction,
    invoice: CommercialInvoice | None,
    packing: PackingList | None,
    bill_of_lading: BillOfLading | None,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if invoice is not None:
        findings.append(_finding(
            "LEDGER-INVOICE-AMOUNT", "Ledger amount vs invoice total", "ledger", "amount", ledger.amount,
            "commercial_invoice", "total_amount", invoice.total_amount, kind="amount", severity=Severity.ERROR,
        ))
        findings.append(_finding(
            "LEDGER-INVOICE-COUNTERPARTY", "Ledger counterparty vs invoice buyer", "ledger", "counterparty", ledger.counterparty,
            "commercial_invoice", "buyer", invoice.buyer, kind="company",
        ))
        if _value(ledger.direction) and str(_value(ledger.direction)).casefold() in {"purchase", "buy"}:
            findings.append(_finding(
                "LEDGER-INVOICE-SELLER", "Purchase counterparty vs invoice seller", "ledger", "counterparty", ledger.counterparty,
                "commercial_invoice", "seller", invoice.seller, kind="company",
            ))
    if invoice is not None and packing is not None:
        if invoice.items and packing.items:
            findings.append(_finding(
                "INVOICE-PACKING-QUANTITY", "Invoice item quantity vs packing quantity", "commercial_invoice", "items[0].quantity", invoice.items[0].quantity,
                "packing_list", "items[0].quantity", packing.items[0].quantity, kind="amount",
            ))
        else:
            findings.append(ValidationFinding(
                "INVOICE-PACKING-QUANTITY", "Invoice item quantity vs packing quantity",
                ValidationStatus.INSUFFICIENT_EVIDENCE, Severity.WARNING,
                message="Comparable item evidence is not available.",
            ))
    if packing is not None and bill_of_lading is not None:
        findings.append(_weight_finding(
            "PACKING-BL-GROSS-WEIGHT", "Packing gross weight vs B/L gross weight", "packing_list", packing.gross_weight,
            packing.weight_unit, "bill_of_lading", bill_of_lading.gross_weight, bill_of_lading.weight_unit,
        ))
        findings.append(_finding(
            "PACKING-BL-PACKAGE-COUNT", "Packing package count vs B/L package count", "packing_list", "package_count", packing.package_count,
            "bill_of_lading", "package_count", bill_of_lading.package_count, kind="amount",
        ))
        findings.append(_finding(
            "PARTY-CONSISTENCY", "Packing consignee vs B/L consignee", "packing_list", "consignee", packing.consignee,
            "bill_of_lading", "consignee", bill_of_lading.consignee, kind="company",
        ))
    if bill_of_lading is not None:
        findings.append(_finding(
            "RECOGNITION-SHIPMENT-DATE", "Recognition date vs shipment evidence", "ledger", "recognition_date", ledger.recognition_date,
            "bill_of_lading", "shipment_date", bill_of_lading.shipment_date, kind="date",
        ))
    return findings
