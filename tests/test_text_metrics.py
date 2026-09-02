import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.text_metrics import (
    character_error_rate,
    levenshtein_distance,
    normalize_ocr_text,
    normalized_texts_match,
    text_similarity,
)


class TextMetricsTest(unittest.TestCase):
    def test_normalizes_unicode_case_and_whitespace(self):
        self.assertEqual(normalize_ocr_text("  ＩＮＶＯＩＣＥ\n"), "invoice")
        self.assertTrue(normalized_texts_match("Invoice 123", " invoice\t123 "))

    def test_calculates_levenshtein_distance_and_cer(self):
        self.assertEqual(levenshtein_distance("kitten", "sitting"), 3)
        self.assertAlmostEqual(character_error_rate("Invoice", "Invoce"), 1 / 7)

    def test_empty_reference_cer_is_explicit(self):
        self.assertEqual(character_error_rate("", ""), 0.0)
        self.assertEqual(character_error_rate("", "text"), 1.0)

    def test_text_similarity_uses_normalized_edit_distance(self):
        self.assertEqual(text_similarity("ABC", "abc"), 1.0)
        self.assertGreater(text_similarity("invoice", "invoce"), 0.8)
        self.assertLess(text_similarity("invoice", "packing"), 0.5)


if __name__ == "__main__":
    unittest.main()
