import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.field_extraction import extract_fields
from fintra_ocr.layout_reconstruction import reconstruct_layout
from fintra_ocr.prediction_parser import OCRPrediction


def prediction(text, left, top, right, bottom=None, score=0.9):
    bottom = top + 20 if bottom is None else bottom
    return OCRPrediction(text, (left, right, right, left), (top, top, bottom, bottom), score)


class LayoutReconstructionTest(unittest.TestCase):
    def test_reorders_detector_output_and_uses_relative_scale(self):
        predictions = [
            prediction("89", 300, 100, 325),
            prediction("GROSS", 10, 100, 80),
            prediction("KG", 330, 100, 355),
            prediction("WEIGHT", 85, 100, 160),
            prediction("next", 10, 145, 60),
        ]
        layout = reconstruct_layout(predictions)
        self.assertEqual(layout.lines[0].indices, (1, 3, 0, 2))
        self.assertEqual(layout.lines[0].text, "GROSS WEIGHT 89 KG")
        self.assertEqual(layout.lines[1].text, "next")

    def test_split_total_weight_is_extracted_without_changing_raw_indices(self):
        predictions = [
            prediction("KG", 190, 100, 215),
            prediction("89", 150, 100, 180),
            prediction("WEIGHT", 115, 100, 140),
            prediction("GROSS", 65, 100, 110),
            prediction("TOTAL", 10, 100, 60),
        ]
        field = extract_fields("포장명세서", predictions)["gross_weight"]
        self.assertEqual(field.value, "89 KG")
        self.assertEqual(field.source_indices, (1, 0))
        self.assertEqual(field.raw_text, "89 KG")


if __name__ == "__main__":
    unittest.main()
