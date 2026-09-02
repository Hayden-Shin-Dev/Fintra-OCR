import sys
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.archive_pairing import expected_label_archive_name
from fintra_ocr.target_scope import FINTRA_FORM_TYPES
from fintra_ocr.target_selection import select_target_archive_pairs


class TargetSelectionTest(unittest.TestCase):
    def test_select_target_archive_pairs_returns_five_archives_per_type(self):
        selected = select_target_archive_pairs(discover_archives())

        for split in ("training", "validation"):
            with self.subTest(split=split):
                pairs = selected[split]
                self.assertEqual(len(pairs), 15)
                self.assertEqual(
                    Counter(pair.form_type for pair in pairs),
                    Counter({
                        "상업송장": 5,
                        "포장명세서": 5,
                        "선하증권": 5,
                    }),
                )
                self.assertTrue(
                    all(pair.form_type in FINTRA_FORM_TYPES for pair in pairs)
                )

    def test_selected_pairs_use_matching_source_and_label_archive_names(self):
        selected = select_target_archive_pairs(discover_archives())

        for pairs in selected.values():
            for pair in pairs:
                with self.subTest(label_archive=pair.label_archive.name):
                    self.assertEqual(
                        expected_label_archive_name(pair.source_archive.name),
                        pair.label_archive.name,
                    )


if __name__ == "__main__":
    unittest.main()
