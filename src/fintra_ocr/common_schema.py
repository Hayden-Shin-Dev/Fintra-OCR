"""Common JSON contract for Fintra OCR field evidence."""

from collections.abc import Mapping
import json
from numbers import Integral, Real
from typing import Literal

from .field_evidence import FieldEvidence


SchemaDocumentType = Literal[
    "commercial_invoice", "packing_list", "bill_of_lading"
]
ProcessingStatus = Literal["success", "partial", "failed"]

SCHEMA_VERSION = "1.0"

_FORM_TYPE_TO_DOCUMENT_TYPE: dict[str, SchemaDocumentType] = {
    "\uc0c1\uc5c5\uc1a1\uc7a5": "commercial_invoice",
    "\ud3ec\uc7a5\uba85\uc138\uc11c": "packing_list",
    "\uc120\ud558\uc99d\uad8c": "bill_of_lading",
}
DOCUMENT_FIELD_KEYS: dict[SchemaDocumentType, frozenset[str]] = {
    "commercial_invoice": frozenset(
        {"invoice_no", "date", "buyer", "seller", "goods_description", "quantity", "amount", "currency"}
    ),
    "packing_list": frozenset(
        {"invoice_no", "goods_description", "quantity", "number_of_packages", "gross_weight"}
    ),
    "bill_of_lading": frozenset(
        {"bl_no", "shipper", "consignee", "goods_description", "number_of_packages", "gross_weight", "on_board_date"}
    ),
}

_FIELD_KEYS = (
    "value",
    "normalized",
    "raw_text",
    "bbox",
    "confidence",
    "status",
    "source_indices",
    "reason",
    "normalization_status",
    "normalization_reason",
)
_FIELD_STATUSES = {"found", "missing", "ambiguous"}
_NORMALIZATION_STATUSES = {
    "not_processed", "normalized", "unchanged", "ambiguous", "failed"
}
_PROCESSING_STATUSES = {"success", "partial", "failed"}


def document_type_from_form_type(form_type: str) -> SchemaDocumentType:
    """Convert the dataset's actual Korean form type to the public type."""
    try:
        return _FORM_TYPE_TO_DOCUMENT_TYPE[form_type]
    except KeyError as error:
        raise ValueError(f"Unsupported Fintra form type: {form_type!r}") from error


def _bbox_to_json(bbox: object) -> list[list[int]] | None:
    if bbox is None:
        return None
    return [[int(x), int(y)] for x, y in bbox]  # type: ignore[misc]


def _field_to_json(field: FieldEvidence) -> dict[str, object]:
    """Serialize one FieldEvidence without dropping source or normalization data."""
    return {
        "value": field.value,
        "normalized": field.normalized,
        "raw_text": field.raw_text,
        "bbox": _bbox_to_json(field.bbox),
        "confidence": field.confidence,
        "status": field.status,
        "source_indices": list(field.source_indices),
        "reason": field.reason,
        "normalization_status": field.normalization_status,
        "normalization_reason": field.normalization_reason,
    }


def _processing_status(fields: Mapping[str, FieldEvidence]) -> ProcessingStatus:
    if not fields or all(field.status == "missing" for field in fields.values()):
        return "failed"
    if any(
        field.status != "found" or field.normalization_status == "failed"
        for field in fields.values()
    ):
        return "partial"
    return "success"


def build_common_document(
    document_type: SchemaDocumentType,
    document_id: str,
    fields: Mapping[str, FieldEvidence],
) -> dict[str, object]:
    """Build the public document JSON from the current extracted field mapping."""
    if document_type not in DOCUMENT_FIELD_KEYS:
        raise ValueError(f"Unsupported document type: {document_type!r}")
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be a non-empty string")
    unknown_fields = set(fields) - DOCUMENT_FIELD_KEYS[document_type]
    if unknown_fields:
        raise ValueError(
            f"Unsupported fields for {document_type}: {sorted(unknown_fields)!r}"
        )
    if any(field_name != field.field_name for field_name, field in fields.items()):
        raise ValueError("field mapping key must match FieldEvidence.field_name")

    document = {
        "schema_version": SCHEMA_VERSION,
        "document_type": document_type,
        "document_id": document_id.strip(),
        "processing_status": _processing_status(fields),
        "fields": {
            field_name: _field_to_json(field)
            for field_name, field in fields.items()
        },
    }
    validate_common_document(document)
    return document


def build_common_document_from_form_type(
    form_type: str,
    document_id: str,
    fields: Mapping[str, FieldEvidence],
) -> dict[str, object]:
    """Build the public document JSON from the dataset form type."""
    return build_common_document(
        document_type_from_form_type(form_type), document_id, fields
    )


def _validate_bbox(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("field bbox must be null or a four-point list")
    for point in value:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(coordinate, Integral) for coordinate in point)
        ):
            raise ValueError("field bbox points must contain two integers")


def validate_common_document(document: Mapping[str, object]) -> None:
    """Validate the JSON-compatible public contract and its field evidence."""
    required = {
        "schema_version", "document_type", "document_id",
        "processing_status", "fields",
    }
    if set(document) != required:
        raise ValueError("document keys do not match the common schema")
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    document_type = document["document_type"]
    if document_type not in DOCUMENT_FIELD_KEYS:
        raise ValueError("unsupported document_type")
    if not isinstance(document["document_id"], str) or not document["document_id"]:
        raise ValueError("document_id must be a non-empty string")
    if document["processing_status"] not in _PROCESSING_STATUSES:
        raise ValueError("unsupported processing_status")
    fields = document["fields"]
    if not isinstance(fields, Mapping):
        raise ValueError("fields must be an object")
    if not set(fields).issubset(DOCUMENT_FIELD_KEYS[document_type]):
        raise ValueError("fields contain keys outside the document type contract")

    for field_name, field in fields.items():
        if not isinstance(field_name, str) or not isinstance(field, Mapping):
            raise ValueError("each field must be an object keyed by a string")
        if set(field) != set(_FIELD_KEYS):
            raise ValueError(f"field {field_name!r} keys do not match the contract")
        if field["value"] is not None and not isinstance(field["value"], str):
            raise ValueError(f"field {field_name!r} value must be string or null")
        if not isinstance(field["raw_text"], str):
            raise ValueError(f"field {field_name!r} raw_text must be a string")
        confidence = field["confidence"]
        if (
            not isinstance(confidence, Real)
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ValueError(f"field {field_name!r} confidence must be between 0 and 1")
        _validate_bbox(field["bbox"])
        source_indices = field["source_indices"]
        if (
            not isinstance(source_indices, list)
            or not all(isinstance(index, Integral) and index >= 0 for index in source_indices)
        ):
            raise ValueError(f"field {field_name!r} source_indices must be non-negative integers")
        if field["status"] not in _FIELD_STATUSES:
            raise ValueError(f"field {field_name!r} has an unsupported status")
        if field["normalization_status"] not in _NORMALIZATION_STATUSES:
            raise ValueError(f"field {field_name!r} has an unsupported normalization status")
        for reason_key in ("reason", "normalization_reason"):
            if field[reason_key] is not None and not isinstance(field[reason_key], str):
                raise ValueError(f"field {field_name!r} {reason_key} must be string or null")
        try:
            json.dumps(field["normalized"])
        except TypeError as error:
            raise ValueError(f"field {field_name!r} normalized value is not JSON-compatible") from error
