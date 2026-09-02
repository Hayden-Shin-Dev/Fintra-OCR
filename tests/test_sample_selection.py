import sys
import unittest
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.label_loader import load_label_json
from fintra_ocr.sample_selection import select_target_sample
from fintra_ocr.target_scope import FINTRA_FORM_TYPES, is_fintra_target_document
from fintra_ocr.target_selection import select_target_archive_pairs


class SampleSelectionTest(unittest.TestCase):
    def test_selects_matching_sample_for_each_fintra_form_type(self):
        selected = select_target_archive_pairs(discover_archives())

        for form_type in sorted(FINTRA_FORM_TYPES):
            with self.subTest(form_type=form_type):
                sample = select_target_sample(selected["training"], form_type)
                self.assertEqual(sample.form_type, form_type)
                self.assertEqual(
                    PurePosixPath(sample.label_member).with_suffix(".png").as_posix(),
                    sample.image_member,
                )
                record = load_label_json(sample.label_archive, sample.label_member)
                self.assertTrue(is_fintra_target_document(record))

    def test_selected_sample_members_are_not_directory_entries(self):
        selected = select_target_archive_pairs(discover_archives())
        sample = select_target_sample(selected["training"], "상업송장")

        self.assertTrue(sample.image_member.lower().endswith(".png"))
        self.assertTrue(sample.label_member.lower().endswith(".json"))
        self.assertNotEqual(sample.image_member, sample.label_member)


if __name__ == "__main__":
    unittest.main()
