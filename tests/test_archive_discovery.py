import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives, list_zip_archives


class ArchiveDiscoveryTest(unittest.TestCase):
    def test_list_zip_archives_returns_only_sorted_zip_files(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "b.zip").touch()
            (directory / "a.ZIP").touch()
            (directory / "ignored.json").touch()

            archives = list_zip_archives(directory)

        self.assertEqual([archive.name for archive in archives], ["a.ZIP", "b.zip"])

    def test_discover_archives_finds_all_dataset_archive_groups(self):
        archives = discover_archives()

        self.assertEqual(
            set(archives),
            {
                "training_source",
                "training_labels",
                "validation_source",
                "validation_labels",
            },
        )
        for archive_group in archives.values():
            with self.subTest(archive_group=archive_group):
                self.assertEqual(len(archive_group), 34)
                self.assertEqual(
                    [archive.name for archive in archive_group],
                    sorted(archive.name for archive in archive_group),
                )


if __name__ == "__main__":
    unittest.main()
