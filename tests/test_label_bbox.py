import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.label_bbox import OCRBoundingBox, parse_bounding_boxes
from fintra_ocr.label_loader import list_json_members, load_label_json


class LabelBoundingBoxTest(unittest.TestCase):
    def test_parse_bounding_boxes_preserves_optional_data_type(self):
        record = {
            "bbox": [
                {
                    "id": 1,
                    "data": "Invoice",
                    "x": [1, 1, 10, 10],
                    "y": [2, 20, 2, 20],
                    "data_type": 1,
                },
                {
                    "id": "uuid-2",
                    "data": "number",
                    "x": [20, 20, 30, 30],
                    "y": [2, 20, 2, 20],
                },
            ]
        }

        self.assertEqual(
            parse_bounding_boxes(record),
            [
                OCRBoundingBox(1, "Invoice", (1, 1, 10, 10), (2, 20, 2, 20), 1),
                OCRBoundingBox("uuid-2", "number", (20, 20, 30, 30), (2, 20, 2, 20)),
            ],
        )

    def test_parse_bounding_boxes_reads_financial_and_logistics_samples(self):
        archives = discover_archives()["training_labels"]
        for label_archive in (archives[0], archives[14]):
            with self.subTest(label_archive=label_archive.name):
                member_name = list_json_members(label_archive)[0]
                boxes = parse_bounding_boxes(
                    load_label_json(label_archive, member_name)
                )
                self.assertGreater(len(boxes), 0)
                self.assertTrue(all(len(box.x) == 4 and len(box.y) == 4 for box in boxes))


if __name__ == "__main__":
    unittest.main()
