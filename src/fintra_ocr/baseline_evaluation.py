"""Evaluate one baseline sample for each Fintra target document type."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from .comparison import OCRComparison, compare_predictions
from .detailed_analysis import DetailedOCRAnalysis, analyze_predictions
from .image_loader import load_image_bytes
from .label_bbox import parse_bounding_boxes
from .label_loader import load_label_json
from .prediction_parser import parse_paddle_result
from .sample_selection import TargetSample, select_target_samples
from .target_scope import FINTRA_FORM_TYPES
from .target_selection import TargetArchivePair


RawPredictor = Callable[[bytes], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class FormEvaluation:
    """Comparison result for one target form type sample."""

    sample: TargetSample
    comparison: OCRComparison


@dataclass(frozen=True)
class DetailedFormEvaluation:
    """Detailed comparison result for one target form type sample."""

    sample: TargetSample
    analysis: DetailedOCRAnalysis


def _load_predictions_for_samples(
    samples: Sequence[TargetSample],
    predictor: Optional[RawPredictor],
    ocr: Any,
) -> list[list[Any]]:
    image_bytes_list = [
        load_image_bytes(sample.source_archive, sample.image_member)
        for sample in samples
    ]
    if predictor is None:
        from .baseline_ocr import create_paddle_ocr, predict_image_bytes_batch

        pipeline = ocr if ocr is not None else create_paddle_ocr()
        raw_results = list(
            predict_image_bytes_batch(image_bytes_list, ocr=pipeline)
        )
        if len(raw_results) != len(samples):
            raise ValueError("PaddleOCR result count must match sample count")
    else:
        raw_results = []
        for image_bytes in image_bytes_list:
            sample_results = list(predictor(image_bytes))
            if not sample_results:
                raise ValueError("PaddleOCR returned no result for a sample")
            raw_results.append(sample_results[0])
    return raw_results


def _select_target_samples(
    archive_groups: Mapping[str, Sequence[TargetArchivePair]],
    split: str,
    samples_per_form: int,
) -> list[TargetSample]:
    if samples_per_form <= 0:
        raise ValueError("samples_per_form must be greater than zero")

    pairs = archive_groups[split]
    samples: list[TargetSample] = []
    for form_type in sorted(FINTRA_FORM_TYPES):
        samples.extend(select_target_samples(pairs, form_type, samples_per_form))
    return samples


def evaluate_target_forms(
    archive_groups: Mapping[str, Sequence[TargetArchivePair]],
    split: str = "training",
    predictor: Optional[RawPredictor] = None,
    ocr: Any = None,
    samples_per_form: int = 1,
) -> list[FormEvaluation]:
    """Evaluate one or more samples for each Fintra target form type."""
    samples = _select_target_samples(archive_groups, split, samples_per_form)
    raw_results = _load_predictions_for_samples(samples, predictor, ocr)

    evaluations: list[FormEvaluation] = []
    for sample, raw_result in zip(samples, raw_results):
        predictions = parse_paddle_result(raw_result)
        record = load_label_json(sample.label_archive, sample.label_member)
        ground_truth = parse_bounding_boxes(record)
        evaluations.append(
            FormEvaluation(
                sample=sample,
                comparison=compare_predictions(predictions, ground_truth),
            )
        )

    return evaluations


def evaluate_detailed_target_forms(
    archive_groups: Mapping[str, Sequence[TargetArchivePair]],
    split: str = "training",
    predictor: Optional[RawPredictor] = None,
    ocr: Any = None,
    samples_per_form: int = 1,
) -> list[DetailedFormEvaluation]:
    """Evaluate target forms with detection, recognition, and segmentation metrics."""
    samples = _select_target_samples(archive_groups, split, samples_per_form)
    raw_results = _load_predictions_for_samples(samples, predictor, ocr)

    evaluations: list[DetailedFormEvaluation] = []
    for sample, raw_result in zip(samples, raw_results):
        predictions = parse_paddle_result(raw_result)
        record = load_label_json(sample.label_archive, sample.label_member)
        ground_truth = parse_bounding_boxes(record)
        evaluations.append(
            DetailedFormEvaluation(
                sample=sample,
                analysis=analyze_predictions(predictions, ground_truth),
            )
        )
    return evaluations
