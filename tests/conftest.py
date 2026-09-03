"""Pytest behavior for the public Fintra repository.

The ~170 GB OCR corpus is intentionally not versioned. Tests that assert the
private corpus inventory or open real archive members are skipped when that
corpus is absent; all fixture/unit tests still run. On the original development
machine, where OCR/ exists, those integration tests run normally.
"""

from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


_DATASET_DEPENDENT_MODULES = {
    "test_archive_discovery.py",
    "test_archive_inventory.py",
    "test_archive_pairing.py",
    "test_baseline_evaluation.py",
    "test_baseline_ocr.py",
    "test_image_loader.py",
    "test_label_bbox.py",
    "test_label_loader.py",
    "test_label_metadata.py",
    "test_member_pairing.py",
    "test_paddle_annotations.py",
    "test_paths.py",
    "test_sample_selection.py",
    "test_target_selection.py",
}


def _private_dataset_present(project_root: Path) -> bool:
    required = (
        project_root / "OCR" / "Training" / "01.원천데이터",
        project_root / "OCR" / "Training" / "02.라벨링데이터",
        project_root / "OCR" / "Validation" / "01.원천데이터",
        project_root / "OCR" / "Validation" / "02.라벨링데이터",
    )
    return all(path.is_dir() for path in required)


def pytest_collection_modifyitems(config, items):
    project_root = Path(__file__).resolve().parents[1]
    if _private_dataset_present(project_root):
        return
    marker = pytest.mark.skip(
        reason="private OCR corpus is not included in the repository; fixture/unit coverage still runs"
    )
    for item in items:
        if Path(str(item.fspath)).name in _DATASET_DEPENDENT_MODULES:
            item.add_marker(marker)
