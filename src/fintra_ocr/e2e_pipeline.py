"""Fintra OCR end-to-end document pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .common_schema import build_common_document_from_form_type
from .field_evidence import FieldEvidence
from .field_extraction import extract_fields
from .normalization import normalize_fields
from .ocr_backends import OCRBackend
from .prediction_parser import OCRPrediction


@dataclass(frozen=True)
class PipelineResult:
    form_type: str
    document_id: str
    predictions: tuple[OCRPrediction, ...]
    fields: Mapping[str, FieldEvidence]
    document: Mapping[str, object]


def build_document_from_predictions(
    form_type: str,
    document_id: str,
    predictions: list[OCRPrediction],
) -> PipelineResult:
    fields = extract_fields(form_type, predictions)
    normalized = normalize_fields(fields)
    document = build_common_document_from_form_type(form_type, document_id, normalized)
    return PipelineResult(form_type, document_id, tuple(predictions), normalized, document)


def run_document(
    image_bytes: bytes,
    form_type: str,
    document_id: str,
    backend: OCRBackend,
) -> PipelineResult:
    predictions = backend.predict_bytes(image_bytes)
    return build_document_from_predictions(form_type, document_id, predictions)
