"""Independent Extractor v2 orchestration and fixed document contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fintra.ocr.adapter import OCRResult

from .layout import Layout
from .party import resolve as resolve_party
from .scalar import resolve as resolve_scalar
from .specs import DOCUMENT_FIELDS, ITEM_FIELDS, PARTY_FIELDS, SPECS
from .table import resolve as resolve_items, resolve_goods_description


def _missing(method: str = "v2_no_candidate") -> dict[str, Any]:
    return {"value": None, "normalized_value": None, "confidence": None,
            "source_text": None, "source_label": None, "bbox": None, "page": None,
            "extraction_method": method, "status": "missing"}


@dataclass(frozen=True)
class V2Document:
    document_type: str
    document_id: str
    source_file: str
    fields: dict[str, Any]
    items: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        output = {
            "schema_version": "fintra-audit-field-schema-v2",
            "document_type": self.document_type,
            "metadata": {
                "document_id": self.document_id,
                "document_type": self.document_type,
                "source_file": self.source_file,
                "extraction_status": "extracted",
            },
            **self.fields,
        }
        output["items"] = self.items
        return output


def _field(result: dict[str, Any], name: str) -> dict[str, Any]:
    value = result or _missing()
    return value


def _resolve_scalar_fields(layout: Layout, names: tuple[str, ...], all_anchors: list) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name in names:
        if name in PARTY_FIELDS:
            values[name] = resolve_party(layout, name, all_anchors)
        elif name in SPECS:
            values[name] = resolve_scalar(layout, name, all_anchors)
        else:
            values[name] = _missing()
    return values


def _normalize_items(items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in items:
        row = {name: item.get(name, _missing("v2_item_field_not_detected")) for name in fields}
        output.append(row)
    return output


def extract_document(result: OCRResult) -> V2Document:
    document_type = result.document_type
    if document_type not in DOCUMENT_FIELDS:
        raise ValueError(f"unsupported document type: {document_type}")
    layout = Layout(result)
    anchor_fields = {name: SPECS[name].aliases for name in DOCUMENT_FIELDS[document_type] if name in SPECS}
    anchor_fields.update({name: SPECS[name].aliases for name in PARTY_FIELDS if name in SPECS})
    all_anchors = layout.all_anchors(anchor_fields)
    fields = _resolve_scalar_fields(layout, DOCUMENT_FIELDS[document_type], all_anchors)

    # Composite invoice headers frequently expose date and number in one
    # visual row.  Each typed resolver remains independent and nullable.
    if document_type == "Packing List" and fields.get("document_number", {}).get("status") != "extracted":
        fields["document_number"] = fields.get("packing_list_number", _missing())
    if document_type == "Packing List" and fields.get("date", {}).get("status") != "extracted":
        fields["date"] = fields.get("document_date", _missing())
    if document_type == "B/L":
        fields["goods_description"] = resolve_goods_description(layout)

    items = []
    if document_type in ITEM_FIELDS:
        items = _normalize_items(resolve_items(layout, document_type), ITEM_FIELDS[document_type])

    # Keep a stable top-level scalar contract even for values represented in
    # item rows.  No field is removed because evidence is absent.
    return V2Document(document_type, result.document_id, result.source_file, fields, items)


EXTRACTORS: dict[str, Callable[[OCRResult], V2Document]] = {
    document_type: extract_document for document_type in DOCUMENT_FIELDS
}


__all__ = ["EXTRACTORS", "V2Document", "extract_document"]
