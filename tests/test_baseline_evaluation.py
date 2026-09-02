import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.baseline_evaluation import evaluate_target_forms
from fintra_ocr.target_scope import FINTRA_FORM_TYPES
from fintra_ocr.target_selection import select_target_archive_pairs


def fake_predictor(_image_bytes):
    return [
        {
            "rec_texts": ["sample"],
            "rec_scores": [0.9],
            "rec_boxes": [[0, 0, 1, 1]],
        }
    ]


class BaselineEvaluationTest(unittest.TestCase):
    def test_evaluates_one_sample_for_each_target_form_type(self):
        selected = select_target_archive_pairs(discover_archives())

        evaluations = evaluate_target_forms(
            selected,
            split="validation",
            predictor=fake_predictor,
        )

        self.assertEqual(len(evaluations), 3)
        self.assertEqual(
            {evaluation.sample.form_type for evaluation in evaluations},
            set(FINTRA_FORM_TYPES),
        )
        self.assertTrue(
            all(evaluation.comparison.ground_truth_count > 0 for evaluation in evaluations)
        )

    def test_unknown_split_raises_key_error(self):
        selected = select_target_archive_pairs(discover_archives())

        with self.assertRaises(KeyError):
            evaluate_target_forms(selected, split="test", predictor=fake_predictor)


if __name__ == "__main__":
    unittest.main()
