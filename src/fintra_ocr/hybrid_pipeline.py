"""Conservative field-level arbitration for the MVP OCR backends.

Each backend runs independently with its existing detector, recognizer, and
field extractor.  This module only decides which already-extracted evidence is
safe to expose to the common document schema.  It deliberately does not add
document-specific rules or alter either OCR backend.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from collections.abc import Mapping

from .common_schema import build_common_document_from_form_type
from .e2e_pipeline import PipelineResult
from .field_evidence import FieldEvidence
from .field_extraction import extract_fields
from .normalization import normalize_fields
from .ocr_backends import OCRBackend
from .prediction_parser import OCRPrediction


@dataclass(frozen=True)
class HybridPolicy:
    """Generic, confidence-gated policy for two independent OCR results."""

    fallback_min_confidence: float = 0.90
    conflict_winner_margin: float = 0.15
    conflict_winner_min_confidence: float = 0.90

    def __post_init__(self) -> None:
        if not 0.0 <= self.fallback_min_confidence <= 1.0:
            raise ValueError("fallback_min_confidence must be between 0 and 1")
        if not 0.0 <= self.conflict_winner_margin <= 1.0:
            raise ValueError("conflict_winner_margin must be between 0 and 1")
        if not 0.0 <= self.conflict_winner_min_confidence <= 1.0:
            raise ValueError("conflict_winner_min_confidence must be between 0 and 1")


def _value_key(field: FieldEvidence) -> str:
    value = field.normalized if field.normalized is not None else field.value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _with_reason(field: FieldEvidence, reason: str) -> FieldEvidence:
    existing = field.reason
    combined = reason if not existing else f"{existing}; {reason}"
    return replace(field, reason=combined)


def _ambiguous_conflict(primary: FieldEvidence, fallback: FieldEvidence) -> FieldEvidence:
    return replace(
        primary,
        status="ambiguous",
        reason=(
            "primary and fallback produced conflicting field values; "
            f"primary_confidence={primary.confidence:.3f}, "
            f"fallback_confidence={fallback.confidence:.3f}"
        ),
    )


def _arbitrate_with_source(
    primary: FieldEvidence,
    fallback: FieldEvidence,
    policy: HybridPolicy = HybridPolicy(),
) -> tuple[FieldEvidence, bool]:
    """Select safe evidence without silently resolving weak conflicts.

    The primary backend remains authoritative when its evidence is usable.  A
    high-confidence fallback fills a primary missing/ambiguous result.  When
    both backends found different values, the fallback wins only with a large
    confidence margin; otherwise the field is explicitly ambiguous.
    """
    if primary.status == "found" and fallback.status == "found":
        if _value_key(primary) == _value_key(fallback):
            if primary.confidence >= fallback.confidence:
                return primary, False
            return _with_reason(fallback, "same value confirmed by primary backend"), True
        if (
            fallback.confidence >= policy.conflict_winner_min_confidence
            and fallback.confidence - primary.confidence >= policy.conflict_winner_margin
        ):
            return _with_reason(fallback, "fallback won a confidence-gated conflict"), True
        return _ambiguous_conflict(primary, fallback), False

    if primary.status in {"missing", "ambiguous"} and fallback.status == "found":
        if fallback.confidence >= policy.fallback_min_confidence:
            return _with_reason(fallback, "fallback filled primary missing/ambiguous evidence"), True
        return primary, False

    return primary, False


def arbitrate_field(
    primary: FieldEvidence,
    fallback: FieldEvidence,
    policy: HybridPolicy = HybridPolicy(),
) -> FieldEvidence:
    """Return the safe field evidence selected by :class:`HybridPolicy`."""
    return _arbitrate_with_source(primary, fallback, policy)[0]


def _rebase_source_indices(field: FieldEvidence, offset: int) -> FieldEvidence:
    if not field.source_indices:
        return field
    return replace(
        field,
        source_indices=tuple(index + offset for index in field.source_indices),
    )


def build_hybrid_document(
    form_type: str,
    document_id: str,
    primary_predictions: list[OCRPrediction],
    fallback_predictions: list[OCRPrediction],
    *,
    policy: HybridPolicy = HybridPolicy(),
) -> PipelineResult:
    """Build one conservative Fintra document from two OCR result sets.

    Predictions are retained as ``primary + fallback`` so field evidence source
    indices remain auditable.  Existing field extraction is run independently
    for each backend; no extractor rule is added here.
    """
    primary_fields = normalize_fields(extract_fields(form_type, primary_predictions))
    fallback_fields = normalize_fields(extract_fields(form_type, fallback_predictions))

    selected: dict[str, FieldEvidence] = {}
    field_names = sorted(set(primary_fields) | set(fallback_fields))
    for field_name in field_names:
        primary_field = primary_fields.get(
            field_name,
            FieldEvidence(field_name, None, "", None, 0.0, "missing"),
        )
        fallback_field = fallback_fields.get(
            field_name,
            FieldEvidence(field_name, None, "", None, 0.0, "missing"),
        )
        chosen, used_fallback = _arbitrate_with_source(
            primary_field, fallback_field, policy
        )
        if used_fallback:
            chosen = _rebase_source_indices(chosen, len(primary_predictions))
        selected[field_name] = chosen

    predictions = tuple(primary_predictions + fallback_predictions)
    document = build_common_document_from_form_type(form_type, document_id, selected)
    return PipelineResult(
        form_type=form_type,
        document_id=document_id,
        predictions=predictions,
        fields=selected,
        document=document,
    )


def run_hybrid_document(
    image_bytes: bytes,
    form_type: str,
    document_id: str,
    primary: OCRBackend,
    fallback: OCRBackend,
    *,
    policy: HybridPolicy = HybridPolicy(),
) -> PipelineResult:
    """Run both backends and expose one conservative Fintra document."""
    return build_hybrid_document(
        form_type,
        document_id,
        primary.predict_bytes(image_bytes),
        fallback.predict_bytes(image_bytes),
        policy=policy,
    )
