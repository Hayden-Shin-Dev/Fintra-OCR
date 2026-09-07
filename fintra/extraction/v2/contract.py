"""Stable Audit Field Schema v2 document contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fintra.ocr.adapter import OCRResult

from .specs import DOCUMENT_FIELDS, ITEM_FIELDS


def _missing(method: str = "v2_contract_missing") -> dict[str, Any]:
    return {
        "value": None,
        "normalized_value": None,
        "confidence": None,
        "source_text": None,
        "source_label": None,
        "bbox": None,
        "page": None,
        "extraction_method": method,
        "status": "missing",
    }


@dataclass(frozen=True)
class V2Document:
    document_type: str
    document_id: str
    source_file: str
    fields: dict[str, Any]
    items: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fintra-audit-field-schema-v2",
            "document_type": self.document_type,
            "metadata": self.metadata,
            **self.fields,
            "items": self.items,
        }


def _field(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else _missing()


def build_document(result: OCRResult, payload: dict[str, Any]) -> V2Document:
    """Project a baseline/overlay payload into the stable v2 contract.

    Existing baseline fields are preserved verbatim.  Only missing contract
    keys are added as nullable evidence, so compatibility fields cannot be
    accidentally renamed or dropped.
    """

    document_type = result.document_type
    metadata = dict(payload.get("metadata") or {})
    metadata.setdefault("document_id", result.document_id)
    metadata.setdefault("document_type", document_type)
    metadata.setdefault("source_file", result.source_file)
    metadata.setdefault("extraction_status", "extracted")

    fields = {
        key: value
        for key, value in payload.items()
        if key not in {"schema_version", "document_type", "metadata", "items"}
    }
    for name in DOCUMENT_FIELDS[document_type]:
        fields.setdefault(name, _missing())

    raw_items = payload.get("items") or []
    items: list[dict[str, Any]] = []
    for raw_item in raw_items:
        item = dict(raw_item) if isinstance(raw_item, dict) else {}
        for name in ITEM_FIELDS.get(document_type, ()):
            item.setdefault(name, _missing("v2_item_contract_missing"))
        items.append(item)

    return V2Document(document_type, result.document_id, result.source_file, fields, items, metadata)


__all__ = ["V2Document", "build_document"]
