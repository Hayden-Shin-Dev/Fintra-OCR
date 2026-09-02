import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.label_loader import load_label_json
from fintra_ocr.paddle_annotations import (
    serialize_detection_line,
    to_detection_entries,
)
from fintra_ocr.sample_selection import select_target_sample
from fintra_ocr.target_selection import select_target_archive_pairs


class PaddleAnnotationsTest(unittest.TestCase):
    def test_converts_target_label_points_and_text(self):
        selected = select_target_archive_pairs(discover_archives())
        sample = select_target_sample(selected["training"], "상업송장")
        record = load_label_json(sample.label_archive, sample.label_member)

        entries = to_detection_entries(record)

        self.assertEqual(len(entries), len(record["bbox"]))
        self.assertEqual(entries[0]["transcription"], record["bbox"][0]["data"])
        self.assertEqual(
            entries[0]["points"],
            [
                list(point)
                for point in zip(record["bbox"][0]["x"], record["bbox"][0]["y"])
            ],
        )

    def test_serializes_one_tab_delimited_detection_line(self):
        record = {
            "bbox": [
                {
                    "id": "uuid",
                    "data": "Invoice",
                    "x": [1, 5, 5, 1],
                    "y": [2, 2, 8, 8],
                }
            ]
        }

        line = serialize_detection_line("folder\\image.png", record)
        image_path, annotation_json = line.split("\t", maxsplit=1)

        self.assertEqual(image_path, "folder/image.png")
        self.assertEqual(
            json.loads(annotation_json),
            [
                {
                    "transcription": "Invoice",
                    "points": [[1, 2], [5, 2], [5, 8], [1, 8]],
                }
            ],
        )

    def test_preserves_empty_text(self):
        record = {
            "bbox": [
                {
                    "id": "uuid",
                    "data": "",
                    "x": [1, 5, 5, 1],
                    "y": [2, 2, 8, 8],
                }
            ]
        }

        self.assertEqual(to_detection_entries(record)[0]["transcription"], "")


if __name__ == "__main__":
    unittest.main()
