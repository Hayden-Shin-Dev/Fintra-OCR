import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.prediction_parser import OCRPrediction, parse_paddle_result


class PredictionParserTest(unittest.TestCase):
    def test_normalizes_text_scores_and_axis_aligned_boxes(self):
        result = {
            "rec_texts": ["Invoice", "123"],
            "rec_scores": [0.98, 0.75],
            "rec_boxes": [[10, 20, 110, 60], [10, 70, 50, 100]],
        }

        self.assertEqual(
            parse_paddle_result(result),
            [
                OCRPrediction("Invoice", (10, 110, 110, 10), (20, 20, 60, 60), 0.98),
                OCRPrediction("123", (10, 50, 50, 10), (70, 70, 100, 100), 0.75),
            ],
        )

    def test_mismatched_result_lengths_raise_value_error(self):
        with self.assertRaises(ValueError):
            parse_paddle_result(
                {
                    "rec_texts": ["one"],
                    "rec_scores": [0.9, 0.8],
                    "rec_boxes": [[0, 0, 1, 1]],
                }
            )

    def test_normalizes_numpy_arrays_from_paddle_result(self):
        result = {
            "rec_texts": ["array"],
            "rec_scores": np.array([0.91], dtype=np.float32),
            "rec_boxes": np.array([[1, 2, 11, 12]], dtype=np.int16),
        }

        predictions = parse_paddle_result(result)

        self.assertEqual(predictions[0].text, "array")
        self.assertEqual(predictions[0].x, (1, 11, 11, 1))
        self.assertEqual(predictions[0].y, (2, 2, 12, 12))
        self.assertAlmostEqual(predictions[0].score, 0.91, places=5)

    def test_missing_required_result_field_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_paddle_result(
                {"rec_texts": ["one"], "rec_scores": [0.9]}
            )


if __name__ == "__main__":
    unittest.main()
