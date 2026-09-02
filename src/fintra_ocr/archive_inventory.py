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


def summarize_archive_extensions(archive_path: Path) -> Dict[str, int]:
    """Count non-directory entries by file extension in one ZIP archive."""
    extension_counts: Dict[str, int] = {}
    with ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            extension = Path(entry.filename).suffix.lower() or "[no extension]"
            extension_counts[extension] = extension_counts.get(extension, 0) + 1

    return dict(sorted(extension_counts.items()))


def summarize_dataset_extensions(
    archive_groups: Mapping[str, Sequence[Path]],
) -> Dict[str, Dict[str, int]]:
    """Summarize file extensions across each discovered archive group."""
    summaries: Dict[str, Dict[str, int]] = {}
    for group_name, archive_paths in archive_groups.items():
        group_counts: Dict[str, int] = {}
        for archive_path in archive_paths:
            for extension, count in summarize_archive_extensions(archive_path).items():
                group_counts[extension] = group_counts.get(extension, 0) + count
        summaries[group_name] = dict(sorted(group_counts.items()))

    return summaries
