import unittest

from scripts.evaluate_ocr_stages import _e2e_metric, _field_base, _fuzzy_similarity, _join_reading_order


class OcrStageMetricTests(unittest.TestCase):
    def test_e2e_metric_uses_exact_text_for_precision_and_recall(self):
        metric = {
            "gt_regions": 4,
            "predicted_regions": 5,
            "matched_regions": 3,
            "exact_text_matches": 2,
            "normalized_text_matches": 2,
            "character_score_on_matched": 0.8,
            "cer_on_matched": 0.2,
            "matches": [],
        }
        result = _e2e_metric(metric)
        self.assertEqual(result["matched_regions"], 2)
        self.assertEqual(result["false_positive_regions"], 3)
        self.assertEqual(result["missed_regions"], 2)
        self.assertAlmostEqual(result["precision"], 2 / 5)
        self.assertAlmostEqual(result["recall"], 2 / 4)

    def test_reading_order_joins_regions_on_same_and_multiple_lines(self):
        regions = [
            {"box": (20, 10, 30, 20), "text": "WORLD"},
            {"box": (0, 10, 10, 20), "text": "HELLO"},
            {"box": (0, 40, 10, 50), "text": "NEXT"},
        ]
        self.assertEqual(_join_reading_order(regions), "HELLO WORLD NEXT")

    def test_field_base_and_fuzzy_similarity(self):
        self.assertEqual(_field_base("items[12].quantity"), "quantity")
        similarity, cer = _fuzzy_similarity("ABC-123", "ABC-12B")
        self.assertGreater(similarity, 0.8)
        self.assertGreater(cer, 0.0)


if __name__ == "__main__":
    unittest.main()
