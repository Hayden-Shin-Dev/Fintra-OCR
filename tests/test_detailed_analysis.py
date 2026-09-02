import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.detailed_analysis import analyze_predictions
from fintra_ocr.label_bbox import OCRBoundingBox
from fintra_ocr.prediction_parser import OCRPrediction


def box(annotation_id, text, left, top, right, bottom):
    return OCRBoundingBox(
        annotation_id,
        text,
        (left, right, right, left),
        (top, top, bottom, bottom),
    )


class DetailedAnalysisTest(unittest.TestCase):
    def test_separates_recognition_error_from_bbox_only_text_match(self):
        ground_truth = [
            box("gt-1", "Invoice", 0, 0, 10, 10),
            box("gt-2", "Total", 40, 0, 50, 10),
        ]
        predictions = [
            OCRPrediction("Wrong", (0, 10, 10, 0), (0, 0, 10, 10), 0.9),
            OCRPrediction("Total", (70, 80, 80, 70), (0, 0, 10, 10), 0.9),
        ]

        analysis = analyze_predictions(predictions, ground_truth)

        self.assertEqual(analysis.detection.matched_count, 1)
        self.assertEqual(analysis.recognition_error_count, 1)
        self.assertEqual(analysis.iou_matched_text_exact_count, 0)
        self.assertEqual(analysis.bbox_only_exact_match_count, 1)
        self.assertEqual(analysis.text_only_exact_match_count, 1)

    def test_detects_gt_to_many_segmentation_with_recovered_text(self):
        ground_truth = [box("gt-1", "ABCD", 0, 0, 10, 10)]
        predictions = [
            OCRPrediction("AB", (0, 4, 4, 0), (0, 0, 10, 10), 0.9),
            OCRPrediction("CD", (6, 10, 10, 6), (0, 0, 10, 10), 0.9),
        ]

        analysis = analyze_predictions(predictions, ground_truth)

        self.assertEqual(analysis.detection.matched_count, 0)
        self.assertEqual(analysis.gt_to_many_case_count, 1)
        self.assertEqual(analysis.gt_to_many_text_recovered_count, 1)
        self.assertEqual(analysis.segmentation_cases[0].prediction_text, "ABCD")

    def test_detects_prediction_to_many_segmentation(self):
        ground_truth = [
            box("gt-1", "AB", 0, 0, 6, 10),
            box("gt-2", "CD", 4, 0, 10, 10),
        ]
        predictions = [
            OCRPrediction("ABCD", (0, 10, 10, 0), (0, 0, 10, 10), 0.9)
        ]

        analysis = analyze_predictions(predictions, ground_truth)

        self.assertEqual(analysis.prediction_to_many_case_count, 1)
        self.assertEqual(analysis.prediction_to_many_text_recovered_count, 1)

    def test_similarity_threshold_is_validated(self):
        with self.assertRaises(ValueError):
            analyze_predictions([], [], similarity_threshold=1.1)


if __name__ == "__main__":
    unittest.main()
