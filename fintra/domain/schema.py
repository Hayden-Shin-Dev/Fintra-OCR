"""Small, dependency-free canonical schema for the Fintra MVP.

The schema deliberately keeps source evidence beside every extracted value.
Missing fields are represented explicitly instead of being guessed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping


class ExtractionStatus(str, Enum):
    EXTRACTED = "extracted"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


class ValidationStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    REVIEW_REQUIRED = "review_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class EvidenceField:
    value: Any = None
    normalized_value: Any = None
    confidence: float | None = None
    source_text: str | None = None
    bbox: list[list[float]] | None = None
    page: int | None = None
    extraction_method: str = "deterministic_rule"
    status: ExtractionStatus = ExtractionStatus.MISSING

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status == ExtractionStatus.EXTRACTED and self.value in (None, ""):
            raise ValueError("extracted evidence must contain a value")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DocumentMetadata:
    document_id: str
    document_type: str
    source_file: str | None = None
    transaction_id: str | None = None
    extraction_status: ExtractionStatus = ExtractionStatus.MISSING
    page_count: int | None = None

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id is required")
        if not self.document_type.strip():
            raise ValueError("document_type is required")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class LineItem:
    description: EvidenceField = field(default_factory=EvidenceField)
    quantity: EvidenceField = field(default_factory=EvidenceField)
    unit: EvidenceField = field(default_factory=EvidenceField)
    unit_price: EvidenceField = field(default_factory=EvidenceField)
    amount: EvidenceField = field(default_factory=EvidenceField)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class CommercialInvoice:
    metadata: DocumentMetadata
    invoice_number: EvidenceField = field(default_factory=EvidenceField)
    invoice_date: EvidenceField = field(default_factory=EvidenceField)
    seller: EvidenceField = field(default_factory=EvidenceField)
    buyer: EvidenceField = field(default_factory=EvidenceField)
    currency: EvidenceField = field(default_factory=EvidenceField)
    total_amount: EvidenceField = field(default_factory=EvidenceField)
    items: list[LineItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class PackingList:
    metadata: DocumentMetadata
    packing_list_number: EvidenceField = field(default_factory=EvidenceField)
    date: EvidenceField = field(default_factory=EvidenceField)
    exporter: EvidenceField = field(default_factory=EvidenceField)
    consignee: EvidenceField = field(default_factory=EvidenceField)
    items: list[LineItem] = field(default_factory=list)
    package_count: EvidenceField = field(default_factory=EvidenceField)
    gross_weight: EvidenceField = field(default_factory=EvidenceField)
    net_weight: EvidenceField = field(default_factory=EvidenceField)
    weight_unit: EvidenceField = field(default_factory=EvidenceField)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class BillOfLading:
    metadata: DocumentMetadata
    bl_number: EvidenceField = field(default_factory=EvidenceField)
    shipper: EvidenceField = field(default_factory=EvidenceField)
    consignee: EvidenceField = field(default_factory=EvidenceField)
    notify_party: EvidenceField = field(default_factory=EvidenceField)
    vessel: EvidenceField = field(default_factory=EvidenceField)
    port_of_loading: EvidenceField = field(default_factory=EvidenceField)
    port_of_discharge: EvidenceField = field(default_factory=EvidenceField)
    shipment_date: EvidenceField = field(default_factory=EvidenceField)
    package_count: EvidenceField = field(default_factory=EvidenceField)
    gross_weight: EvidenceField = field(default_factory=EvidenceField)
    weight_unit: EvidenceField = field(default_factory=EvidenceField)
    goods_description: EvidenceField = field(default_factory=EvidenceField)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class LedgerTransaction:
    transaction_id: str
    transaction_date: EvidenceField = field(default_factory=EvidenceField)
    recognition_date: EvidenceField = field(default_factory=EvidenceField)
    account: EvidenceField = field(default_factory=EvidenceField)
    counterparty: EvidenceField = field(default_factory=EvidenceField)
    currency: EvidenceField = field(default_factory=EvidenceField)
    amount: EvidenceField = field(default_factory=EvidenceField)
    direction: EvidenceField = field(default_factory=EvidenceField)

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id is required")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class ValidationFinding:
    rule_id: str
    title: str
    status: ValidationStatus
    severity: Severity
    left_document: str | None = None
    left_field: str | None = None
    left_value: Any = None
    right_document: str | None = None
    right_field: str | None = None
    right_value: Any = None
    difference: Any = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class TransactionReview:
    ledger_transaction: LedgerTransaction
    commercial_invoice: CommercialInvoice | None = None
    packing_list: PackingList | None = None
    bill_of_lading: BillOfLading | None = None
    validation_results: list[ValidationFinding] = field(default_factory=list)
    overall_review_status: str = "INCOMPLETE"
    evidence_summary: list[str] = field(default_factory=list)
    accounting_references: list[dict[str, Any]] = field(default_factory=list)
    ai_review: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def evidence(
    value: Any,
    *,
    source_text: str | None = None,
    bbox: list[list[float]] | None = None,
    confidence: float | None = None,
    normalized_value: Any = None,
    method: str = "deterministic_rule",
) -> EvidenceField:
    """Create extracted evidence while keeping an explicit trace to OCR."""

    if value in (None, ""):
        return EvidenceField(status=ExtractionStatus.MISSING, extraction_method=method)
    return EvidenceField(
        value=value,
        normalized_value=normalized_value,
        confidence=confidence,
        source_text=source_text,
        bbox=bbox,
        extraction_method=method,
        status=ExtractionStatus.EXTRACTED,
    )


def ambiguous(*, source_text: str | None = None, method: str = "deterministic_rule") -> EvidenceField:
    return EvidenceField(
        source_text=source_text,
        extraction_method=method,
        status=ExtractionStatus.AMBIGUOUS,
    )


def missing(method: str = "deterministic_rule") -> EvidenceField:
    return EvidenceField(extraction_method=method, status=ExtractionStatus.MISSING)


def decimal_value(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def document_from_dict(payload: Mapping[str, Any]) -> Any:
    """Deserialize the common JSON shape used by fixtures and persistence."""

    kind = payload.get("document_type") or payload.get("metadata", {}).get("document_type")
    metadata_payload = payload.get("metadata", {})
    metadata = DocumentMetadata(**metadata_payload)
    field_names = {
        "Commercial Invoice": CommercialInvoice,
        "Packing List": PackingList,
        "B/L": BillOfLading,
    }
    cls = field_names.get(kind)
    if cls is None:
        raise ValueError(f"unsupported document_type: {kind}")
    values = {key: value for key, value in payload.items() if key not in {"metadata", "document_type"}}
    values = {key: EvidenceField(**value) if isinstance(value, dict) and "status" in value else value for key, value in values.items()}
    return cls(metadata=metadata, **values)
