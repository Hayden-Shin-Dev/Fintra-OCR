"""Paths for the OCR dataset stored in the project repository."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


PathInput = Union[str, Path]


@dataclass(frozen=True)
class DatasetPaths:
    """Repository-relative paths for the four OCR dataset directories."""

    project_root: Path
    ocr_root: Path
    training_source: Path
    training_labels: Path
    validation_source: Path
    validation_labels: Path

    @classmethod
    def from_project_root(
        cls, project_root: Optional[PathInput] = None
    ) -> "DatasetPaths":
        """Build dataset paths from a repository root or this package's root."""
        root = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else Path(__file__).resolve().parents[2]
        )
        ocr_root = root / "OCR"

        return cls(
            project_root=root,
            ocr_root=ocr_root,
            training_source=ocr_root / "Training" / "01.원천데이터",
            training_labels=ocr_root / "Training" / "02.라벨링데이터",
            validation_source=ocr_root / "Validation" / "01.원천데이터",
            validation_labels=ocr_root / "Validation" / "02.라벨링데이터",
        )


def get_dataset_paths(project_root: Optional[PathInput] = None) -> DatasetPaths:
    """Return repository-relative paths for the OCR dataset."""
    return DatasetPaths.from_project_root(project_root)
