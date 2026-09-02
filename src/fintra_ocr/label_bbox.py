"""Parsing helpers for OCR label bounding boxes."""

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Tuple, Union


@dataclass(frozen=True)
class OCRBoundingBox:
    """One OCR text annotation and its four-point coordinates."""

    annotation_id: Union[int, str]
    text: str
    x: Tuple[int, int, int, int]
    y: Tuple[int, int, int, int]
    data_type: Optional[int] = None


def _parse_coordinates(value: Any, field_name: str) -> Tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(field_name + " must contain four coordinates")
    if not all(isinstance(coordinate, int) for coordinate in value):
        raise ValueError(field_name + " coordinates must be integers")
    return tuple(value)  # type: ignore[return-value]


def parse_bounding_boxes(record: Mapping[str, Any]) -> List[OCRBoundingBox]:
    """Parse bbox records while preserving optional data_type values."""
    raw_boxes = record.get("bbox")
    if not isinstance(raw_boxes, list):
        raise ValueError("OCR label bbox must be a list")

    parsed_boxes: List[OCRBoundingBox] = []
    for index, raw_box in enumerate(raw_boxes):
        if not isinstance(raw_box, Mapping):
            raise ValueError("OCR bbox at index " + str(index) + " must be an object")

        for required_field in ("id", "data", "x", "y"):
            if required_field not in raw_box:
                raise ValueError(
                    "OCR bbox at index "
                    + str(index)
                    + " is missing "
                    + required_field
                )

        annotation_id = raw_box["id"]
        text = raw_box["data"]
        if not isinstance(annotation_id, (int, str)):
            raise ValueError("OCR bbox id must be an integer or string")
        if not isinstance(text, str):
            raise ValueError("OCR bbox data must be a string")

        data_type = raw_box.get("data_type")
        if data_type is not None and not isinstance(data_type, int):
            raise ValueError("OCR bbox data_type must be an integer when present")

        parsed_boxes.append(
            OCRBoundingBox(
                annotation_id=annotation_id,
                text=text,
                x=_parse_coordinates(raw_box["x"], "x"),
                y=_parse_coordinates(raw_box["y"], "y"),
                data_type=data_type,
            )
        )

    return parsed_boxes
