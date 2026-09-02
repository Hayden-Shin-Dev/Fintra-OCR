"""Scope rules for documents used by Fintra OCR."""

from typing import Any, Mapping

from .label_metadata import inspect_label_metadata


FINTRA_DATASET_NAME = "대규모 OCR 데이터셋 (물류)"
FINTRA_DATASET_IDENTIFIER = "IMG_OCR_6_T"
FINTRA_FORM_TYPES = frozenset({"상업송장", "포장명세서", "선하증권"})


def is_fintra_target_document(record: Mapping[str, Any]) -> bool:
    """Return whether a label record belongs to Fintra's three target documents."""
    metadata = inspect_label_metadata(record)
    return (
        metadata["dataset_name"] == FINTRA_DATASET_NAME
        and metadata["dataset_identifier"] == FINTRA_DATASET_IDENTIFIER
        and metadata["form_type"] in FINTRA_FORM_TYPES
    )
