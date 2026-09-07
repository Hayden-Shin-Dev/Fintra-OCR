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
from .specs import DOCUMENT_FIELDS, ITEM_FIELDS, PARTY_FIELDS, PARTY_FIELDS_BY_DOCUMENT, SPECS
from .table import resolve as resolve_table, resolve_goods_description


SCALAR_RELATIONS = {"inline", "right", "below", "right_multiline", "below_multiline"}
PARTY_RELATIONS = SCALAR_RELATIONS | {"party_block", "party_block_line", "same_as_role"}
# Numeric and unit cells have an objective type guard.  Free-text description,
# price, amount, and shipping-mark cells require row association logic that is
# not yet part of this compatibility overlay and must remain baseline-owned.
SAFE_TABLE_FILL_FIELDS = {
    "description", "hs_code", "line_number", "part_number", "po_number",
    "product_code", "quantity", "shipping_mark", "sku", "unit", "unit_price",
    "amount", "package_count", "package_type", "gross_weight", "net_weight",
    "weight_unit", "measurement",
}


def _usable_candidate(value: dict[str, Any], family: str = "scalar") -> bool:
    if value.get("status") != "extracted" or value.get("value") in (None, ""):
        return False
    candidate = value.get("candidate") or {}
    # A candidate must retain its semantic provenance.  Unanchored typed
    # fallbacks are intentionally not allowed to override the baseline.
    anchor_strength = candidate.get("anchor_strength")
    relations = PARTY_RELATIONS if family == "party" else SCALAR_RELATIONS
    section_ok = candidate.get("section") == ("party_block" if family == "party" else "label_value")
    same_as_ok = family == "party" and candidate.get("relation") == "same_as_role"
    return (
        (bool(candidate.get("semantic_anchor")) or same_as_ok)
        and anchor_strength is not None
        and float(anchor_strength) >= 0.90
        and (candidate.get("relation") in relations or same_as_ok)
        and candidate.get("type_valid") is True
        and (section_ok or same_as_ok)
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
        and (candidate.get("score", 0.0) >= 1.0 or candidate.get("section") == "item_table")
    )


def _anchor_inventory(result: OCRResult) -> tuple[Layout, list]:
    layout = Layout(result)
    fields = {name: SPECS[name].aliases for name in DOCUMENT_FIELDS[result.document_type] if name in SPECS}
    fields.update({name: SPECS[name].aliases for name in PARTY_FIELDS_BY_DOCUMENT[result.document_type]})
    return layout, layout.all_anchors(fields)


def _same_value(left: dict[str, Any] | None, right: dict[str, Any]) -> bool:
    from .layout import canonical
    return bool(left and left.get("value") and right.get("value") and
                canonical(str(left["value"])) == canonical(str(right["value"])))


def _semantic_override_allowed(baseline: dict[str, Any] | None, candidate: dict[str, Any], family: str) -> bool:
    """Allow a strong, role-scoped semantic candidate to correct baseline output.

    Baseline values are retained when the semantic candidate is weak or
    ambiguous.  A different value may replace baseline only when the
    candidate has an explicit anchor and typed evidence; this keeps the rule
    independent of document IDs and Gold literals.
    """
    if not _usable_candidate(candidate, family):
        return False
    if _missing(baseline) or _same_value(baseline, candidate):
        return True
    # A different value is not allowed to overwrite an existing extraction
    # until the candidate is proven to belong to a distinct, bounded semantic
    # block.  This conservative guard prevents duplicate OCR suffixes and
    # fuzzy cross-role anchors from degrading the frozen baseline.  The
    # candidate remains available in diagnostics for a later arbitration
    # decision; it is never silently discarded from raw evidence.
    return False


def apply(result: OCRResult, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fill only missing fields with strong, typed semantic evidence."""

    output = dict(payload)
    layout, all_anchors = _anchor_inventory(result)
    overrides: list[dict[str, Any]] = []
    title_diagnostics: list[dict[str, Any]] = []
    resolved_parties: dict[str, dict[str, Any]] = {}
    allowed_parties = set(PARTY_FIELDS_BY_DOCUMENT[result.document_type]) | {
        field for field in DOCUMENT_FIELDS[result.document_type] if field in PARTY_FIELDS
    }

    def record_title(field: str, candidate: dict[str, Any], before: dict[str, Any] | None, family: str) -> None:
        anchors = layout.anchors(field, SPECS[field].aliases) if field in SPECS else []
        candidate_meta = candidate.get("candidate") or {}
        status = candidate.get("status")
        if status == "extracted":
            state = "BASELINE_KEPT" if before and not _missing(before) and not _same_value(before, candidate) else "EXTRACTED"
        elif status == "ambiguous":
            state = "AMBIGUOUS"
        elif anchors:
            state = "LABEL_NO_VALUE"
        else:
            state = "NO_LABEL"
        title_diagnostics.append({
            "field": field,
            "family": family,
            "label_detected": bool(anchors),
            "label_strength": max((anchor.strength for anchor in anchors), default=0.0),
            "value_candidate_count": candidate_meta.get("candidate_count", 0),
            "selected_value": candidate.get("value"),
            "state": state,
            "reject_reason": candidate_meta.get("reject_reason"),
        })

    # Resolve party roles independently but keep the role inventory scoped to
    # the document contract.  This prevents e.g. CI seller/buyer resolution
    # from being polluted by B/L-only notify-party anchors.
    for field in DOCUMENT_FIELDS[result.document_type]:
        if field in allowed_parties:
            candidate = resolve_party(layout, field, all_anchors, resolved_parties)
            resolved_parties[field] = candidate
            record_title(field, candidate, output.get(field), "party")
            if _semantic_override_allowed(output.get(field), candidate, "party"):
                was_missing = _missing(output.get(field))
                method = "party_anchor_overlay" if was_missing else "party_semantic_arbitration"
                output[field] = candidate
                overrides.append({"field": field, "method": method})

    # Typed scalar overlay uses the same document-scoped anchor inventory.
    for field in DOCUMENT_FIELDS[result.document_type]:
        if field not in SPECS or field in allowed_parties:
            continue
        candidate = resolve_scalar(layout, field, all_anchors)
        record_title(field, candidate, output.get(field), "scalar")
        if _semantic_override_allowed(output.get(field), candidate, "scalar"):
            was_missing = _missing(output.get(field))
            output[field] = candidate
            method = "scalar_anchor_overlay" if was_missing else "scalar_semantic_arbitration"
            overrides.append({"field": field, "method": method})

    # Item fields are overlaid only onto an existing baseline row.  This keeps
    # row identity owned by Production Clean and uses the v2 table engine only
    # to fill a missing typed cell, never to invent or reorder rows.
    if result.document_type in ITEM_FIELDS:
        base_items = output.get("items") or []
        table_items = resolve_table(layout, result.document_type)
        for index, (base_item, table_item) in enumerate(zip(base_items, table_items)):
            for field, candidate in table_item.items():
                if field not in SAFE_TABLE_FILL_FIELDS:
                    continue
                if (field in ITEM_FIELDS[result.document_type] and
                        (_missing(base_item.get(field)) or _same_value(base_item.get(field), candidate)) and
                        _usable_table_candidate(candidate)):
                    base_item[field] = candidate
                    overrides.append({"field": f"items[{index}].{field}", "method": "typed_table_overlay"})
                if field in ITEM_FIELDS[result.document_type]:
                    meta = candidate.get("candidate") or {}
                    title_diagnostics.append({
                        "field": f"items[{index}].{field}",
                        "family": "table",
                        "label_detected": bool(meta.get("source_label")),
                        "label_strength": None,
                        "value_candidate_count": meta.get("candidate_count", 0),
                        "selected_value": candidate.get("value"),
                        "state": "EXTRACTED" if candidate.get("status") == "extracted" else "NO_LABEL",
                        "reject_reason": meta.get("reject_reason"),
                    })

    # B/L goods description is a bounded semantic/table candidate, never an
    # unbounded page concatenation.  It is only used when clean has no value.
    if result.document_type == "B/L" and ("goods_description" in DOCUMENT_FIELDS["B/L"] or _missing(output.get("goods_description"))):
        candidate = resolve_goods_description(layout)
        if candidate.get("status") == "extracted" and candidate.get("source_text"):
            output["goods_description"] = candidate
            overrides.append({"field": "goods_description", "method": "bounded_goods_overlay"})

    return output, {
        "mode": "semantic_overlay",
        "overrides": overrides,
        "title_diagnostics": title_diagnostics,
        "document_id": result.document_id,
    }


__all__ = ["apply"]
