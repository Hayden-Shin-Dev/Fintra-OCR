"""Validation for source and label OCR archive names."""

from pathlib import Path
from typing import Dict, List, Sequence


def expected_label_archive_name(source_archive_name: str) -> str:
    """Return the label archive name expected for a source archive name."""
    for source_prefix, label_prefix in (("TS_", "TL_"), ("VS_", "VL_")):
        if source_archive_name.startswith(source_prefix):
            return label_prefix + source_archive_name[len(source_prefix) :]

    raise ValueError(
        "Unsupported source archive prefix: " + source_archive_name
    )


def find_archive_pairing_mismatches(
    source_archives: Sequence[Path], label_archives: Sequence[Path]
) -> Dict[str, List[str]]:
    """Return source and label archive names without a corresponding pair."""
    source_names = {archive.name for archive in source_archives}
    label_names = {archive.name for archive in label_archives}
    expected_label_names = {
        expected_label_archive_name(source_name) for source_name in source_names
    }

    return {
        "unmatched_source": sorted(
            source_name
            for source_name in source_names
            if expected_label_archive_name(source_name) not in label_names
        ),
        "unmatched_labels": sorted(
            label_name
            for label_name in label_names
            if label_name not in expected_label_names
        ),
    }
