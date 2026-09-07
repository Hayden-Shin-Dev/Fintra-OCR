"""Paddle OCR capture that preserves every globalized OCR region.

The production extractor is not called here.  Accurate mode uses the same
validated Paddle model/config and pass schedule as ``PaddleOCRBackend`` but
keeps all pass-level regions before duplicate suppression in ``raw_regions``.
A second ``normalized_regions`` view applies only the existing conservative
OCR duplicate suppression; no semantic field mapping occurs.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from fintra.ocr.adapter import OCRRegion
from fintra.ocr.paddle_backend import PaddleOCRBackend, _deduplicate, _focus_regions, _starts

from .models import OCRCaptureRegion, OCRCaptureResult


def _global_polygon(
    polygon: list[list[float]],
    *,
    left: float = 0.0,
    top: float = 0.0,
    scale: float = 1.0,
) -> list[list[float]]:
    return [[float(x) / scale + left, float(y) / scale + top] for x, y in polygon]


class PaddleOCRCaptureBackend:
    """OCR-only capture wrapper around the validated Fintra Paddle backend."""

    def __init__(
        self,
        *,
        device: str = "gpu",
        mode: str = "accurate",
        backend: Any | None = None,
    ) -> None:
        self.backend = backend or PaddleOCRBackend(device=device, mode=mode)

    def run_bytes(self, image_bytes: bytes, *, source_file: str = "uploaded-image") -> OCRCaptureResult:
        from PIL import Image

        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError("numpy is required by the Paddle OCR capture path") from error

        with Image.open(BytesIO(image_bytes)) as image:
            rgb = np.asarray(image.convert("RGB")).copy()
        height, width = rgb.shape[:2]

        raw_regions: list[OCRCaptureRegion] = []
        global_regions: list[OCRRegion] = []
        pass_counter = 0

        def capture_pass(
            image_array: Any,
            *,
            pass_name: str,
            left: float = 0.0,
            top: float = 0.0,
            scale: float = 1.0,
        ) -> None:
            nonlocal pass_counter
            regions, _ = self.backend._predict_array(image_array)
            current_pass = pass_counter
            pass_counter += 1
            for region in regions:
                polygon = _global_polygon(region.polygon, left=left, top=top, scale=scale)
                capture = OCRCaptureRegion(
                    region_id=len(raw_regions),
                    text=region.text,
                    confidence=region.confidence,
                    polygon=polygon,
                    page=region.page,
                    pass_name=pass_name,
                    pass_index=current_pass,
                    source_region_index=region.index,
                    origin=(float(left), float(top)),
                    scale=float(scale),
                )
                raw_regions.append(capture)
                global_regions.append(
                    OCRRegion(
                        polygon=polygon,
                        text=region.text,
                        confidence=region.confidence,
                        page=region.page,
                        index=len(global_regions),
                    )
                )

        capture_pass(rgb, pass_name="full")

        mode = getattr(self.backend, "mode", "fast")
        min_tile_dimension = int(getattr(self.backend, "min_tile_dimension", 1500))
        if mode == "accurate" and max(height, width) >= min_tile_dimension:
            tile_size = int(getattr(self.backend, "tile_size", 1280))
            tile_overlap = int(getattr(self.backend, "tile_overlap", 160))
            for top in _starts(height, tile_size, tile_overlap):
                for left in _starts(width, tile_size, tile_overlap):
                    crop = rgb[top:min(height, top + tile_size), left:min(width, left + tile_size)]
                    if crop.shape[0] < 128 or crop.shape[1] < 128:
                        continue
                    capture_pass(crop.copy(), pass_name="tile", left=left, top=top)

            focus_upscale = float(getattr(self.backend, "focus_upscale", 1.75))
            for left, top, right, bottom in _focus_regions(width, height):
                crop = rgb[top:bottom, left:right]
                capture_pass(crop.copy(), pass_name="focus", left=left, top=top)
                if focus_upscale > 1.0 and crop.shape[0] >= 160 and crop.shape[1] >= 240:
                    new_width = int(round(crop.shape[1] * focus_upscale))
                    new_height = int(round(crop.shape[0] * focus_upscale))
                    enlarged = np.asarray(Image.fromarray(crop).resize((new_width, new_height))).copy()
                    capture_pass(
                        enlarged,
                        pass_name="focus_upscaled",
                        left=left,
                        top=top,
                        scale=focus_upscale,
                    )

        normalized_ocr = _deduplicate(global_regions)
        normalized_regions = [
            OCRCaptureRegion(
                region_id=index,
                text=region.text,
                confidence=region.confidence,
                polygon=region.polygon,
                page=region.page,
                pass_name="normalized",
                pass_index=0,
                source_region_index=region.index,
            )
            for index, region in enumerate(normalized_ocr)
        ]

        metadata = {
            "runtime": "paddle_ocr_first_capture",
            "semantic_extraction": False,
            "field_mapping": False,
            "device": getattr(self.backend, "device", "unknown"),
            "mode": mode,
            "detection_model": getattr(self.backend, "detection_model", "unknown"),
            "recognition_model": getattr(self.backend, "recognition_model", "unknown"),
            "tile_size": getattr(self.backend, "tile_size", None),
            "tile_overlap": getattr(self.backend, "tile_overlap", None),
            "focus_upscale": getattr(self.backend, "focus_upscale", None),
            "ocr_pass_count": pass_counter,
            "raw_region_count": len(raw_regions),
            "normalized_region_count": len(normalized_regions),
        }
        return OCRCaptureResult(
            source_file=source_file,
            image_width=width,
            image_height=height,
            raw_regions=raw_regions,
            normalized_regions=normalized_regions,
            metadata=metadata,
        )

    def run_path(self, path: Path) -> OCRCaptureResult:
        return self.run_bytes(path.read_bytes(), source_file=str(path))
