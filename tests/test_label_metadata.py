import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.label_loader import list_json_members, load_label_json
from fintra_ocr.label_metadata import get_dataset_section, inspect_label_metadata


class LabelMetadataTest(unittest.TestCase):
    def test_get_dataset_section_accepts_both_dataset_key_spellings(self):
        for key in ("Dataset", "DataSet"):
            with self.subTest(key=key):
                section_key, section = get_dataset_section({key: {"type": 1}})
                self.assertEqual(section_key, key)
                self.assertEqual(section["type"], 1)

    def test_inspect_label_metadata_normalizes_common_fields(self):
        record = {
            "DataSet": {"identifier": "dataset-id", "name": "dataset-name"},
            "Images": {
                "identifier": "image-id",
                "form_type": "상업송장",
                "type": "PNG",
                "width": 100,
                "height": 200,
            },
        }

        metadata = inspect_label_metadata(record)

        self.assertEqual(metadata["dataset_key"], "DataSet")
        self.assertEqual(metadata["dataset_identifier"], "dataset-id")
        self.assertEqual(metadata["image_identifier"], "image-id")
        self.assertEqual(metadata["form_type"], "상업송장")
        self.assertEqual(metadata["width"], 100)
        self.assertEqual(metadata["height"], 200)

    def test_inspect_financial_and_logistics_dataset_metadata(self):
        archives = discover_archives()["training_labels"]
        selected_archives = [archives[0], archives[14]]

        for label_archive in selected_archives:
            with self.subTest(label_archive=label_archive.name):
                member_name = list_json_members(label_archive)[0]
                metadata = inspect_label_metadata(
                    load_label_json(label_archive, member_name)
                )
                self.assertIn(metadata["dataset_key"], {"Dataset", "DataSet"})
                self.assertIsInstance(metadata["image_identifier"], str)
                self.assertIsInstance(metadata["form_type"], str)
                self.assertIsInstance(metadata["width"], int)
                self.assertIsInstance(metadata["height"], int)


if __name__ == "__main__":
    unittest.main()
