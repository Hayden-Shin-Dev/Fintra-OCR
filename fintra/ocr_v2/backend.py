"""Standalone Paddle OCR v2 backend.

Model names and production pass geometry intentionally match the frozen
reference.  The difference is only the isolated raw-evidence contract and
post-processing resolver; this module is not imported by production dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import inspect
from pathlib import Path
from typing import Any

from .merge import resolve
from .models import OCRV2Result, RawOCRRegion


@dataclass(frozen=True)
class OCRV2Config:
    detection_model: str = "PP-OCRv6_medium_det"
    recognition_model: str = "PP-OCRv6_medium_rec"
    device: str = "gpu"
    mode: str = "accurate"
    tile_size: int = 1280
    tile_overlap: int = 160
    min_tile_dimension: int = 1500
    focus_upscale: float = 1.75


def _polygon(value: Any) -> list[list[float]]:
    values = value.tolist() if hasattr(value, "tolist") else value
    if len(values) == 4 and not isinstance(values[0], (list, tuple)):
        left, top, right, bottom = [float(item) for item in values]
        return [[left, top], [right, top], [right, bottom], [left, bottom]]
    return [[float(point[0]), float(point[1])] for point in values]


def _mapping(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result.get("res", result)
    if hasattr(result, "json"):
        value = result.json() if callable(result.json) else result.json
        if isinstance(value, str):
            import json
            value = json.loads(value)
        return value.get("res", value)
    direct = {}
    for key in ("rec_texts", "rec_scores", "rec_boxes", "rec_polys"):
        try:
            direct[key] = result[key]
        except (KeyError, TypeError, IndexError, AttributeError):
            pass
    return direct


def _parse(result: Any) -> list[tuple[str, float | None, list[list[float]]]]:
    mapping = _mapping(result)
    texts = mapping.get("rec_texts", mapping.get("texts", []))
    scores = mapping.get("rec_scores", mapping.get("scores"))
    boxes = mapping.get("rec_boxes", mapping.get("boxes", mapping.get("rec_polys", mapping.get("polys"))))
    texts = texts.tolist() if hasattr(texts, "tolist") else list(texts)
    boxes = boxes.tolist() if hasattr(boxes, "tolist") else list(boxes)
    if scores is None:
        scores = [None] * len(texts)
    scores = scores.tolist() if hasattr(scores, "tolist") else list(scores)
    if len(texts) != len(boxes):
        raise ValueError(f"Paddle v2 result length mismatch: texts={len(texts)} boxes={len(boxes)}")
    return [(str(text), None if score is None else float(score), _polygon(box))
            for text, score, box in zip(texts, scores, boxes)]


def _offset(polygon: list[list[float]], left: float, top: float, scale: float = 1.0) -> list[list[float]]:
    return [[float(x) / scale + left, float(y) / scale + top] for x, y in polygon]


def _starts(length: int, tile_size: int, overlap: int) -> list[int]:
    if length <= tile_size:
        return [0]
    stride = max(1, tile_size - overlap)
    starts = list(range(0, max(1, length - tile_size + 1), stride))
    last = max(0, length - tile_size)
    if starts[-1] != last:
        starts.append(last)
    return starts


def _focus_regions(width: int, height: int) -> list[tuple[int, int, int, int]]:
    if width < 600 or height < 800:
        return []
    return [(int(width * 0.45), 0, width, int(height * 0.42)),
            (int(width * 0.42), int(height * 0.68), width, height),
            (0, int(height * 0.48), width, int(height * 0.78))]


class OCRV2Backend:
    def __init__(self, config: OCRV2Config | None = None) -> None:
        self.config = config or OCRV2Config()
        if self.config.mode not in {"fast", "accurate"}:
            raise ValueError("mode must be fast or accurate")
        from paddleocr import PaddleOCR
        supported = set(inspect.signature(PaddleOCR.__init__).parameters)
        desired: dict[str, Any] = {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "text_detection_model_name": self.config.detection_model,
            "text_recognition_model_name": self.config.recognition_model,
            "device": self.config.device,
        }
        if self.config.mode == "accurate":
            desired.update({"text_det_limit_side_len": 1536, "text_det_limit_type": "max"})
        self.ocr = PaddleOCR(**{key: value for key, value in desired.items() if key in supported})

    def _predict(self, image: Any) -> list[tuple[str, float | None, list[list[float]]]]:
        results = list(self.ocr.predict(input=image))
        if not results:
            return []
        return _parse(results[0])

    def run_path(self, image_path: Path, *, document_id: str, document_type: str) -> OCRV2Result:
        from PIL import Image
        import numpy as np
        with Image.open(image_path) as image:
            rgb = np.asarray(image.convert("RGB")).copy()
        height, width = rgb.shape[:2]
        raw: list[RawOCRRegion] = []
        pass_index = 0
        pass_region_counts: dict[str, int] = {}

        def capture(array: Any, pass_name: str, left: float = 0.0, top: float = 0.0, scale: float = 1.0) -> None:
            nonlocal pass_index
            before = len(raw)
            for source_index, (text, confidence, polygon) in enumerate(self._predict(array)):
                raw.append(RawOCRRegion(len(raw), text, confidence, _offset(polygon, left, top, scale),
                                        1, pass_name, pass_index, source_index))
            pass_region_counts[pass_name] = pass_region_counts.get(pass_name, 0) + len(raw) - before
            pass_index += 1

        capture(rgb, "full")
        if self.config.mode == "accurate" and max(height, width) >= self.config.min_tile_dimension:
            for top in _starts(height, self.config.tile_size, self.config.tile_overlap):
                for left in _starts(width, self.config.tile_size, self.config.tile_overlap):
                    crop = rgb[top:min(height, top + self.config.tile_size), left:min(width, left + self.config.tile_size)]
                    if crop.shape[0] >= 128 and crop.shape[1] >= 128:
                        capture(crop.copy(), "tile", left, top)
            for left, top, right, bottom in _focus_regions(width, height):
                crop = rgb[top:bottom, left:right]
                capture(crop.copy(), "focus", left, top)
                if self.config.focus_upscale > 1.0 and crop.shape[0] >= 160 and crop.shape[1] >= 240:
                    enlarged = np.asarray(Image.fromarray(crop).resize((int(round(crop.shape[1] * self.config.focus_upscale)), int(round(crop.shape[0] * self.config.focus_upscale)))))
                    capture(enlarged, "focus_upscaled", left, top, self.config.focus_upscale)
        resolved, stats = resolve(raw)
        metadata = {
            "detection_model": self.config.detection_model,
            "recognition_model": self.config.recognition_model,
            "device": self.config.device,
            "mode": self.config.mode,
            "tile_size": self.config.tile_size,
            "tile_overlap": self.config.tile_overlap,
            "focus_upscale": self.config.focus_upscale,
            "ocr_pass_count": pass_index,
            "pass_region_counts": pass_region_counts,
            "raw_region_count": len(raw),
            **stats,
        }
        return OCRV2Result(document_id, document_type, str(image_path), width, height, raw, resolved, metadata)
