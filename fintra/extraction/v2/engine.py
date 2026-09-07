"""Production Clean + semantic overlay Extractor v2 orchestration."""

from __future__ import annotations

from typing import Callable

from fintra.ocr.adapter import OCRResult

from .baseline import extract_baseline
from .contract import V2Document, build_document
from .overlay import apply as apply_overlay
from .specs import DOCUMENT_FIELDS


def extract_document(result: OCRResult) -> V2Document:
    if result.document_type not in DOCUMENT_FIELDS:
        raise ValueError(f"unsupported document type: {result.document_type}")
    baseline = extract_baseline(result)
    overlaid, _diagnostics = apply_overlay(result, baseline)
    return build_document(result, overlaid)


EXTRACTORS: dict[str, Callable[[OCRResult], V2Document]] = {
    document_type: extract_document for document_type in DOCUMENT_FIELDS
}


__all__ = ["EXTRACTORS", "V2Document", "extract_document"]
