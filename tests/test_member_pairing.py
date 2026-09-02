import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.member_pairing import find_member_pairing_mismatches


class MemberPairingTest(unittest.TestCase):
    def test_member_pairing_reports_missing_and_duplicate_basenames(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            image_archive = directory / "images.zip"
            label_archive = directory / "labels.zip"
            with ZipFile(image_archive, "w") as archive:
                archive.writestr("one.png", "image")
                archive.writestr("one.png", "duplicate")
                archive.writestr("image_only.png", "image")
            with ZipFile(label_archive, "w") as archive:
                archive.writestr("one.json", "{}")
                archive.writestr("label_only.json", "{}")

            mismatches = find_member_pairing_mismatches(image_archive, label_archive)

        self.assertEqual(
            mismatches,
            {
                "missing_labels": ["image_only"],
                "missing_images": ["label_only"],
                "duplicate_images": ["one"],
                "duplicate_labels": [],
            },
        )

    def test_target_commercial_invoice_members_are_paired(self):
        archives = discover_archives()
        image_archive = next(
            archive
            for archive in archives["training_source"]
            if archive.name.endswith("INV01.zip")
        )
        label_archive = next(
            archive
            for archive in archives["training_labels"]
            if archive.name.endswith("INV01.zip")
        )

        self.assertEqual(
            find_member_pairing_mismatches(image_archive, label_archive),
            {
                "missing_labels": [],
                "missing_images": [],
                "duplicate_images": [],
                "duplicate_labels": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
