"""Candidate objects used before final field selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fintra.domain.schema import EvidenceField


@dataclass(frozen=True)
class FieldCandidate:
    field_name: str
    value: Any
    source_text: str | None
    region_indices: tuple[int, ...]
    bbox: list[list[float]] | None
    ocr_confidence: float | None
    semantic_anchor: str | None
    relation: str
    normalized_geometry: tuple[float, float, float, float] | None
    type_valid: bool
    section_membership: str | None
    score: float
    reject_reason: str | None = None
    evidence: EvidenceField | None = None

    @property
    def accepted(self) -> bool:
        return self.type_valid and self.evidence is not None and self.evidence.value not in (None, "")
