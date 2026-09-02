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
    summarize_archive_extensions,
    summarize_dataset_extensions,
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

    def test_summarize_archive_extensions_counts_non_directory_entries(self):
        with TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "sample.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("images/", "")
                archive.writestr("images/one.PNG", "image")
                archive.writestr("labels/one.json", "label")
                archive.writestr("metadata", "metadata")

            self.assertEqual(
                summarize_archive_extensions(archive_path),
                {".json": 1, ".png": 1, "[no extension]": 1},
            )

    def test_summarize_dataset_extensions_matches_current_file_types(self):
        summaries = summarize_dataset_extensions(discover_archives())

        self.assertEqual(
            summaries,
            {
                "training_source": {".png": 126326},
                "training_labels": {".json": 126326},
                "validation_source": {".png": 15785},
                "validation_labels": {".json": 15785},
            },
        )


if __name__ == "__main__":
    unittest.main()
