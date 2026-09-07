"""OCR-first capture path for Fintra v2 experiments.

This namespace is intentionally independent from field extraction.  It only
captures OCR text, geometry and confidence so later layout/semantic stages can
be designed without losing source evidence.
"""

from .models import OCRCaptureRegion, OCRCaptureResult
from .paddle_capture import PaddleOCRCaptureBackend

__all__ = ["OCRCaptureRegion", "OCRCaptureResult", "PaddleOCRCaptureBackend"]
