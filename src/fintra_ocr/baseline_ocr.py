"""Minimal PaddleOCR runner for one in-memory target image."""

from io import BytesIO
from typing import Any, Optional, Sequence

import numpy as np
from PIL import Image, UnidentifiedImageError


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes into an RGB NumPy array for PaddleOCR."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return np.asarray(image.convert("RGB")).copy()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Image bytes could not be decoded") from error


def create_paddle_ocr(lang: Optional[str] = None) -> Any:
    """Create the CPU PaddleOCR pipeline used by the baseline."""
    from paddleocr import PaddleOCR

    options = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "engine": "paddle",
    }
    if lang is not None:
        options["lang"] = lang
    return PaddleOCR(**options)


def predict_image_bytes(image_bytes: bytes, ocr: Any = None) -> list[Any]:
    """Run one image through PaddleOCR and return its raw result objects."""
    image = decode_image_bytes(image_bytes)
    pipeline = ocr if ocr is not None else create_paddle_ocr()
    return list(pipeline.predict(input=image))


def predict_image_bytes_batch(
    image_bytes_list: Sequence[bytes], ocr: Any = None
) -> list[Any]:
    """Run several image byte inputs through PaddleOCR in one batch."""
    if not image_bytes_list:
        return []

    images = [decode_image_bytes(image_bytes) for image_bytes in image_bytes_list]
    pipeline = ocr if ocr is not None else create_paddle_ocr()
    return list(pipeline.predict(input=images))
