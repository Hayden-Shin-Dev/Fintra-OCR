import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.archive_pairing import (
    expected_label_archive_name,
    find_archive_pairing_mismatches,
)


class ArchivePairingTest(unittest.TestCase):
    def test_expected_label_name_replaces_training_and_validation_prefixes(self):
        self.assertEqual(
            expected_label_archive_name("TS_금융_1.은행_1-1.신고서.zip"),
            "TL_금융_1.은행_1-1.신고서.zip",
        )
        self.assertEqual(
            expected_label_archive_name("VS_물류_1.상업송장_INV01.zip"),
            "VL_물류_1.상업송장_INV01.zip",
        )

    def test_pairing_reports_missing_and_extra_archives(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_archives = [
                directory / "TS_a.zip",
                directory / "TS_missing.zip",
            ]
            label_archives = [
                directory / "TL_a.zip",
                directory / "TL_extra.zip",
            ]

        self.assertEqual(
            find_archive_pairing_mismatches(source_archives, label_archives),
            {
                "unmatched_source": ["TS_missing.zip"],
                "unmatched_labels": ["TL_extra.zip"],
            },
        )

    def test_training_and_validation_archive_pairing_has_no_mismatches(self):
        archives = discover_archives()

        for split in ("training", "validation"):
            with self.subTest(split=split):
                mismatches = find_archive_pairing_mismatches(
                    archives[split + "_source"],
                    archives[split + "_labels"],
                )
                self.assertEqual(mismatches, {
                    "unmatched_source": [],
                    "unmatched_labels": [],
                })


if __name__ == "__main__":
    unittest.main()
