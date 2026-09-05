"""OCR backends for Fintra.

PaddleOCR is the production/MVP backend. Tesseract is intentionally provided as
an optional smoke-test backend so the pipeline can be exercised in development
environments where Paddle model packages are unavailable; Tesseract metrics must
never be presented as PaddleOCR metrics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import BytesIO
import inspect
import json
from typing import Any, Protocol

import numpy as np
from PIL import Image

from .prediction_parser import OCRPrediction


class OCRBackend(Protocol):
    name: str
    def predict_bytes(self, image_bytes: bytes) -> list[OCRPrediction]: ...


def _axis_box(points: Sequence[Sequence[float]]) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    xs = [int(round(float(point[0]))) for point in points]
    ys = [int(round(float(point[1]))) for point in points]
    if not xs or not ys:
        raise ValueError("OCR polygon is empty")
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return (left, right, right, left), (top, top, bottom, bottom)


def _unwrap_result_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the OCR payload from Paddle/PaddleX mapping wrappers.

    PaddleOCR 3.x result objects are dict-like on some releases, while their
    ``json`` representation is commonly wrapped as ``{"res": {...}}``.  Accept
    both shapes and unwrap only when the nested payload is itself a mapping.
    """
    current: Mapping[str, Any] = value
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        nested = current.get("res")
        if isinstance(nested, Mapping):
            current = nested
            continue
        break
    return current


def _mapping_from_result(result: Any) -> Mapping[str, Any]:
    # PaddleOCR/PaddleX Result objects can already be Mapping subclasses.
    # Do not return a nested {"res": ...} wrapper unchanged.
    if isinstance(result, Mapping):
        return _unwrap_result_mapping(result)

    # Some PaddleX result classes expose direct key access without formally
    # registering as collections.abc.Mapping.
    direct: dict[str, Any] = {}
    if hasattr(result, "__getitem__"):
        for key in ("rec_texts", "rec_scores", "rec_boxes", "rec_polys"):
            try:
                direct[key] = result[key]
            except (KeyError, TypeError, IndexError, AttributeError):
                pass
        if direct.get("rec_texts") is not None and direct.get("rec_scores") is not None:
            return direct

    # PaddleX result APIs vary slightly by release. ``json`` is usually a
    # property; ``to_dict``/``dict`` may be methods. ``res`` is also supported
    # because some versions expose the inner result directly.
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
            return _unwrap_result_mapping(value)

    if hasattr(result, "__dict__") and isinstance(result.__dict__, Mapping):
        return _unwrap_result_mapping(result.__dict__)
    raise ValueError(f"Unsupported PaddleOCR result object: {type(result)!r}")


def _first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    """Return first non-None value without truth-testing numpy arrays."""
    for key in keys:
        if key in mapping:
            value = mapping[key]
            if value is not None:
                return value
    return None


def _parse_mapping(mapping: Mapping[str, Any]) -> list[OCRPrediction]:
    # IMPORTANT: PaddleOCR 3.7 returns numpy.ndarray for rec_scores/rec_boxes.
    # Never use ``a or b`` here because NumPy arrays reject boolean coercion.
    mapping = _unwrap_result_mapping(mapping)
    texts = _first_present(mapping, "rec_texts", "texts")
    scores = _first_present(mapping, "rec_scores", "scores")
    boxes = _first_present(mapping, "rec_boxes", "boxes")
    polys = _first_present(mapping, "rec_polys", "polys", "dt_polys")

    if texts is None or scores is None or (boxes is None and polys is None):
        keys = ", ".join(sorted(str(key) for key in mapping.keys()))
        raise ValueError(
            "PaddleOCR result does not contain rec_texts/rec_scores/"
            f"rec_boxes(or rec_polys). Available keys: [{keys}]"
        )

    geometry = boxes if boxes is not None else polys
    if not (len(texts) == len(scores) == len(geometry)):
        raise ValueError(
            "PaddleOCR result lengths do not match: "
            f"texts={len(texts)}, scores={len(scores)}, geometry={len(geometry)}"
        )

    predictions: list[OCRPrediction] = []
    for text, score, box in zip(texts, scores, geometry):
        if boxes is not None:
            # rec_boxes in PaddleOCR 3.7 is typically an ndarray row
            # [x_min, y_min, x_max, y_max]. Older/custom outputs may provide a
            # 4-point polygon instead.
            if len(box) == 4 and not hasattr(box[0], "__len__"):
                left, top, right, bottom = [int(round(float(v))) for v in box]
                x, y = (left, right, right, left), (top, top, bottom, bottom)
            else:
                x, y = _axis_box(box)
        else:
            x, y = _axis_box(box)
        predictions.append(OCRPrediction(str(text), x, y, float(score)))
    return predictions


def parse_paddle_output(raw_result: Any) -> list[OCRPrediction]:
    """Parse PaddleOCR 3.x/PaddleX result objects and legacy nested output."""
    mapping_error: Exception | None = None
    try:
        return _parse_mapping(_mapping_from_result(raw_result))
    except (ValueError, TypeError, KeyError) as error:
        mapping_error = error

    # Legacy PaddleOCR output: [[polygon, (text, score)], ...]
    if isinstance(raw_result, Sequence) and not isinstance(raw_result, (str, bytes, np.ndarray)):
        rows = raw_result
        if len(rows) == 1 and isinstance(rows[0], Sequence):
            first = rows[0]
            if first and isinstance(first[0], Sequence) and len(first[0]) == 2:
                rows = first
        predictions: list[OCRPrediction] = []
        for row in rows:
            if not isinstance(row, Sequence) or len(row) < 2:
                continue
            polygon, rec = row[0], row[1]
            if not isinstance(rec, Sequence) or len(rec) < 2:
                continue
            x, y = _axis_box(polygon)
            predictions.append(OCRPrediction(str(rec[0]), x, y, float(rec[1])))
        if predictions:
            return predictions

    detail = f"; mapping parse error: {mapping_error}" if mapping_error else ""
    raise ValueError(
        f"Could not parse PaddleOCR output of type {type(raw_result).__name__}{detail}"
    )



def _prediction_bounds(prediction: OCRPrediction) -> tuple[int, int, int, int]:
    return min(prediction.x), min(prediction.y), max(prediction.x), max(prediction.y)


def _box_iou(first: OCRPrediction, second: OCRPrediction) -> float:
    ax1, ay1, ax2, ay2 = _prediction_bounds(first)
    bx1, by1, bx2, by2 = _prediction_bounds(second)
    iw = max(0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / (area_a + area_b - inter)


def _text_key(text: str) -> str:
    return "".join(character.casefold() for character in text if character.isalnum())


def _same_detection(first: OCRPrediction, second: OCRPrediction) -> bool:
    """Return True for overlapping duplicate OCR boxes from tiled passes."""
    iou = _box_iou(first, second)
    if iou < 0.20:
        return False
    first_key = _text_key(first.text)
    second_key = _text_key(second.text)
    if not first_key or not second_key:
        return iou >= 0.65
    if first_key == second_key:
        return iou >= 0.20
    similarity = SequenceMatcher(None, first_key, second_key).ratio()
    return iou >= 0.45 and similarity >= 0.72


def _deduplicate_predictions(predictions: Sequence[OCRPrediction]) -> list[OCRPrediction]:
    """Merge duplicate detections emitted by overlapping high-resolution tiles.

    Higher-confidence text wins.  Geometry is kept in original page coordinates.
    Different text in the same region is retained unless the boxes and strings are
    both strongly similar; this avoids deleting legitimate adjacent table cells.
    """
    ordered = sorted(predictions, key=lambda item: item.score, reverse=True)
    kept: list[OCRPrediction] = []
    for candidate in ordered:
        duplicate_index = next(
            (index for index, existing in enumerate(kept) if _same_detection(candidate, existing)),
            None,
        )
        if duplicate_index is None:
            kept.append(candidate)
            continue
        existing = kept[duplicate_index]
        # Prefer confidence; use the longer text as a tie-breaker because tiled
        # recognition often recovers a complete token where full-page OCR clips it.
        if (candidate.score, len(candidate.text.strip())) > (existing.score, len(existing.text.strip())):
            kept[duplicate_index] = candidate
    kept.sort(key=lambda item: (min(item.y), min(item.x), -item.score))
    return kept


def _offset_predictions(
    predictions: Sequence[OCRPrediction], left: int, top: int
) -> list[OCRPrediction]:
    return [
        OCRPrediction(
            text=item.text,
            x=tuple(int(value + left) for value in item.x),
            y=tuple(int(value + top) for value in item.y),
            score=item.score,
        )
        for item in predictions
    ]




def _rescale_predictions(
    predictions: Sequence[OCRPrediction], scale: float, left: int = 0, top: int = 0
) -> list[OCRPrediction]:
    """Map OCR coordinates from an upscaled crop back to page coordinates."""
    if scale <= 0:
        raise ValueError("scale must be positive")
    return [
        OCRPrediction(
            text=item.text,
            x=tuple(int(round(value / scale + left)) for value in item.x),
            y=tuple(int(round(value / scale + top)) for value in item.y),
            score=item.score,
        )
        for item in predictions
    ]

def _tile_starts(length: int, tile_size: int, overlap: int) -> list[int]:
    if length <= tile_size:
        return [0]
    stride = max(1, tile_size - overlap)
    starts = list(range(0, max(1, length - tile_size + 1), stride))
    last = max(0, length - tile_size)
    if not starts or starts[-1] != last:
        starts.append(last)
    return starts


def _focus_regions(width: int, height: int) -> list[tuple[int, int, int, int]]:
    """High-value trade-document regions for a second OCR look.

    The regular 1280px tiles can cut a long key/value line at a tile edge.  A
    smaller semantic region changes the detector/recognizer context and often
    recovers the missing tail (e.g. ``TOTAL GROSS WEIGHT : 53 KG``).  Regions
    remain generic page fractions; there is no document-id/template hardcode.
    """
    if width < 600 or height < 800:
        return []
    regions = [
        # Header metadata: invoice number/date, B/L number, shipment date.
        (int(width * 0.45), 0, width, int(height * 0.42)),
        # Footer totals/signatures: invoice total and packing gross/package total.
        (int(width * 0.42), int(height * 0.68), width, height),
        # Full-width lower table band: B/L TOTAL rows may start near page centre.
        (0, int(height * 0.48), width, int(height * 0.78)),
    ]
    output=[]
    seen=set()
    for left,top,right,bottom in regions:
        left=max(0,min(width-1,left)); top=max(0,min(height-1,top))
        right=max(left+1,min(width,right)); bottom=max(top+1,min(height,bottom))
        key=(left,top,right,bottom)
        if key not in seen and right-left>=256 and bottom-top>=192:
            seen.add(key); output.append(key)
    return output


@dataclass
class PaddleOCRBackend:
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
                "PaddleOCR is not installed. Install requirements-paddle.txt in the project's venv."
            ) from error
        if self.mode not in {"fast", "accurate"}:
            raise ValueError("PaddleOCRBackend.mode must be 'fast' or 'accurate'")
        if self.tile_size < 512:
            raise ValueError("tile_size must be at least 512 pixels")
        if self.tile_overlap < 0 or self.tile_overlap >= self.tile_size:
            raise ValueError("tile_overlap must be >= 0 and smaller than tile_size")
        if self.focus_upscale < 1.0 or self.focus_upscale > 3.0:
            raise ValueError("focus_upscale must be between 1.0 and 3.0")

        signature = inspect.signature(PaddleOCR.__init__)
        supported = set(signature.parameters)
        desired: dict[str, Any] = {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "text_detection_model_name": self.detection_model,
            "text_recognition_model_name": self.recognition_model,
            "device": self.device,
        }
        # Full A4 scans in the sample are ~1654x2340.  Paddle's detector can
        # otherwise downscale small table text aggressively.  The option is
        # filtered by the runtime signature so older PaddleOCR releases remain
        # compatible.
        if self.mode == "accurate":
            desired.update({
                "text_det_limit_side_len": 1536,
                "text_det_limit_type": "max",
            })
        if self.lang:
            desired["lang"] = self.lang
        options = {key: value for key, value in desired.items() if key in supported}
        self._ocr = PaddleOCR(**options)

    def _predict_array(self, rgb: np.ndarray) -> list[OCRPrediction]:
        raw = list(self._ocr.predict(input=rgb))
        if not raw:
            return []
        if len(raw) != 1:
            raise ValueError(f"Expected one PaddleOCR page result, received {len(raw)}")
        return parse_paddle_output(raw[0])

    def predict_bytes(self, image_bytes: bytes) -> list[OCRPrediction]:
        with Image.open(BytesIO(image_bytes)) as image:
            rgb = np.asarray(image.convert("RGB")).copy()

        if self.mode == "fast" or max(rgb.shape[:2]) < self.min_tile_dimension:
            return self._predict_array(rgb)

        height, width = rgb.shape[:2]
        predictions: list[OCRPrediction] = []

        # Keep one whole-page pass for large headings / labels that cross tile
        # boundaries, then add high-resolution overlapping tiles for small table
        # text.  Tiles are processed sequentially, so GPU VRAM usage does not
        # multiply with the number of tiles.
        predictions.extend(self._predict_array(rgb))
        x_starts = _tile_starts(width, self.tile_size, self.tile_overlap)
        y_starts = _tile_starts(height, self.tile_size, self.tile_overlap)
        for top in y_starts:
            for left in x_starts:
                crop = rgb[top:min(height, top + self.tile_size), left:min(width, left + self.tile_size)]
                if crop.shape[0] < 128 or crop.shape[1] < 128:
                    continue
                tile_predictions = self._predict_array(crop.copy())
                predictions.extend(_offset_predictions(tile_predictions, left, top))

        # Focused second-look regions mitigate tile-edge clipping on long
        # key/value lines and dense footer totals. They run sequentially and do
        # not increase peak GPU memory materially.
        for left, top, right, bottom in _focus_regions(width, height):
            crop = rgb[top:bottom, left:right]
            focused = self._predict_array(crop.copy())
            predictions.extend(_offset_predictions(focused, left, top))

            # A targeted high-resolution retry is deliberately restricted to
            # the three generic focus bands. This is materially more robust on
            # dot-matrix/faint totals (e.g. ``53 KG``) without exploding the
            # cost of upscaling the entire A4 page. Coordinates are mapped back
            # to the original image before deduplication.
            if self.focus_upscale > 1.0 and crop.shape[0] >= 160 and crop.shape[1] >= 240:
                new_w = int(round(crop.shape[1] * self.focus_upscale))
                new_h = int(round(crop.shape[0] * self.focus_upscale))
                # Keep the retry bounded on unusually large scans. Paddle's
                # detector will still apply its configured side-length limit.
                max_side = 2400
                retry_scale = self.focus_upscale
                if max(new_w, new_h) > max_side:
                    retry_scale *= max_side / max(new_w, new_h)
                    new_w = max(1, int(round(crop.shape[1] * retry_scale)))
                    new_h = max(1, int(round(crop.shape[0] * retry_scale)))
                if retry_scale > 1.05:
                    enlarged = np.asarray(
                        Image.fromarray(crop).resize((new_w, new_h), Image.Resampling.LANCZOS)
                    ).copy()
                    retry = self._predict_array(enlarged)
                    predictions.extend(_rescale_predictions(retry, retry_scale, left, top))
        return _deduplicate_predictions(predictions)


@dataclass
class TesseractOCRBackend:
    psm: int = 6
    name: str = "tesseract-smoke-only"

    def predict_bytes(self, image_bytes: bytes) -> list[OCRPrediction]:
        try:
            import pytesseract
            from pytesseract import Output
        except ImportError as error:
            raise RuntimeError("pytesseract is not installed") from error
        with Image.open(BytesIO(image_bytes)) as image:
            data = pytesseract.image_to_data(
                image, output_type=Output.DICT, config=f"--psm {self.psm}"
            )
        predictions: list[OCRPrediction] = []
        for index, text in enumerate(data["text"]):
            text = str(text).strip()
            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1.0
            if not text or confidence < 0:
                continue
            left = int(data["left"][index])
            top = int(data["top"][index])
            width = int(data["width"][index])
            height = int(data["height"][index])
            predictions.append(
                OCRPrediction(
                    text=text,
                    x=(left, left + width, left + width, left),
                    y=(top, top, top + height, top + height),
                    score=max(0.0, min(1.0, confidence / 100.0)),
                )
            )
        return predictions
