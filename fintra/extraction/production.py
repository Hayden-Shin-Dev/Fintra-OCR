"""Clean production extraction boundary.

The boundary consumes only :class:`OCRResult` and emits the evidence-bearing
canonical schema.  Its standalone parity kernel is kept separate from the
historical ``documents``/``refinement`` modules; those modules remain
available only to comparison probes and historical regression tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fintra.domain.schema import EvidenceField
from fintra.ocr.adapter import OCRResult

from .layout import Layout
from .production_engine import (
    extract_bill_of_lading as _extract_bill_of_lading,
    extract_commercial_invoice as _extract_commercial_invoice,
    extract_packing_list as _extract_packing_list,
)


@dataclass(frozen=True)
class FieldCandidate:
    """Common evidence candidate used by production diagnostics and clients."""

    field_name: str
    value: Any
    source_text: str | None
    ocr_region_indices: tuple[int, ...]
    bbox: list[list[float]] | None
    ocr_confidence: float | None
    semantic_anchor: str | None
    normalized_geometry: tuple[float, float, float, float] | None
    relation: str | None
    extraction_method: str
    type_valid: bool
    score: float
    reject_reason: str | None = None


def _dimensions(result: OCRResult) -> tuple[float, float]:
    layout = Layout(result)
    return layout.width, layout.height


def _candidate(field_name: str, field: EvidenceField, result: OCRResult) -> FieldCandidate:
    bbox = field.bbox
    geometry = None
    if bbox:
        width, height = _dimensions(result)
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        geometry = (min(xs) / width, min(ys) / height, max(xs) / width, max(ys) / height)
    region_indices: list[int] = []
    if bbox:
        fx1, fy1, fx2, fy2 = min(xs), min(ys), max(xs), max(ys)
        for region in result.regions:
            rx1, ry1, rx2, ry2 = region.bbox
            overlap = max(0.0, min(fx2, rx2) - max(fx1, rx1)) * max(0.0, min(fy2, ry2) - max(fy1, ry1))
            region_area = max(1.0, (rx2 - rx1) * (ry2 - ry1))
            if overlap / region_area >= 0.25 or (fx1 <= region.bbox[0] <= fx2 and fy1 <= region.bbox[1] <= fy2):
                region_indices.append(region.index)
    return FieldCandidate(
        field_name=field_name,
        value=field.value,
        source_text=field.source_text,
        ocr_region_indices=tuple(sorted(set(region_indices))),
        bbox=bbox,
        ocr_confidence=field.confidence,
        semantic_anchor=None,
        normalized_geometry=geometry,
        relation=None,
        extraction_method=field.extraction_method,
        type_valid=field.status.value == "extracted",
        score=float(field.confidence or 0.0),
    )


def _walk_candidates(value: Any, prefix: str, result: OCRResult) -> list[FieldCandidate]:
    candidates: list[FieldCandidate] = []
    if isinstance(value, EvidenceField):
        if value.status.value == "extracted":
            candidates.append(_candidate(prefix, value, result))
        return candidates
    if isinstance(value, list):
        for index, item in enumerate(value):
            candidates.extend(_walk_candidates(item, f"{prefix}[{index}]", result))
        return candidates
    if hasattr(value, "__dataclass_fields__"):
        for name in value.__dataclass_fields__:
            if name == "metadata":
                continue
            child = getattr(value, name)
            child_prefix = f"{prefix}.{name}" if prefix else name
            candidates.extend(_walk_candidates(child, child_prefix, result))
    return candidates


def candidates_for(document: Any, result: OCRResult) -> list[FieldCandidate]:
    """Return the selected canonical fields as a uniform evidence view."""

    return _walk_candidates(document, "", result)


def _extract(result: OCRResult) -> Any:
    factories = {
        "Commercial Invoice": _extract_commercial_invoice,
        "Packing List": _extract_packing_list,
        "B/L": _extract_bill_of_lading,
    }
    try:
        document = factories[result.document_type](result)
    except KeyError as exc:
        raise ValueError(f"unsupported document_type: {result.document_type}") from exc
    # The clean path performs a single candidate selection pass.  The
    # candidates are intentionally derived after selection for diagnostics;
    # they never trigger a second resolver or overwrite a field.
    candidates_for(document, result)
    return document


def extract_commercial_invoice(result: OCRResult):
    return _extract(result)


def extract_packing_list(result: OCRResult):
    return _extract(result)


def extract_bill_of_lading(result: OCRResult):
    return _extract(result)


EXTRACTORS: dict[str, Callable[[OCRResult], object]] = {
    "Commercial Invoice": extract_commercial_invoice,
    "Packing List": extract_packing_list,
    "B/L": extract_bill_of_lading,
}


__all__ = [
    "FieldCandidate",
    "EXTRACTORS",
    "candidates_for",
    "extract_commercial_invoice",
    "extract_packing_list",
    "extract_bill_of_lading",
]
