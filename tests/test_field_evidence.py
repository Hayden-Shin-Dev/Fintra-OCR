import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.field_evidence import make_field_evidence, missing_field
from fintra_ocr.prediction_parser import OCRPrediction


class FieldEvidenceTest(unittest.TestCase):
    def test_combines_source_predictions_and_preserves_evidence(self):
        predictions = [
            OCRPrediction("123", (30, 50, 50, 30), (10, 10, 20, 20), 0.91),
            OCRPrediction("INV-", (10, 30, 30, 10), (10, 10, 20, 20), 0.97),
        ]

        evidence = make_field_evidence(
            "invoice_no", predictions, (0, 1), "INV-123"
        )

        self.assertEqual(evidence.value, "INV-123")
        self.assertEqual(evidence.raw_text, "INV- 123")
        self.assertEqual(evidence.bbox, ((10, 10), (50, 10), (50, 20), (10, 20)))
        self.assertEqual(evidence.confidence, 0.91)
        self.assertEqual(evidence.source_indices, (1, 0))
        self.assertEqual(evidence.status, "found")

    def test_missing_field_has_no_fabricated_evidence(self):
        evidence = missing_field("buyer", "no deterministic candidate")

        self.assertIsNone(evidence.value)
        self.assertEqual(evidence.raw_text, "")
        self.assertIsNone(evidence.bbox)
        self.assertEqual(evidence.confidence, 0.0)
        self.assertEqual(evidence.status, "missing")
        self.assertEqual(evidence.reason, "no deterministic candidate")

    def test_found_evidence_requires_a_prediction_and_value(self):
        predictions = [OCRPrediction("one", (0, 1, 1, 0), (0, 0, 1, 1), 0.9)]

        with self.assertRaises(ValueError):
            make_field_evidence("field", predictions, (), "one")
        with self.assertRaises(ValueError):
            make_field_evidence("field", predictions, (0,), None)

    def test_ambiguous_evidence_keeps_source_details(self):
        predictions = [OCRPrediction("$", (0, 1, 1, 0), (0, 0, 1, 1), 0.82)]

        evidence = make_field_evidence(
            "currency", predictions, (0,), "$", status="ambiguous",
            reason="currency code is not visible",
        )

        self.assertEqual(evidence.status, "ambiguous")
        self.assertEqual(evidence.value, "$")
        self.assertEqual(evidence.raw_text, "$")
        self.assertIsNotNone(evidence.bbox)
        self.assertEqual(evidence.confidence, 0.82)


if __name__ == "__main__":
    unittest.main()
