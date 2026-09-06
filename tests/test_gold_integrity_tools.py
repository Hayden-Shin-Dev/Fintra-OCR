import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_evaluator_consistency import consistency_checks  # noqa: E402
from audit_historical_evaluator_mismatch import counts_by_type  # noqa: E402


class GoldIntegrityToolTests(unittest.TestCase):
    def test_normalized_match_reconciliation_includes_exact_and_normalized_only(self):
        rows = [
            {"status": "exact_match", "gt_status": "available", "document_type": "Commercial Invoice", "field_name": "x"},
            {"status": "normalized_match", "gt_status": "available", "document_type": "Commercial Invoice", "field_name": "x"},
            {"status": "wrong", "gt_status": "available", "document_type": "Commercial Invoice", "field_name": "x"},
        ]
        metrics = {
            "selection": {"rows": 3},
            "overall": {
                "status_counts": {"exact_match": 1, "normalized_match": 1, "wrong": 1},
                "applicable_gold": 3,
                "normalized_matches": 2,
                "wrong": 1,
                "missing": 0,
            },
        }
        _, checks = consistency_checks(rows, metrics)
        self.assertTrue(all(checks.values()))

    def test_type_summary_exposes_normalized_only_rows(self):
        rows = [
            {"status": "exact_match", "gt_status": "available", "document_type": "B/L", "field_name": "vessel"},
            {"status": "normalized_match", "gt_status": "available", "document_type": "B/L", "field_name": "vessel"},
            {"status": "missing", "gt_status": "available", "document_type": "B/L", "field_name": "vessel"},
        ]
        summary = counts_by_type(rows)
        self.assertEqual(summary["B/L"]["exact"], 1)
        self.assertEqual(summary["B/L"]["normalized_only"], 1)
        self.assertEqual(summary["B/L"]["normalized_matches"], 2)


if __name__ == "__main__":
    unittest.main()
