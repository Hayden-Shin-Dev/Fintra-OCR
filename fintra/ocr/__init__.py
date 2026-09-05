from .adapter import CommandOCRAdapter, FixtureOCRAdapter, OCRRegion, OCRResult
from .paddle_backend import PaddleOCRBackend, parse_paddle_result

__all__ = [
    "CommandOCRAdapter", "FixtureOCRAdapter", "OCRRegion", "OCRResult",
    "PaddleOCRBackend", "parse_paddle_result",
]
