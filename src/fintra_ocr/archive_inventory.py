"""Inventory of files stored inside OCR dataset ZIP archives."""

from pathlib import Path
from typing import Dict, Mapping, Sequence
from zipfile import ZipFile


def count_files_in_archive(archive_path: Path) -> int:
    """Count non-directory entries in one ZIP archive without extracting it."""
    with ZipFile(archive_path) as archive:
        return sum(1 for entry in archive.infolist() if not entry.is_dir())


def count_files_in_archives(archive_paths: Sequence[Path]) -> int:
    """Count non-directory entries across a sequence of ZIP archives."""
    return sum(count_files_in_archive(path) for path in archive_paths)


def count_dataset_files(
    archive_groups: Mapping[str, Sequence[Path]],
) -> Dict[str, int]:
    """Count files for each discovered dataset archive group."""
    return {
        group_name: count_files_in_archives(archive_paths)
        for group_name, archive_paths in archive_groups.items()
    }
