"""Normalize raw PaddleOCR results for ground-truth comparison."""

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any


@dataclass(frozen=True)
class OCRPrediction:
    """One recognized text and its axis-aligned four-point box."""

    text: str
    x: tuple[int, int, int, int]
    y: tuple[int, int, int, int]
    score: float


def _as_sequence(value: Any, field_name: str) -> Any:
    if value is None or not hasattr(value, "__len__"):
        raise ValueError(f"PaddleOCR result {field_name} must be a sequence")
    return value


def _parse_box(
    value: Any, index: int
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if value is None or not hasattr(value, "__len__") or len(value) != 4:
        raise ValueError(f"PaddleOCR rec_boxes[{index}] must contain four values")
    if not all(isinstance(coordinate, Integral) for coordinate in value):
        raise ValueError(f"PaddleOCR rec_boxes[{index}] must contain integers")

    left, top, right, bottom = (int(coordinate) for coordinate in value)
    return (left, right, right, left), (top, top, bottom, bottom)


def parse_paddle_result(result: Mapping[str, Any]) -> list[OCRPrediction]:
    """Convert one PaddleOCR result object into comparable predictions."""
    texts = _as_sequence(result.get("rec_texts"), "rec_texts")
    scores = _as_sequence(result.get("rec_scores"), "rec_scores")
    boxes = _as_sequence(result.get("rec_boxes"), "rec_boxes")

    if not len(texts) == len(scores) == len(boxes):
        raise ValueError("PaddleOCR text, score, and box counts must match")

    predictions: list[OCRPrediction] = []
    for index, (text, score, box) in enumerate(zip(texts, scores, boxes)):
        if not isinstance(text, str):
            raise ValueError(f"PaddleOCR rec_texts[{index}] must be a string")
        if not isinstance(score, Real):
            raise ValueError(f"PaddleOCR rec_scores[{index}] must be numeric")
        x, y = _parse_box(box, index)
        predictions.append(
            OCRPrediction(text=text, x=x, y=y, score=float(score))
        )

    return predictions
