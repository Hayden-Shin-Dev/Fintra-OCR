"""Optional PaddleOCR backend for the Fintra canonical OCR contract.

This module is intentionally isolated from the Modern OCR runtime.  PaddleOCR
is imported only when :class:`PaddleOCRBackend` is instantiated, so the
application and Modern tests do not acquire a Paddle dependency.

The constructor options and the large-page retry policy mirror the legacy
project's Paddle implementation.  The only application-facing conversion is
to :class:`~fintra.ocr.adapter.OCRResult` / ``OCRRegion``; no field extraction
or document-specific rule is present here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import BytesIO
import inspect
import json
from pathlib import Path
from typing import Any

from .adapter import OCRRegion, OCRResult


def _as_list(value: Any) -> list[Any]:
    """Convert numpy-like or tuple-like values without importing numpy."""
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value) if isinstance(value, (list, tuple)) else []


def _unwrap_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    current = value
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        nested = current.get("res")
        if isinstance(nested, Mapping):
            current = nested
        else:
            break
    return current


def _result_mapping(result: Any) -> Mapping[str, Any]:
    if isinstance(result, Mapping):
        return _unwrap_mapping(result)

    direct: dict[str, Any] = {}
    if hasattr(result, "__getitem__"):
        for key in ("rec_texts", "rec_scores", "rec_boxes", "rec_polys"):
            try:
                direct[key] = result[key]
            except (KeyError, TypeError, IndexError, AttributeError):
                pass
        if direct.get("rec_texts") is not None:
            return direct

    for attribute in ("json", "res", "to_dict", "dict"):
        if not hasattr(result, attribute):
            continue
        value = getattr(result, attribute)
        try:
            value = value() if callable(value) else value
        except TypeError:
            continue
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                continue
        if isinstance(value, Mapping):
            return _unwrap_mapping(value)

    if isinstance(getattr(result, "__dict__", None), Mapping):
        return _unwrap_mapping(result.__dict__)
    raise ValueError(f"Unsupported PaddleOCR result object: {type(result)!r}")


def _first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _polygon(box: Any) -> list[list[float]]:
    values = _as_list(box)
    if len(values) == 4 and not isinstance(values[0], (list, tuple)):
        left, top, right, bottom = (float(value) for value in values)
        return [[left, top], [right, top], [right, bottom], [left, bottom]]
    points = []
    for point in values:
        coordinates = _as_list(point)
        if len(coordinates) < 2:
            raise ValueError("PaddleOCR geometry contains an invalid point")
        points.append([float(coordinates[0]), float(coordinates[1])])
    if not points:
        raise ValueError("PaddleOCR geometry is empty")
    return points


def _parse_mapping(mapping: Mapping[str, Any]) -> list[OCRRegion]:
    mapping = _unwrap_mapping(mapping)
    texts = _first_present(mapping, "rec_texts", "texts")
    scores = _first_present(mapping, "rec_scores", "scores")
    boxes = _first_present(mapping, "rec_boxes", "boxes")
    polygons = _first_present(mapping, "rec_polys", "polys", "dt_polys")
    geometry = boxes if boxes is not None else polygons
    if texts is None or geometry is None:
        keys = ", ".join(sorted(str(key) for key in mapping))
        raise ValueError(
            "PaddleOCR result does not contain rec_texts and rec_boxes/rec_polys; "
            f"available keys: [{keys}]"
        )

    text_values = _as_list(texts)
    geometry_values = _as_list(geometry)
    score_values = _as_list(scores) if scores is not None else [None] * len(text_values)
    if not (len(text_values) == len(score_values) == len(geometry_values)):
        raise ValueError(
            "PaddleOCR result lengths do not match: "
            f"texts={len(text_values)}, scores={len(score_values)}, geometry={len(geometry_values)}"
        )

    regions: list[OCRRegion] = []
    for index, (text, score, box) in enumerate(zip(text_values, score_values, geometry_values)):
        regions.append(
            OCRRegion(
                polygon=_polygon(box),
                text=str(text),
                confidence=None if score is None else float(score),
                index=index,
            )
        )
    return regions


def parse_paddle_result(raw_result: Any) -> list[OCRRegion]:
    """Parse PaddleOCR 3.x mappings/result objects and legacy nested output."""
    mapping_error: Exception | None = None
    try:
        return _parse_mapping(_result_mapping(raw_result))
    except (ValueError, TypeError, KeyError) as error:
        mapping_error = error

    rows = raw_result if isinstance(raw_result, Sequence) and not isinstance(raw_result, (str, bytes)) else None
    if rows is not None:
        rows = _as_list(rows)
        if len(rows) == 1 and isinstance(rows[0], Sequence):
            first = _as_list(rows[0])
            if first and isinstance(first[0], Sequence) and len(_as_list(first[0])) == 2:
                rows = first
        regions: list[OCRRegion] = []
        for index, row in enumerate(rows):
            row_values = _as_list(row)
            if len(row_values) < 2:
                continue
            rec = _as_list(row_values[1])
            if len(rec) < 2:
                continue
            regions.append(
                OCRRegion(
                    polygon=_polygon(row_values[0]),
                    text=str(rec[0]),
                    confidence=float(rec[1]),
                    index=index,
                )
            )
        if regions:
            return regions

    detail = f"; mapping parse error: {mapping_error}" if mapping_error else ""
    raise ValueError(f"Could not parse PaddleOCR result{detail}")


def _bounds(region: OCRRegion) -> tuple[float, float, float, float]:
    return region.bbox


def _iou(first: OCRRegion, second: OCRRegion) -> float:
    ax1, ay1, ax2, ay2 = _bounds(first)
    bx1, by1, bx2, by2 = _bounds(second)
    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = width * height
    if intersection <= 0:
        return 0.0
    area_a = max(1.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1.0, (bx2 - bx1) * (by2 - by1))
    return intersection / (area_a + area_b - intersection)


def _text_key(text: str) -> str:
    return "".join(character.casefold() for character in text if character.isalnum())


def _duplicate(first: OCRRegion, second: OCRRegion) -> bool:
    overlap = _iou(first, second)
    if overlap < 0.20:
        return False
    first_key, second_key = _text_key(first.text), _text_key(second.text)
    if not first_key or not second_key:
        return overlap >= 0.65
    similarity = SequenceMatcher(None, first_key, second_key).ratio()
    return overlap >= 0.20 and (first_key == second_key or (overlap >= 0.45 and similarity >= 0.72))


def _deduplicate(regions: Sequence[OCRRegion]) -> list[OCRRegion]:
    ranked = sorted(regions, key=lambda item: item.confidence if item.confidence is not None else 0.0, reverse=True)
    kept: list[OCRRegion] = []
    for candidate in ranked:
        duplicate_index = next((index for index, item in enumerate(kept) if _duplicate(candidate, item)), None)
        if duplicate_index is None:
            kept.append(candidate)
            continue
        existing = kept[duplicate_index]
        candidate_score = candidate.confidence if candidate.confidence is not None else 0.0
        existing_score = existing.confidence if existing.confidence is not None else 0.0
        if (candidate_score, len(candidate.text.strip())) > (existing_score, len(existing.text.strip())):
            kept[duplicate_index] = candidate
    return [OCRRegion(item.polygon, item.text, item.confidence, item.page, index) for index, item in enumerate(sorted(kept, key=lambda item: (item.bbox[1], item.bbox[0])))]


def _offset(regions: Sequence[OCRRegion], left: float, top: float) -> list[OCRRegion]:
    return [
        OCRRegion(
            polygon=[[x + left, y + top] for x, y in region.polygon],
            text=region.text,
            confidence=region.confidence,
            page=region.page,
            index=region.index,
        )
        for region in regions
    ]


def _rescale(regions: Sequence[OCRRegion], scale: float, left: float = 0, top: float = 0) -> list[OCRRegion]:
    return [
        OCRRegion(
            polygon=[[x / scale + left, y / scale + top] for x, y in region.polygon],
            text=region.text,
            confidence=region.confidence,
            page=region.page,
            index=region.index,
        )
        for region in regions
    ]


def _starts(length: int, tile_size: int, overlap: int) -> list[int]:
    if length <= tile_size:
        return [0]
    stride = max(1, tile_size - overlap)
    starts = list(range(0, max(1, length - tile_size + 1), stride))
    last = max(0, length - tile_size)
    if not starts or starts[-1] != last:
        starts.append(last)
    return starts


def _focus_regions(width: int, height: int) -> list[tuple[int, int, int, int]]:
    if width < 600 or height < 800:
        return []
    return [
        (int(width * 0.45), 0, width, int(height * 0.42)),
        (int(width * 0.42), int(height * 0.68), width, height),
        (0, int(height * 0.48), width, int(height * 0.78)),
    ]


def _jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return _jsonable(value.tolist())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass
class PaddleOCRBackend:
    """Legacy Paddle model configuration exposed through the V2 OCR adapter."""

    detection_model: str = "PP-OCRv6_medium_det"
    recognition_model: str = "PP-OCRv6_medium_rec"
    device: str = "cpu"
    lang: str | None = None
    mode: str = "accurate"
    tile_size: int = 1280
    tile_overlap: int = 160
    min_tile_dimension: int = 1500
    focus_upscale: float = 1.75
    name: str = "paddleocr"

    def __post_init__(self) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise RuntimeError(
                "PaddleOCR is not installed; use the isolated Paddle runtime described in runtime/paddle/README.md"
            ) from error
        if self.mode not in {"fast", "accurate"}:
            raise ValueError("mode must be 'fast' or 'accurate'")
        if self.tile_size < 512 or not 0 <= self.tile_overlap < self.tile_size:
            raise ValueError("tile_size must be >= 512 and overlap must be in [0, tile_size)")
        if not 1.0 <= self.focus_upscale <= 3.0:
            raise ValueError("focus_upscale must be between 1.0 and 3.0")

        supported = set(inspect.signature(PaddleOCR.__init__).parameters)
        desired: dict[str, Any] = {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "text_detection_model_name": self.detection_model,
            "text_recognition_model_name": self.recognition_model,
            "device": self.device,
        }
        if self.mode == "accurate":
            desired.update({"text_det_limit_side_len": 1536, "text_det_limit_type": "max"})
        if self.lang:
            desired["lang"] = self.lang
        self._ocr = PaddleOCR(**{key: value for key, value in desired.items() if key in supported})

    def _predict_array(self, image: Any) -> tuple[list[OCRRegion], Any]:
        raw_results = list(self._ocr.predict(input=image))
        if not raw_results:
            return [], None
        if len(raw_results) != 1:
            raise ValueError(f"Expected one PaddleOCR page result, got {len(raw_results)}")
        return parse_paddle_result(raw_results[0]), raw_results[0]

    def predict_bytes(self, image_bytes: bytes) -> tuple[list[OCRRegion], str]:
        from PIL import Image

        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError("numpy is required by PaddleOCR") from error
        with Image.open(BytesIO(image_bytes)) as image:
            rgb = np.asarray(image.convert("RGB")).copy()

        regions, raw = self._predict_array(rgb)
        raw_values = [_jsonable(_result_mapping(raw))] if raw is not None else []
        if self.mode == "fast" or max(rgb.shape[:2]) < self.min_tile_dimension:
            return regions, json.dumps(raw_values, ensure_ascii=False)

        height, width = rgb.shape[:2]
        all_regions = list(regions)
        raw_values = [_jsonable(_result_mapping(raw))] if raw is not None else []
        for top in _starts(height, self.tile_size, self.tile_overlap):
            for left in _starts(width, self.tile_size, self.tile_overlap):
                crop = rgb[top:min(height, top + self.tile_size), left:min(width, left + self.tile_size)]
                if crop.shape[0] < 128 or crop.shape[1] < 128:
                    continue
                tile_regions, tile_raw = self._predict_array(crop.copy())
                all_regions.extend(_offset(tile_regions, left, top))
                if tile_raw is not None:
                    raw_values.append(_jsonable(_result_mapping(tile_raw)))

        for left, top, right, bottom in _focus_regions(width, height):
            crop = rgb[top:bottom, left:right]
            focused, focused_raw = self._predict_array(crop.copy())
            all_regions.extend(_offset(focused, left, top))
            if focused_raw is not None:
                raw_values.append(_jsonable(_result_mapping(focused_raw)))
            if self.focus_upscale > 1.0 and crop.shape[0] >= 160 and crop.shape[1] >= 240:
                new_width = int(round(crop.shape[1] * self.focus_upscale))
                new_height = int(round(crop.shape[0] * self.focus_upscale))
                enlarged = np.asarray(Image.fromarray(crop).resize((new_width, new_height))).copy()
                retry, retry_raw = self._predict_array(enlarged)
                all_regions.extend(_rescale(retry, self.focus_upscale, left, top))
                if retry_raw is not None:
                    raw_values.append(_jsonable(_result_mapping(retry_raw)))

        return _deduplicate(all_regions), json.dumps(raw_values, ensure_ascii=False)

    def run_ocr(self, document_path: Path, document_type: str) -> OCRResult:
        regions, raw_output = self.predict_bytes(document_path.read_bytes())
        return OCRResult(
            document_id=document_path.stem,
            document_type=document_type,
            source_file=str(document_path),
            regions=regions,
            raw_output=raw_output,
            runtime="paddle_legacy_reference",
            metadata={
                "model_source": "legacy Fintra Paddle reference",
                "detection_model": self.detection_model,
                "recognition_model": self.recognition_model,
                "device": self.device,
                "mode": self.mode,
                "tile_size": self.tile_size,
                "tile_overlap": self.tile_overlap,
                "focus_upscale": self.focus_upscale,
                "output_regions": len(regions),
            },
        )
