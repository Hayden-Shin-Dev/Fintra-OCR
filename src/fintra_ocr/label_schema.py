"""Schema checks for OCR label JSON records."""

from collections.abc import Mapping
from typing import Any, List, Set


_TOP_LEVEL_REQUIRED = {"Annotation", "DataSet", "Images", "bbox"}
_TOP_LEVEL_OPTIONAL = set()
_ANNOTATION_FIELDS = {"object_recognition", "text_language"}
_DATASET_FIELDS = {
    "category",
    "identifier",
    "label_path",
    "name",
    "src_path",
    "type",
}
_IMAGE_REQUIRED_FIELDS = {
    "data_captured",
    "form_type",
    "height",
    "identifier",
    "type",
    "width",
}
_BBOX_REQUIRED_FIELDS = {"data", "id", "x", "y"}
_BBOX_OPTIONAL_FIELDS = set()


def _check_fields(
    value: Mapping[str, Any],
    required: Set[str],
    optional: Set[str],
    section_name: str,
) -> List[str]:
    errors: List[str] = []
    keys = set(value)
    for field in sorted(required - keys):
        errors.append(section_name + " is missing " + field)
    for field in sorted(keys - required - optional):
        errors.append(section_name + " contains unexpected field " + field)
    return errors


def _check_bbox(index: int, value: Any) -> List[str]:
    prefix = "bbox[" + str(index) + "]"
    if not isinstance(value, Mapping):
        return [prefix + " must be an object"]

    errors = _check_fields(
        value,
        _BBOX_REQUIRED_FIELDS,
        _BBOX_OPTIONAL_FIELDS,
        prefix,
    )
    if "id" in value and type(value["id"]) is not str:
        errors.append(prefix + ".id must be a string")
    if "data" in value and not isinstance(value["data"], str):
        errors.append(prefix + ".data must be a string")

    for coordinate_name in ("x", "y"):
        coordinates = value.get(coordinate_name)
        if not isinstance(coordinates, list) or len(coordinates) != 4:
            errors.append(prefix + "." + coordinate_name + " must contain four coordinates")
        elif not all(type(coordinate) is int for coordinate in coordinates):
            errors.append(prefix + "." + coordinate_name + " coordinates must be integers")

    return errors


def validate_label_schema(record: Any) -> List[str]:
    """Return schema errors for one OCR label record; an empty list means valid."""
    if not isinstance(record, Mapping):
        return ["top-level label must be an object"]

    errors: List[str] = []
    keys = set(record)
    for field in sorted(_TOP_LEVEL_REQUIRED - keys):
        errors.append("top-level is missing " + field)
    for field in sorted(keys - _TOP_LEVEL_REQUIRED - _TOP_LEVEL_OPTIONAL):
        errors.append("top-level contains unexpected field " + field)

    dataset = record.get("DataSet")
    if not isinstance(dataset, Mapping):
        errors.append("DataSet must be an object")
    else:
        errors.extend(_check_fields(dataset, _DATASET_FIELDS, set(), "DataSet"))

    annotation = record.get("Annotation")
    if not isinstance(annotation, Mapping):
        errors.append("Annotation must be an object")
    else:
        errors.extend(_check_fields(annotation, _ANNOTATION_FIELDS, set(), "Annotation"))

    images = record.get("Images")
    if not isinstance(images, Mapping):
        errors.append("Images must be an object")
    else:
        errors.extend(
            _check_fields(
                images,
                _IMAGE_REQUIRED_FIELDS,
                set(),
                "Images",
            )
        )

    boxes = record.get("bbox")
    if not isinstance(boxes, list):
        errors.append("bbox must be a list")
    else:
        for index, box in enumerate(boxes):
            errors.extend(_check_bbox(index, box))

    return errors
