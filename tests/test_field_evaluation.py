import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.field_evaluation import evaluate_prediction_rows


def field(value, normalized=None, status="found", raw_text=None):
    return {
        "status": status,
        "value": value,
        "normalized": value if normalized is None else normalized,
        "raw_text": value if raw_text is None else raw_text,
    }


class FieldEvaluationTest(unittest.TestCase):
    def test_reports_outcome_and_preserves_document_isolation(self):
        row = {
            "document_id": "DOC-001",
            "form_type": "상업송장",
            "ocr_predictions": [
                {"text": "Invoice No. 123", "confidence": 0.9, "bbox": [[0, 0], [120, 0], [120, 20], [0, 20]]},
            ],
            "fields": {"invoice_no": field("123")},
            "oracle_fields": {"invoice_no": field("123")},
        }
        report = evaluate_prediction_rows([row])
        self.assertEqual(report["document_count"], 1)
        self.assertEqual(report["split_counts"], {"holdout": 1})
        result = next(item for item in report["field_results"] if item["field_name"] == "invoice_no")
        self.assertEqual(result["improved"]["outcome"], "correct")

    def test_unknown_oracle_is_not_counted_as_ocr_failure(self):
        row = {
            "document_id": "DOC-002",
            "form_type": "포장명세서",
            "ocr_predictions": [],
            "fields": {"invoice_no": field(None, status="missing")},
            "oracle_fields": {"invoice_no": field(None, status="missing")},
        }
        report = evaluate_prediction_rows([row])
        result = next(item for item in report["field_results"] if item["field_name"] == "invoice_no")
        self.assertEqual(result["improved"]["outcome"], "unknown")
        self.assertEqual(result["improved"]["cause"], "ORACLE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
