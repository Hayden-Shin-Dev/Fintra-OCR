"""High-confidence semantic overlay on top of the Production Clean baseline.

The baseline remains authoritative whenever it already has an extracted value.
This first overlay only fills a missing field when the independent v2
candidate has a strong semantic anchor, a bounded relation, and valid typed
evidence.  It is deliberately document-independent and does not inspect Gold
or benchmark outcomes.
"""

from __future__ import annotations

from typing import Any

from fintra.ocr.adapter import OCRResult

from .layout import Layout
from .party import resolve as resolve_party
from .scalar import resolve as resolve_scalar
from .specs import DOCUMENT_FIELDS, PARTY_FIELDS_BY_DOCUMENT, SPECS
from .table import resolve as resolve_table, resolve_goods_description


RELATIONS = {"inline", "right", "below"}
# Numeric and unit cells have an objective type guard.  Free-text description,
# price, amount, and shipping-mark cells require row association logic that is
# not yet part of this compatibility overlay and must remain baseline-owned.
SAFE_TABLE_FILL_FIELDS = {
    "quantity", "unit", "package_count", "package_type", "gross_weight",
    "net_weight", "weight_unit", "measurement",
}


def _usable_candidate(value: dict[str, Any]) -> bool:
    if value.get("status") != "extracted" or value.get("value") in (None, ""):
        return False
    candidate = value.get("candidate") or {}
    # A candidate must retain its semantic provenance.  Unanchored typed
    # fallbacks are intentionally not allowed to override the baseline.
    anchor_strength = candidate.get("anchor_strength")
    return (
        bool(candidate.get("semantic_anchor"))
        and anchor_strength is not None
        and float(anchor_strength) >= 0.90
        and candidate.get("relation") in RELATIONS
        and candidate.get("type_valid") is True
        and candidate.get("section") == "label_value"
    )


def _missing(field: dict[str, Any] | None) -> bool:
    return not field or field.get("status") in {None, "missing"}


def _usable_table_candidate(value: dict[str, Any]) -> bool:
    if value.get("status") != "extracted" or value.get("value") in (None, ""):
        return False
    candidate = value.get("candidate") or {}
    return (
        candidate.get("type_valid") is True
        and candidate.get("section") == "item_table"
        and value.get("source_text")
        and value.get("extraction_method") in {"v2_table_rank", "v2_table_inferred"}
    )


def _anchor_inventory(result: OCRResult) -> tuple[Layout, list]:
    layout = Layout(result)
    fields = {name: SPECS[name].aliases for name in DOCUMENT_FIELDS[result.document_type] if name in SPECS}
    fields.update({name: SPECS[name].aliases for name in PARTY_FIELDS_BY_DOCUMENT[result.document_type]})
    return layout, layout.all_anchors(fields)


def apply(result: OCRResult, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fill only missing fields with strong, typed semantic evidence."""

    output = dict(payload)
    layout, all_anchors = _anchor_inventory(result)
    overrides: list[dict[str, Any]] = []
    resolved_parties: dict[str, dict[str, Any]] = {}
    allowed_parties = set(PARTY_FIELDS_BY_DOCUMENT[result.document_type])

    # Resolve party roles independently but keep the role inventory scoped to
    # the document contract.  This prevents e.g. CI seller/buyer resolution
    # from being polluted by B/L-only notify-party anchors.
    for field in DOCUMENT_FIELDS[result.document_type]:
        if field in allowed_parties:
            candidate = resolve_party(layout, field, all_anchors, resolved_parties)
            resolved_parties[field] = candidate
            if _missing(output.get(field)) and _usable_candidate(candidate):
                output[field] = candidate
                overrides.append({"field": field, "method": "party_anchor_overlay"})

    # Typed scalar overlay uses the same document-scoped anchor inventory.
    for field in DOCUMENT_FIELDS[result.document_type]:
        if field not in SPECS or field in allowed_parties or not _missing(output.get(field)):
            continue
        candidate = resolve_scalar(layout, field, all_anchors)
        if _usable_candidate(candidate):
            output[field] = candidate
            overrides.append({"field": field, "method": "scalar_anchor_overlay"})

    # Item fields are overlaid only onto an existing baseline row.  This keeps
    # row identity owned by Production Clean and uses the v2 table engine only
    # to fill a missing typed cell, never to invent or reorder rows.
    if result.document_type in {"Commercial Invoice", "Packing List"}:
        base_items = output.get("items") or []
        table_items = resolve_table(layout, result.document_type)
        for index, (base_item, table_item) in enumerate(zip(base_items, table_items)):
            for field, candidate in table_item.items():
                if field not in SAFE_TABLE_FILL_FIELDS:
                    continue
                if _missing(base_item.get(field)) and _usable_table_candidate(candidate):
                    base_item[field] = candidate
                    overrides.append({"field": f"items[{index}].{field}", "method": "typed_table_overlay"})

    # B/L goods description is a bounded semantic/table candidate, never an
    # unbounded page concatenation.  It is only used when clean has no value.
    if result.document_type == "B/L" and _missing(output.get("goods_description")):
        candidate = resolve_goods_description(layout)
        if candidate.get("status") == "extracted" and candidate.get("source_text"):
            output["goods_description"] = candidate
            overrides.append({"field": "goods_description", "method": "bounded_goods_overlay"})

    return output, {
        "mode": "semantic_overlay",
        "overrides": overrides,
        "document_id": result.document_id,
    }


__all__ = ["apply"]
