"""Separate OCR text recognition errors from bbox and segmentation effects."""

from collections.abc import Sequence
from dataclasses import dataclass

from .comparison import (
    BoundingBoxMatch,
    OCRComparison,
    bounding_box_iou,
    compare_predictions,
    match_bounding_boxes,
)
from .label_bbox import OCRBoundingBox
from .prediction_parser import OCRPrediction
from .text_metrics import character_error_rate, normalized_texts_match, text_similarity


@dataclass(frozen=True)
class TextMatch:
    """Text comparison for one GT/prediction pair."""

    ground_truth_index: int
    prediction_index: int
    similarity: float
    cer: float
    normalized_exact: bool
    spatial_iou: float


@dataclass(frozen=True)
class SegmentationCase:
    """A spatial one-to-many relation and its concatenated text comparison."""

    relation: str
    ground_truth_indices: tuple[int, ...]
    prediction_indices: tuple[int, ...]
    ground_truth_text: str
    prediction_text: str
    similarity: float
    cer: float


@dataclass(frozen=True)
class DetailedOCRAnalysis:
    """Detection, text-only, unmatched-text, and segmentation metrics."""

    detection: OCRComparison
    iou_matched_text_exact_count: int
    iou_matched_text_cer: float
    text_only_exact_match_count: int
    text_only_cer: float
    bbox_only_exact_match_count: int
    bbox_only_similar_match_count: int
    recognition_error_count: int
    unmatched_ground_truth_count: int
    unmatched_prediction_count: int
    gt_to_many_case_count: int
    gt_to_many_text_recovered_count: int
    prediction_to_many_case_count: int
    prediction_to_many_text_recovered_count: int
    unmatched_text_matches: tuple[TextMatch, ...]
    segmentation_cases: tuple[SegmentationCase, ...]


def _greedy_text_matches(
    predictions: Sequence[OCRPrediction],
    ground_truth: Sequence[OCRBoundingBox],
    ground_truth_indices: Sequence[int],
    prediction_indices: Sequence[int],
    similarity_threshold: float,
    require_similarity: bool = False,
) -> list[TextMatch]:
    candidates: list[TextMatch] = []
    for ground_truth_index in ground_truth_indices:
        for prediction_index in prediction_indices:
            truth = ground_truth[ground_truth_index]
            prediction = predictions[prediction_index]
            similarity = text_similarity(truth.text, prediction.text)
            if require_similarity and similarity < similarity_threshold:
                continue
            candidates.append(
                TextMatch(
                    ground_truth_index=ground_truth_index,
                    prediction_index=prediction_index,
                    similarity=similarity,
                    cer=character_error_rate(truth.text, prediction.text),
                    normalized_exact=normalized_texts_match(
                        truth.text, prediction.text
                    ),
                    spatial_iou=bounding_box_iou(truth, prediction),
                )
            )

    candidates.sort(
        key=lambda match: (
            match.normalized_exact,
            match.similarity,
            -match.cer,
            -match.ground_truth_index,
            -match.prediction_index,
        ),
        reverse=True,
    )
    matched_ground_truth = set()
    matched_predictions = set()
    matches: list[TextMatch] = []
    for match in candidates:
        if (
            match.ground_truth_index in matched_ground_truth
            or match.prediction_index in matched_predictions
        ):
            continue
        matched_ground_truth.add(match.ground_truth_index)
        matched_predictions.add(match.prediction_index)
        matches.append(match)
    return matches


def _mean_cer(matches: Sequence[TextMatch]) -> float:
    if not matches:
        return 0.0
    return sum(match.cer for match in matches) / len(matches)


def _ordered_text(texts: Sequence[str], indices: Sequence[int], boxes) -> str:
    ordered_indices = sorted(
        indices,
        key=lambda index: (min(boxes[index].x), min(boxes[index].y), index),
    )
    return "".join(texts[index] for index in ordered_indices)


def analyze_predictions(
    predictions: Sequence[OCRPrediction],
    ground_truth: Sequence[OCRBoundingBox],
    iou_threshold: float = 0.5,
    similarity_threshold: float = 0.8,
) -> DetailedOCRAnalysis:
    """Analyze detection, text recognition, and segmentation independently."""
    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0 and 1")

    detection = compare_predictions(predictions, ground_truth, iou_threshold)
    bbox_matches = match_bounding_boxes(predictions, ground_truth, iou_threshold)
    matched_ground_truth = {match.ground_truth_index for match in bbox_matches}
    matched_predictions = {match.prediction_index for match in bbox_matches}

    iou_text_matches = [
        TextMatch(
            ground_truth_index=match.ground_truth_index,
            prediction_index=match.prediction_index,
            similarity=text_similarity(
                ground_truth[match.ground_truth_index].text,
                predictions[match.prediction_index].text,
            ),
            cer=character_error_rate(
                ground_truth[match.ground_truth_index].text,
                predictions[match.prediction_index].text,
            ),
            normalized_exact=normalized_texts_match(
                ground_truth[match.ground_truth_index].text,
                predictions[match.prediction_index].text,
            ),
            spatial_iou=match.iou,
        )
        for match in bbox_matches
    ]
    text_only_matches = _greedy_text_matches(
        predictions,
        ground_truth,
        range(len(ground_truth)),
        range(len(predictions)),
        similarity_threshold,
    )
    unmatched_text_matches = _greedy_text_matches(
        predictions,
        ground_truth,
        [
            index
            for index in range(len(ground_truth))
            if index not in matched_ground_truth
        ],
        [
            index
            for index in range(len(predictions))
            if index not in matched_predictions
        ],
        similarity_threshold,
        require_similarity=True,
    )

    segmentation_cases: list[SegmentationCase] = []
    gt_to_many_recovered = 0
    prediction_to_many_recovered = 0
    for ground_truth_index, truth in enumerate(ground_truth):
        overlapping_predictions = tuple(
            prediction_index
            for prediction_index, prediction in enumerate(predictions)
            if bounding_box_iou(truth, prediction) > 0.0
        )
        if len(overlapping_predictions) < 2:
            continue
        prediction_text = _ordered_text(
            [prediction.text for prediction in predictions],
            overlapping_predictions,
            predictions,
        )
        similarity = text_similarity(truth.text, prediction_text)
        case = SegmentationCase(
            relation="gt_to_many",
            ground_truth_indices=(ground_truth_index,),
            prediction_indices=overlapping_predictions,
            ground_truth_text=truth.text,
            prediction_text=prediction_text,
            similarity=similarity,
            cer=character_error_rate(truth.text, prediction_text),
        )
        segmentation_cases.append(case)
        if similarity >= similarity_threshold:
            gt_to_many_recovered += 1

    for prediction_index, prediction in enumerate(predictions):
        overlapping_ground_truth = tuple(
            ground_truth_index
            for ground_truth_index, truth in enumerate(ground_truth)
            if bounding_box_iou(truth, prediction) > 0.0
        )
        if len(overlapping_ground_truth) < 2:
            continue
        ground_truth_text = _ordered_text(
            [truth.text for truth in ground_truth],
            overlapping_ground_truth,
            ground_truth,
        )
        similarity = text_similarity(ground_truth_text, prediction.text)
        case = SegmentationCase(
            relation="prediction_to_many",
            ground_truth_indices=overlapping_ground_truth,
            prediction_indices=(prediction_index,),
            ground_truth_text=ground_truth_text,
            prediction_text=prediction.text,
            similarity=similarity,
            cer=character_error_rate(ground_truth_text, prediction.text),
        )
        segmentation_cases.append(case)
        if similarity >= similarity_threshold:
            prediction_to_many_recovered += 1

    bbox_only_exact = sum(match.normalized_exact for match in unmatched_text_matches)
    bbox_only_similar = sum(
        not match.normalized_exact for match in unmatched_text_matches
    )
    return DetailedOCRAnalysis(
        detection=detection,
        iou_matched_text_exact_count=sum(
            match.normalized_exact for match in iou_text_matches
        ),
        iou_matched_text_cer=_mean_cer(iou_text_matches),
        text_only_exact_match_count=sum(
            match.normalized_exact for match in text_only_matches
        ),
        text_only_cer=_mean_cer(text_only_matches),
        bbox_only_exact_match_count=bbox_only_exact,
        bbox_only_similar_match_count=bbox_only_similar,
        recognition_error_count=detection.matched_count
        - sum(match.normalized_exact for match in iou_text_matches),
        unmatched_ground_truth_count=len(ground_truth) - len(matched_ground_truth),
        unmatched_prediction_count=len(predictions) - len(matched_predictions),
        gt_to_many_case_count=sum(
            case.relation == "gt_to_many" for case in segmentation_cases
        ),
        gt_to_many_text_recovered_count=gt_to_many_recovered,
        prediction_to_many_case_count=sum(
            case.relation == "prediction_to_many" for case in segmentation_cases
        ),
        prediction_to_many_text_recovered_count=prediction_to_many_recovered,
        unmatched_text_matches=tuple(unmatched_text_matches),
        segmentation_cases=tuple(segmentation_cases),
    )
