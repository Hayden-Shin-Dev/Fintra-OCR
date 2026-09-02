import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.comparison import (
    bounding_box_iou,
    compare_predictions,
    match_bounding_boxes,
)
from fintra_ocr.label_bbox import OCRBoundingBox
from fintra_ocr.prediction_parser import OCRPrediction


class ComparisonTest(unittest.TestCase):
    def test_matches_boxes_and_counts_exact_text(self):
        ground_truth = [
            OCRBoundingBox("gt-1", "Invoice", (0, 10, 10, 0), (0, 0, 10, 10))
        ]
        predictions = [
            OCRPrediction("Invoice", (1, 9, 9, 1), (1, 1, 9, 9), 0.99),
            OCRPrediction("noise", (20, 30, 30, 20), (20, 20, 30, 30), 0.50),
        ]

        comparison = compare_predictions(predictions, ground_truth)

        self.assertEqual(comparison.ground_truth_count, 1)
        self.assertEqual(comparison.prediction_count, 2)
        self.assertEqual(comparison.matched_count, 1)
        self.assertEqual(comparison.exact_text_match_count, 1)
        self.assertEqual(comparison.precision, 0.5)
        self.assertEqual(comparison.recall, 1.0)

    def test_iou_threshold_controls_box_matching(self):
        ground_truth = [
            OCRBoundingBox("gt-1", "Invoice", (0, 10, 10, 0), (0, 0, 10, 10))
        ]
        predictions = [
            OCRPrediction("Invoice", (5, 15, 15, 5), (5, 5, 15, 15), 0.80)
        ]

        comparison = compare_predictions(predictions, ground_truth, iou_threshold=0.6)

        self.assertEqual(comparison.matched_count, 0)
        self.assertEqual(comparison.exact_text_match_count, 0)

    def test_empty_inputs_have_zero_precision_and_recall(self):
        comparison = compare_predictions([], [])

        self.assertEqual(comparison.matched_count, 0)
        self.assertEqual(comparison.precision, 0.0)
        self.assertEqual(comparison.recall, 0.0)

    def test_exposes_indices_and_iou_for_matching_boxes(self):
        ground_truth = [
            OCRBoundingBox("gt-1", "Invoice", (0, 10, 10, 0), (0, 0, 10, 10))
        ]
        predictions = [
            OCRPrediction("Invoice", (1, 9, 9, 1), (1, 1, 9, 9), 0.99)
        ]

        matches = match_bounding_boxes(predictions, ground_truth)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].ground_truth_index, 0)
        self.assertEqual(matches[0].prediction_index, 0)
        self.assertEqual(matches[0].iou, bounding_box_iou(ground_truth[0], predictions[0]))


if __name__ == "__main__":
    unittest.main()
