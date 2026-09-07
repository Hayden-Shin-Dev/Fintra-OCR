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
    overlaid, diagnostics = apply_overlay(result, baseline)
    metadata = dict(overlaid.get("metadata") or {})
    metadata["v2_title_diagnostics"] = diagnostics.get("title_diagnostics", [])
    metadata["v2_overrides"] = diagnostics.get("overrides", [])
    overlaid["metadata"] = metadata
    return build_document(result, overlaid)


EXTRACTORS: dict[str, Callable[[OCRResult], V2Document]] = {
    document_type: extract_document for document_type in DOCUMENT_FIELDS
}


__all__ = ["EXTRACTORS", "V2Document", "extract_document"]
