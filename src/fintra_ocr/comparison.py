"""Compare normalized PaddleOCR predictions with target annotations."""

from dataclasses import dataclass
from typing import Sequence

from .label_bbox import OCRBoundingBox
from .prediction_parser import OCRPrediction


@dataclass(frozen=True)
class OCRComparison:
    """Counts from one prediction-versus-ground-truth comparison."""

    ground_truth_count: int
    prediction_count: int
    matched_count: int
    exact_text_match_count: int
    iou_threshold: float

    @property
    def precision(self) -> float:
        """Return matched predictions divided by all predictions."""
        if self.prediction_count == 0:
            return 0.0
        return self.matched_count / self.prediction_count

    @property
    def recall(self) -> float:
        """Return matched ground-truth boxes divided by all ground truth."""
        if self.ground_truth_count == 0:
            return 0.0
        return self.matched_count / self.ground_truth_count


def _bounds(x: Sequence[int], y: Sequence[int]) -> tuple[int, int, int, int]:
    return min(x), min(y), max(x), max(y)


def _intersection_over_union(
    first: tuple[int, int, int, int], second: tuple[int, int, int, int]
) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection_width = max(0, right - left)
    intersection_height = max(0, bottom - top)
    intersection = intersection_width * intersection_height

    first_area = max(0, first[2] - first[0]) * max(0, first[3] - first[1])
    second_area = max(0, second[2] - second[0]) * max(0, second[3] - second[1])
    union = first_area + second_area - intersection
    if union == 0:
        return 0.0
    return intersection / union


def compare_predictions(
    predictions: Sequence[OCRPrediction],
    ground_truth: Sequence[OCRBoundingBox],
    iou_threshold: float = 0.5,
) -> OCRComparison:
    """Greedily match boxes by highest IoU and count exact text matches."""
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be between 0 and 1")

    pairs = []
    for truth_index, truth in enumerate(ground_truth):
        truth_bounds = _bounds(truth.x, truth.y)
        for prediction_index, prediction in enumerate(predictions):
            prediction_bounds = _bounds(prediction.x, prediction.y)
            pairs.append(
                (
                    _intersection_over_union(truth_bounds, prediction_bounds),
                    truth_index,
                    prediction_index,
                )
            )

    matched_truth = set()
    matched_predictions = set()
    exact_text_matches = 0
    for iou, truth_index, prediction_index in sorted(pairs, reverse=True):
        if iou < iou_threshold:
            break
        if truth_index in matched_truth or prediction_index in matched_predictions:
            continue
        matched_truth.add(truth_index)
        matched_predictions.add(prediction_index)
        if ground_truth[truth_index].text == predictions[prediction_index].text:
            exact_text_matches += 1

    return OCRComparison(
        ground_truth_count=len(ground_truth),
        prediction_count=len(predictions),
        matched_count=len(matched_truth),
        exact_text_match_count=exact_text_matches,
        iou_threshold=iou_threshold,
    )
