"""Evidence objects returned by deterministic OCR field extraction."""

from dataclasses import dataclass
from typing import Literal

from .prediction_parser import OCRPrediction


FieldStatus = Literal["found", "missing", "ambiguous"]
BoundingBox = tuple[
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
]


@dataclass(frozen=True)
class FieldEvidence:
    """One extracted field value and the OCR evidence supporting it."""

    field_name: str
    value: str | None
    raw_text: str
    bbox: BoundingBox | None
    confidence: float
    status: FieldStatus
    source_indices: tuple[int, ...] = ()
    reason: str | None = None


def _prediction_order(prediction: OCRPrediction, index: int) -> tuple[int, int, int]:
    return min(prediction.y), min(prediction.x), index


def _combined_bbox(predictions: list[OCRPrediction]) -> BoundingBox:
    left = min(min(prediction.x) for prediction in predictions)
    top = min(min(prediction.y) for prediction in predictions)
    right = max(max(prediction.x) for prediction in predictions)
    bottom = max(max(prediction.y) for prediction in predictions)
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def make_field_evidence(
    field_name: str,
    predictions: list[OCRPrediction],
    source_indices: tuple[int, ...],
    value: str | None,
    status: FieldStatus = "found",
    reason: str | None = None,
) -> FieldEvidence:
    """Build field evidence from one or more OCR prediction indices."""
    if status not in {"found", "missing", "ambiguous"}:
        raise ValueError("status must be found, missing, or ambiguous")
    if status == "found" and value is None:
        raise ValueError("found evidence must have a value")
    if status != "found":
        return FieldEvidence(
            field_name=field_name,
            value=None,
            raw_text="",
            bbox=None,
            confidence=0.0,
            status=status,
            reason=reason,
        )

    selected = [predictions[index] for index in source_indices]
    if not selected:
        raise ValueError("found evidence must reference at least one prediction")
    ordered = sorted(
        zip(source_indices, selected),
        key=lambda item: _prediction_order(item[1], item[0]),
    )
    return FieldEvidence(
        field_name=field_name,
        value=value,
        raw_text=" ".join(prediction.text for _, prediction in ordered),
        bbox=_combined_bbox(selected),
        confidence=min(prediction.score for prediction in selected),
        status=status,
        source_indices=tuple(index for index, _ in ordered),
        reason=reason,
    )


def missing_field(field_name: str, reason: str) -> FieldEvidence:
    """Build an explicit missing-field result without fabricated evidence."""
    return make_field_evidence(
        field_name=field_name,
        predictions=[],
        source_indices=(),
        value=None,
        status="missing",
        reason=reason,
    )
