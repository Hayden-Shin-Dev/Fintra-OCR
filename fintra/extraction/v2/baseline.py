"""Production Clean baseline adapter for Extractor v2.

The adapter deliberately contains no extraction logic.  It makes the frozen
Production Clean result the compatibility baseline while allowing a semantic
overlay to add only high-confidence corrections later.
"""

from __future__ import annotations

from typing import Any

from fintra.extraction.clean.engine import EXTRACTORS as CLEAN_EXTRACTORS
from fintra.ocr.adapter import OCRResult


def extract_baseline(result: OCRResult) -> dict[str, Any]:
    """Return the unchanged Production Clean payload for ``result``."""

    return CLEAN_EXTRACTORS[result.document_type](result).to_dict()


__all__ = ["extract_baseline"]
