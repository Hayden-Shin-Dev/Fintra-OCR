"""Discovery of OCR dataset ZIP archives."""

from pathlib import Path
from typing import Dict, List, Optional

from .paths import DatasetPaths, get_dataset_paths


def list_zip_archives(directory: Path) -> List[Path]:
    """Return ZIP files directly inside a directory in filename order."""
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    return sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".zip"
        ),
        key=lambda path: path.name,
    )


def discover_archives(
    dataset_paths: Optional[DatasetPaths] = None,
) -> Dict[str, List[Path]]:
    """Discover source and label ZIP archives for both dataset splits."""
    paths = dataset_paths or get_dataset_paths()
    return {
        "training_source": list_zip_archives(paths.training_source),
        "training_labels": list_zip_archives(paths.training_labels),
        "validation_source": list_zip_archives(paths.validation_source),
        "validation_labels": list_zip_archives(paths.validation_labels),
    }
