"""Data contracts for the OCR-first capture path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OCRCaptureRegion:
    """One OCR text region with source-pass provenance preserved."""

    region_id: int
    text: str
    confidence: float | None
    polygon: list[list[float]]
    page: int = 1
    pass_name: str = "full"
    pass_index: int = 0
    source_region_index: int = 0
    origin: tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs = [point[0] for point in self.polygon]
        ys = [point[1] for point in self.polygon]
        return min(xs), min(ys), max(xs), max(ys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "text": self.text,
            "confidence": self.confidence,
            "polygon": self.polygon,
            "bbox": list(self.bbox),
            "page": self.page,
            "source_pass": {
                "name": self.pass_name,
                "index": self.pass_index,
                "source_region_index": self.source_region_index,
                "origin": [self.origin[0], self.origin[1]],
                "scale": self.scale,
            },
        }


@dataclass(frozen=True)
class OCRCaptureResult:
    """OCR-only result before any label/value or canonical-field reasoning."""

    source_file: str
    image_width: int
    image_height: int
    raw_regions: list[OCRCaptureRegion]
    normalized_regions: list[OCRCaptureRegion]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fintra-ocr-capture.v1",
            "source_file": self.source_file,
            "image": {
                "width": self.image_width,
                "height": self.image_height,
                "page_count": 1,
            },
            "raw_regions": [region.to_dict() for region in self.raw_regions],
            "normalized_regions": [region.to_dict() for region in self.normalized_regions],
            "metadata": self.metadata,
        }
