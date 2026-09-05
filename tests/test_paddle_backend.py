import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fintra.ocr.paddle_backend import parse_paddle_result
from scripts.run_paddle_field_eval import select_cases


class PaddleBackendParserTests(unittest.TestCase):
    def test_parses_paddle_v3_mapping_and_preserves_confidence(self):
        regions = parse_paddle_result({
            "res": {
                "rec_texts": ["Invoice", "USD 10.00"],
                "rec_scores": [0.91, 0.83],
                "rec_boxes": [[10, 20, 50, 40], [60, 20, 130, 40]],
            }
        })
        self.assertEqual([item.text for item in regions], ["Invoice", "USD 10.00"])
        self.assertEqual(regions[0].polygon, [[10.0, 20.0], [50.0, 20.0], [50.0, 40.0], [10.0, 40.0]])
        self.assertEqual(regions[1].confidence, 0.83)

    def test_parses_numpy_like_values_without_numpy_dependency(self):
        class Array:
            def __init__(self, value):
                self.value = value

            def tolist(self):
                return self.value

        regions = parse_paddle_result({
            "rec_texts": Array(["A"]),
            "rec_scores": Array([0.5]),
            "rec_polys": Array([[[1, 2], [11, 2], [11, 12], [1, 12]]]),
        })
        self.assertEqual(regions[0].text, "A")
        self.assertEqual(regions[0].bbox, (1.0, 2.0, 11.0, 12.0))

    def test_parses_legacy_nested_sequence(self):
        regions = parse_paddle_result([
            [[[1, 2], [11, 2], [11, 12], [1, 12]], ["ABC", 0.77]],
        ])
        self.assertEqual(regions[0].text, "ABC")
        self.assertEqual(regions[0].confidence, 0.77)

    def test_rejects_mismatched_result_lengths(self):
        with self.assertRaises(ValueError):
            parse_paddle_result({
                "rec_texts": ["A", "B"],
                "rec_scores": [0.5],
                "rec_boxes": [[0, 0, 1, 1], [2, 2, 3, 3]],
            })

    def test_smoke_selection_is_one_case_per_document_type(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for case_id, document_type in (("ci-001", "Commercial Invoice"), ("pl-001", "Packing List"), ("bl-001", "B/L")):
                case = root / case_id
                case.mkdir()
                (case / "case_manifest.json").write_text(
                    json.dumps({"case_id": case_id, "document_type": document_type}),
                    encoding="utf-8",
                )
            selected = select_cases(root, smoke=True, limit=None)
            self.assertEqual([case.name for case in selected], ["ci-001", "pl-001", "bl-001"])


if __name__ == "__main__":
    unittest.main()
