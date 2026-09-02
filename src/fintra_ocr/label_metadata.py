"""Inspection helpers for OCR label metadata sections."""

from typing import Any, Dict, Mapping, Tuple


def get_dataset_section(record: Mapping[str, Any]) -> Tuple[str, Mapping[str, Any]]:
    """Return the dataset section and its key from either known spelling."""
    for key in ("Dataset", "DataSet"):
        section = record.get(key)
        if isinstance(section, Mapping):
            return key, section

    raise KeyError("OCR label does not contain Dataset or DataSet metadata")


def inspect_label_metadata(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Return common metadata while preserving the source dataset key spelling."""
    dataset_key, dataset = get_dataset_section(record)
    images = record.get("Images")
    if not isinstance(images, Mapping):
        raise KeyError("OCR label does not contain Images metadata")

    return {
        "dataset_key": dataset_key,
        "dataset_identifier": dataset.get("identifier"),
        "dataset_name": dataset.get("name"),
        "image_identifier": images.get("identifier"),
        "form_type": images.get("form_type"),
        "image_type": images.get("type"),
        "width": images.get("width"),
        "height": images.get("height"),
        "image_metadata_keys": tuple(sorted(images)),
    }
