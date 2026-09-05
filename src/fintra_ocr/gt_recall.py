"""Ground-truth recall metrics for the AIHub-style Fintra labels.

Important dataset fact: target JSON labels do not necessarily annotate static
form captions such as "Invoice Number" or "Gross Weight" even though those
captions are visibly printed on the image. Therefore OCR prediction precision
against the JSON is not a valid metric: correctly recognized static captions can
look like false positives. This module evaluates *GT value recall* and text
quality instead.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from statistics import mean
from typing import Sequence

from .label_bbox import OCRBoundingBox
from .prediction_parser import OCRPrediction
from .text_metrics import character_error_rate, normalize_ocr_text, normalized_texts_match, text_similarity


@dataclass(frozen=True)
class GTBoxMatch:
    gt_index: int
    gt_text: str
    predicted_text: str
    prediction_indices: tuple[int, ...]
    similarity: float
    cer: float
    geometric_candidate: bool
    exact: bool
    contained: bool


@dataclass(frozen=True)
class GTRecallReport:
    gt_boxes: int
    predicted_boxes: int
    geometric_recall: float
    exact_text_recall: float
    segmentation_aware_recall: float
    similarity_90_recall: float
    mean_similarity: float
    mean_cer: float
    matches: tuple[GTBoxMatch, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        return data


def _bounds(item: OCRBoundingBox | OCRPrediction) -> tuple[int, int, int, int]:
    return min(item.x), min(item.y), max(item.x), max(item.y)


def _intersection(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    left = max(a[0], b[0]); top = max(a[1], b[1])
    right = min(a[2], b[2]); bottom = min(a[3], b[3])
    return max(0, right-left) * max(0, bottom-top)


def _nearby_prediction_indices(gt: OCRBoundingBox, predictions: Sequence[OCRPrediction]) -> list[int]:
    gx1, gy1, gx2, gy2 = _bounds(gt)
    gw, gh = max(1, gx2-gx1), max(1, gy2-gy1)
    margin_x = max(12, int(gw * 0.25))
    margin_y = max(8, int(gh * 0.45))
    expanded = (gx1-margin_x, gy1-margin_y, gx2+margin_x, gy2+margin_y)
    result: list[int] = []
    for index, prediction in enumerate(predictions):
        pb = _bounds(prediction)
        inter = _intersection(expanded, pb)
        if inter > 0:
            result.append(index)
            continue
        cx = (pb[0] + pb[2]) / 2
        cy = (pb[1] + pb[3]) / 2
        if expanded[0] <= cx <= expanded[2] and expanded[1] <= cy <= expanded[3]:
            result.append(index)
    result.sort(key=lambda idx: (min(predictions[idx].y), min(predictions[idx].x), idx))
    return result


def _candidate_groups(indices: Sequence[int], max_group: int = 12) -> list[tuple[int, ...]]:
    groups: list[tuple[int, ...]] = [(index,) for index in indices]
    # Contiguous groups cover common Paddle segmentation differences without
    # exploding combinatorially.
    for size in range(2, min(max_group, len(indices)) + 1):
        for start in range(0, len(indices)-size+1):
            groups.append(tuple(indices[start:start+size]))
    return groups


def _join(predictions: Sequence[OCRPrediction], group: Sequence[int]) -> str:
    return " ".join(predictions[index].text.strip() for index in group if predictions[index].text.strip())


def match_gt_box(
    gt: OCRBoundingBox,
    predictions: Sequence[OCRPrediction],
    gt_index: int,
) -> GTBoxMatch:
    indices = _nearby_prediction_indices(gt, predictions)
    if not indices:
        return GTBoxMatch(gt_index, gt.text, "", (), 0.0, 1.0, False, False, False)
    best_group: tuple[int, ...] = ()
    best_text = ""
    best_similarity = -1.0
    for group in _candidate_groups(indices):
        candidate = _join(predictions, group)
        similarity = text_similarity(gt.text, candidate)
        if similarity > best_similarity:
            best_similarity = similarity
            best_group = group
            best_text = candidate
            if similarity == 1.0:
                break
    return GTBoxMatch(
        gt_index=gt_index,
        gt_text=gt.text,
        predicted_text=best_text,
        prediction_indices=best_group,
        similarity=max(0.0, best_similarity),
        cer=character_error_rate(gt.text, best_text),
        geometric_candidate=True,
        exact=normalized_texts_match(gt.text, best_text),
        contained=(
            bool(normalize_ocr_text(gt.text))
            and normalize_ocr_text(gt.text) in normalize_ocr_text(best_text)
        ),
    )


def evaluate_gt_recall(
    ground_truth: Sequence[OCRBoundingBox],
    predictions: Sequence[OCRPrediction],
) -> GTRecallReport:
    usable_gt = [item for item in ground_truth if item.text.strip()]
    matches = tuple(match_gt_box(item, predictions, index) for index, item in enumerate(usable_gt))
    total = len(matches)
    if total == 0:
        return GTRecallReport(0, len(predictions), 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, matches)
    geometric = sum(match.geometric_candidate for match in matches) / total
    exact = sum(match.exact for match in matches) / total
    segmentation_aware = sum(match.exact or match.contained for match in matches) / total
    sim90 = sum(match.similarity >= 0.90 for match in matches) / total
    return GTRecallReport(
        gt_boxes=total,
        predicted_boxes=len(predictions),
        geometric_recall=geometric,
        exact_text_recall=exact,
        segmentation_aware_recall=segmentation_aware,
        similarity_90_recall=sim90,
        mean_similarity=mean(match.similarity for match in matches),
        mean_cer=mean(match.cer for match in matches),
        matches=matches,
    )
