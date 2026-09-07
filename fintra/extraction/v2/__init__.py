"""Independent Audit Field Schema v2 extractor.

This namespace is intentionally independent from the historical and current
production extractors.  It consumes an :class:`OCRResult` and emits the
fixed, evidence-bearing v2 document contract.
"""

from .engine import EXTRACTORS, extract_document

__all__ = ["EXTRACTORS", "extract_document"]
