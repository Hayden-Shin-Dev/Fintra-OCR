"""Convert target labels to PaddleOCR text-detection annotations."""

import json
from pathlib import PurePosixPath
from typing import Any, Mapping

from .label_bbox import parse_bounding_boxes


def to_detection_entries(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convert target bbox labels to PaddleOCR points/transcription entries."""
    entries: list[dict[str, Any]] = []
    for box in parse_bounding_boxes(record):
        entries.append(
            {
                "transcription": box.text,
                "points": [
                    [x, y]
                    for x, y in zip(box.x, box.y)
                ],
            }
        )
    return entries


def serialize_detection_line(
    image_path: str, record: Mapping[str, Any]
) -> str:
    """Serialize one PaddleOCR detection annotation line."""
    normalized_path = PurePosixPath(image_path.replace("\\", "/")).as_posix()
    annotations = json.dumps(
        to_detection_entries(record), ensure_ascii=False, separators=(",", ":")
    )
    return normalized_path + "\t" + annotations
