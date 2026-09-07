"""Stable Audit Field Schema v2 document contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fintra.ocr.adapter import OCRResult

from .specs import COMPATIBILITY_DOCUMENT_FIELDS, DOCUMENT_FIELDS, FIELD_FAMILY, ITEM_FIELDS


def _missing(method: str = "v2_contract_missing") -> dict[str, Any]:
    return {
        "value": None,
        "normalized_value": None,
        "confidence": None,
        "source_text": None,
        "source_label": None,
        "semantic_relation": None,
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


def _field(value: Any, *, default_method: str = "v2_contract_missing") -> dict[str, Any]:
    """Return one stable evidence slot without mutating the source payload.

    Production Clean predates the v2 provenance keys.  The adapter adds those
    keys here rather than changing the frozen production schema or extractor.
    A v2 candidate can provide its semantic label/relation in its diagnostic
    block; clean-baseline evidence is explicitly marked as such.
    """

    if not isinstance(value, dict):
        return _missing(default_method)
    field = dict(value)
    field.setdefault("value", None)
    field.setdefault("normalized_value", None)
    field.setdefault("confidence", None)
    field.setdefault("source_text", None)
    field.setdefault("source_label", None)
    field.setdefault("semantic_relation", None)
    field.setdefault("bbox", None)
    field.setdefault("page", None)
    field.setdefault("extraction_method", default_method)
    field.setdefault("status", "missing")

    candidate = field.get("candidate")
    if isinstance(candidate, dict):
        field["source_label"] = field.get("source_label") or candidate.get("semantic_anchor")
        field["semantic_relation"] = field.get("semantic_relation") or candidate.get("relation")
    if field.get("semantic_relation") is None and field.get("status") == "extracted":
        field["semantic_relation"] = "clean_baseline"
    return field


def build_document(result: OCRResult, payload: dict[str, Any]) -> V2Document:
    """Project a baseline/overlay payload into the stable v2 contract.

    Existing baseline field values are preserved.  The adapter adds the v2
    provenance keys without changing the frozen extractor or its selected
    values.  Only missing contract keys are added as nullable evidence, so
    compatibility fields cannot be accidentally renamed or dropped.
    """

    document_type = result.document_type
    metadata = dict(payload.get("metadata") or {})
    metadata.setdefault("document_id", result.document_id)
    metadata.setdefault("document_type", document_type)
    metadata.setdefault("source_file", result.source_file)
    metadata.setdefault("extraction_status", "extracted")
    metadata.setdefault("field_activity", {
        name: {"status": "active", "family": FIELD_FAMILY.get(name, "scalar")}
        for name in DOCUMENT_FIELDS[document_type]
    })
    metadata.setdefault("item_field_activity", {
        name: {"status": "active", "family": "table"}
        for name in ITEM_FIELDS.get(document_type, ())
    })
    metadata.setdefault("compatibility_field_activity", {
        name: {"status": "compatibility_only", "family": "scalar"}
        for name in COMPATIBILITY_DOCUMENT_FIELDS.get(document_type, ())
    })

    fields = {
        key: _field(value, default_method="v2_baseline_provenance")
        for key, value in payload.items()
        if key not in {"schema_version", "document_type", "metadata", "items"}
    }
    for name in DOCUMENT_FIELDS[document_type]:
        fields.setdefault(name, _missing())
    for name in COMPATIBILITY_DOCUMENT_FIELDS.get(document_type, ()):
        fields.setdefault(name, _missing("v2_compatibility_contract_missing"))

    raw_items = payload.get("items") or []
    items: list[dict[str, Any]] = []
    for raw_item in raw_items:
        item = dict(raw_item) if isinstance(raw_item, dict) else {}
        for name in ITEM_FIELDS.get(document_type, ()):
            item[name] = _field(item.get(name), default_method="v2_item_contract_missing")
        items.append(item)

    return V2Document(document_type, result.document_id, result.source_file, fields, items, metadata)


__all__ = ["V2Document", "build_document"]
