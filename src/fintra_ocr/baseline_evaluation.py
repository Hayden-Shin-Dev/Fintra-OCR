"""Evaluate one baseline sample for each Fintra target document type."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from .comparison import OCRComparison, compare_predictions
from .image_loader import load_image_bytes
from .label_bbox import parse_bounding_boxes
from .label_loader import load_label_json
from .prediction_parser import parse_paddle_result
from .sample_selection import TargetSample, select_target_sample
from .target_scope import FINTRA_FORM_TYPES
from .target_selection import TargetArchivePair


RawPredictor = Callable[[bytes], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class FormEvaluation:
    """Comparison result for one target form type sample."""

    sample: TargetSample
    comparison: OCRComparison


def evaluate_target_forms(
    archive_groups: Mapping[str, Sequence[TargetArchivePair]],
    split: str = "training",
    predictor: Optional[RawPredictor] = None,
    ocr: Any = None,
) -> list[FormEvaluation]:
    """Evaluate one sample for each of the three Fintra target form types."""
    if predictor is None:
        from .baseline_ocr import create_paddle_ocr, predict_image_bytes

        pipeline = ocr if ocr is not None else create_paddle_ocr()

        def predictor(image_bytes: bytes) -> Sequence[Mapping[str, Any]]:
            return predict_image_bytes(image_bytes, ocr=pipeline)

    pairs = archive_groups[split]
    evaluations: list[FormEvaluation] = []
    for form_type in sorted(FINTRA_FORM_TYPES):
        sample = select_target_sample(pairs, form_type)
        image_bytes = load_image_bytes(sample.source_archive, sample.image_member)
        raw_results = list(predictor(image_bytes))
        if not raw_results:
            raise ValueError(f"PaddleOCR returned no result for {form_type!r}")

        predictions = parse_paddle_result(raw_results[0])
        record = load_label_json(sample.label_archive, sample.label_member)
        ground_truth = parse_bounding_boxes(record)
        evaluations.append(
            FormEvaluation(
                sample=sample,
                comparison=compare_predictions(predictions, ground_truth),
            )
        )

    return evaluations
