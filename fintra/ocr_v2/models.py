"""Immutable-ish data contracts for the isolated OCR v2 experiment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawOCRRegion:
    region_id: int
    text: str
    confidence: float | None
    polygon: list[list[float]]
    page: int = 1
    pass_name: str = "full"
    pass_index: int = 0
    source_region_index: int = 0

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
            "pass_name": self.pass_name,
            "pass_index": self.pass_index,
            "source_region_index": self.source_region_index,
        }


@dataclass(frozen=True)
class ResolvedOCRRegion:
    region_id: int
    text: str
    confidence: float | None
    polygon: list[list[float]]
    source_region_ids: list[int] = field(default_factory=list)
    duplicate_group: int | None = None
    resolution: str = "kept"
    page: int = 1

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs = [point[0] for point in self.polygon]
        ys = [point[1] for point in self.polygon]
        return min(xs), min(ys), max(xs), max(ys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.region_id,
            "text": self.text,
            "confidence": self.confidence,
            "polygon": self.polygon,
            "bbox": list(self.bbox),
            "page": self.page,
            "source_region_ids": self.source_region_ids,
            "duplicate_group": self.duplicate_group,
            "resolution": self.resolution,
        }


@dataclass(frozen=True)
class OCRV2Result:
    document_id: str
    document_type: str
    source_file: str
    image_width: int
    image_height: int
    raw_regions: list[RawOCRRegion]
    resolved_regions: list[ResolvedOCRRegion]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "source_file": self.source_file,
            "regions": [region.to_dict() for region in self.resolved_regions],
            "raw_regions": [region.to_dict() for region in self.raw_regions],
            "resolved_regions": [region.to_dict() for region in self.resolved_regions],
            "runtime": "paddle_ocr_v2_experiment",
            "metadata": self.metadata,
        }
