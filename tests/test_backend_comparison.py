import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.compare_field_backends import compare


class BackendComparisonTests(unittest.TestCase):
    def test_oracle_union_is_not_lower_than_either_backend(self):
        fields = ["case_id", "field_name", "document_type", "gt_status", "status"]
        rows = [
            ["ci-001", "seller", "Commercial Invoice", "available", "normalized_match"],
            ["ci-001", "buyer", "Commercial Invoice", "available", "wrong"],
            ["pl-001", "quantity", "Packing List", "available", "missing"],
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            modern = root / "modern.csv"
            paddle = root / "paddle.csv"
            for path, values in ((modern, rows), (paddle, [
                rows[0],
                ["ci-001", "buyer", "Commercial Invoice", "available", "normalized_match"],
                rows[2],
            ])):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(fields)
                    writer.writerows(values)
            report = compare(modern, paddle)
            self.assertEqual(report["modern_recoverable"], 1)
            self.assertEqual(report["paddle_recoverable"], 2)
            self.assertEqual(report["oracle_union_recoverable"], 2)


if __name__ == "__main__":
    unittest.main()
