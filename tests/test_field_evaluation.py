import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_field_extraction import evaluate, normalize_field, compare_field


class FieldEvaluationTests(unittest.TestCase):
    def test_failed_normalizations_never_count_as_matches(self):
        self.assertEqual(compare_field("Departure", "43-43-11267", "invoice_date"), "wrong")
        self.assertEqual(compare_field("of", "53-32-81805", "invoice_date"), "wrong")
        self.assertEqual(compare_field("banana", "pear", "total_amount"), "wrong")

    def test_unit_price_is_numeric_not_unit(self):
        self.assertEqual(compare_field("USD 12.00", "$12.00", "items[0].unit_price"), "normalized_match")
        self.assertEqual(compare_field("12.0", "12.00", "items[0].unit_price"), "normalized_match")
        self.assertEqual(compare_field("kgs", "KG", "weight_unit"), "normalized_match")
        self.assertEqual(compare_field("Nov 14, 2020", "2020-11-14", "invoice_date"), "normalized_match")
        self.assertEqual(compare_field("20-Nar-2001", "20-Mar-2001", "invoice_date"), "wrong")

    def test_normalization_is_type_specific_and_conservative(self):
        self.assertEqual(normalize_field(" ACME,  Ltd. ", "seller"), "ACME LTD")
        self.assertEqual(normalize_field("2024/01/02", "invoice_date"), "2024-01-02")
        self.assertEqual(normalize_field("USD 1,250.00", "total_amount"), "1250.00")
        self.assertNotEqual(normalize_field("KG", "weight_unit"), normalize_field("LB", "weight_unit"))

    def test_evaluate_marks_exact_and_normalized_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = root / "ci-001"
            recognition = case / "outputs" / "recognition"
            recognition.mkdir(parents=True)
            manifest = {
                "case_id": "ci-001",
                "document_id": "doc-1",
                "document_type": "Commercial Invoice",
                "gold_fields": [
                    {"field_name": "invoice_number", "status": "available", "value": "INV-1"},
                    {"field_name": "total_amount", "status": "available", "value": "$1250.00"},
                    {"field_name": "seller", "status": "ambiguous_gt", "value": None},
                ],
            }
            (case / "case_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            prediction = {
                "document_id": "doc-1",
                "regions": [
                    {"bbox": [0, 0, 10, 10], "text": "Invoice No: INV-1"},
                    {"bbox": [0, 20, 10, 30], "text": "Total Amount: USD 1250.00"},
                ],
            }
            (recognition / "doc-1.json").write_text(json.dumps(prediction), encoding="utf-8")
            result = evaluate(root, root / "report")
            self.assertEqual(result["overall"]["normalized_matches"], 2)
            self.assertEqual(result["overall"]["ambiguous_gt"], 1)
            self.assertEqual(result["overall"]["ambiguous"], 0)
            self.assertEqual(result["field_extraction_status"], "PASS")
            self.assertTrue(result["target_met"])


if __name__ == "__main__":
    unittest.main()
