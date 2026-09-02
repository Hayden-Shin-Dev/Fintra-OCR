import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.archive_inventory import (
    count_dataset_files,
    count_files_in_archive,
)


class ArchiveInventoryTest(unittest.TestCase):
    def test_count_files_in_archive_ignores_directory_entries(self):
        with TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "sample.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("images/", "")
                archive.writestr("images/one.png", "image")
                archive.writestr("labels/one.json", "label")

            self.assertEqual(count_files_in_archive(archive_path), 2)

    def test_count_dataset_files_matches_current_dataset_totals(self):
        counts = count_dataset_files(discover_archives())

        self.assertEqual(
            counts,
            {
                "training_source": 126326,
                "training_labels": 126326,
                "validation_source": 15785,
                "validation_labels": 15785,
            },
        )


if __name__ == "__main__":
    unittest.main()
