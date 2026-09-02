import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.target_gt_analysis import (
    TargetLabelRecord,
    analyze_records,
)


def record(document_type, member_name, boxes):
    return TargetLabelRecord(
        split="training",
        document_type=document_type,
        archive_name="fixture.zip",
        member_name=member_name,
        record={
            "bbox": [
                {"data": text, "x": [x, x + 10, x + 10, x], "y": [y, y, y + 10, y + 10]}
                for text, x, y in boxes
            ]
        },
    )


class TargetGTAnalysisTest(unittest.TestCase):
    def test_streaming_aggregate_counts_fields_and_formats(self):
        result = analyze_records([
            record("packing_list", "complete.json", [
                ("Invoice No.", 10, 10), ("172224", 100, 10),
                ("Quantity", 10, 30), ("83", 100, 30), ("PKG", 130, 30),
                ("TOTAL", 10, 50), ("31 PKG", 100, 50), ("614KG", 180, 50),
            ]),
            record("packing_list", "missing.json", [("Description", 10, 10)]),
        ], representatives_per_type=3)

        packing = result["document_types"]["packing_list"]
        self.assertEqual(packing["document_count"], 2)
        self.assertEqual(packing["field_stats"]["invoice_no"]["documents_with_candidate"], 1)
        self.assertEqual(packing["field_stats"]["invoice_no"]["missing_rate"], 0.5)
        self.assertEqual(packing["units"]["PKG"], 2)
        self.assertEqual(packing["units"]["KG"], 1)
        self.assertGreaterEqual(packing["geometry"]["split_value_rows"], 1)

    def test_malformed_bbox_is_counted_without_aborting(self):
        result = analyze_records([
            record("commercial_invoice", "bad.json", [("Date", 10, 10)]),
            TargetLabelRecord("training", "commercial_invoice", "fixture.zip", "malformed.json", {"bbox": None}),
        ])

        self.assertEqual(result["document_count"], 2)
        self.assertEqual(result["document_types"]["commercial_invoice"]["malformed_records"], 1)

    def test_representatives_have_selection_reasons(self):
        result = analyze_records([
            record("bill_of_lading", f"sample-{index}.json", [("Shipper", 10, 10), (str(index), 100, 10)])
            for index in range(10)
        ], representatives_per_type=3)

        samples = result["document_types"]["bill_of_lading"]["representative_samples"]
        self.assertEqual(len(samples), 3)
        self.assertTrue(all(sample["selection_reason"] for sample in samples))

    def test_plain_integer_is_not_counted_as_money(self):
        result = analyze_records([
            record("commercial_invoice", "amounts.json", [
                ("$1,216.98", 10, 10), ("1216", 100, 10),
            ])
        ])

        amount_stats = result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]
        self.assertEqual(amount_stats["occurrences"], 1)
        self.assertEqual(
            result["document_types"]["commercial_invoice"]["amount_patterns"]["with_symbol"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
