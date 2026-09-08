"""Evidence candidates used by the production extractor selection path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fintra.domain.schema import EvidenceField


@dataclass(frozen=True)
class FieldCandidate:
    """A typed, scored candidate before canonical field assignment."""

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
    section_membership: str | None = None
    evidence_field: EvidenceField | None = None

