"""Isolated OCR v2 experiment.

The package is deliberately not imported by the production OCR or extractor
dispatch.  It preserves pass-level raw evidence and builds a separate resolved
view for benchmark experiments.
"""

from .backend import OCRV2Backend, OCRV2Config
from .models import OCRV2Result, RawOCRRegion, ResolvedOCRRegion

__all__ = ["OCRV2Backend", "OCRV2Config", "OCRV2Result", "RawOCRRegion", "ResolvedOCRRegion"]
