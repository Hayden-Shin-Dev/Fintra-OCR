import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_validation_engine import evaluate


class ValidationEvaluationTests(unittest.TestCase):
    def test_fixture_matrix_covers_rules_and_expected_statuses(self):
        with tempfile.TemporaryDirectory() as temp:
            metrics = evaluate(Path(temp))
        self.assertEqual(metrics["scenarios"], 25)
        self.assertEqual(metrics["rule_accuracy"], 1.0)
        self.assertEqual(metrics["review_required_correctness"], 1.0)
        self.assertEqual(metrics["insufficient_evidence_correctness"], 1.0)
        self.assertEqual(len(metrics["rules"]), 7)


if __name__ == "__main__":
    unittest.main()
