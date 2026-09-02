"""Validation for PNG and JSON members inside target document archives."""

from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Dict, List
from zipfile import ZipFile


def _member_stems(archive_path: Path, extension: str) -> List[str]:
    with ZipFile(archive_path) as archive:
        return [
            PurePosixPath(entry.filename).stem
            for entry in archive.infolist()
            if not entry.is_dir() and entry.filename.lower().endswith(extension)
        ]


def find_member_pairing_mismatches(
    image_archive: Path, label_archive: Path
) -> Dict[str, List[str]]:
    """Compare PNG and JSON basenames in two corresponding ZIP archives."""
    image_stems = _member_stems(image_archive, ".png")
    label_stems = _member_stems(label_archive, ".json")
    image_counts = Counter(image_stems)
    label_counts = Counter(label_stems)
    image_names = set(image_counts)
    label_names = set(label_counts)

    return {
        "missing_labels": sorted(image_names - label_names),
        "missing_images": sorted(label_names - image_names),
        "duplicate_images": sorted(
            name for name, count in image_counts.items() if count > 1
        ),
        "duplicate_labels": sorted(
            name for name, count in label_counts.items() if count > 1
        ),
    }
