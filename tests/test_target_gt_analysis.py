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
                ("Number of Packages", 10, 50), ("31", 100, 50), ("PKG", 130, 50),
                ("Gross Weight 614KG", 10, 70),
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
        self.assertEqual(packing["field_stats"]["number_of_packages"]["separate_bbox_label_value"], 1)
        self.assertEqual(packing["field_stats"]["gross_weight"]["same_bbox_label_value"], 1)
        self.assertEqual(packing["field_stats"]["quantity"]["documents_with_anchored_value"], 1)

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

    def test_representatives_include_a_missing_field_case(self):
        result = analyze_records([
            record("packing_list", "complete.json", [
                ("Invoice No.", 10, 10), ("172224", 100, 10),
                ("Quantity", 10, 30), ("83", 100, 30),
                ("31 PKG", 100, 50), ("614KG", 180, 50),
            ]),
            record("packing_list", "missing.json", [("Description", 10, 10)]),
        ], representatives_per_type=3)

        samples = result["document_types"]["packing_list"]["representative_samples"]
        self.assertTrue(any(sample["features"]["missing_core_fields"] > 0 for sample in samples))

    def test_plain_integer_without_anchor_is_unclassified_not_money(self):
        result = analyze_records([
            record("commercial_invoice", "amounts.json", [
                ("$1,216.98", 10, 10), ("1216", 100, 10),
            ])
        ])

        amount_stats = result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]
        self.assertEqual(amount_stats["documents_with_label_anchor"], 0)
        self.assertEqual(amount_stats["documents_with_anchored_value"], 0)
        self.assertEqual(amount_stats["format_only_unanchored_candidate"], 1)
        self.assertEqual(amount_stats["ambiguous_or_unclassified"], 0)
        self.assertEqual(amount_stats["exclusive_document_status"], {"format_only": 1})
        self.assertEqual(
            result["document_types"]["commercial_invoice"]["unclassified_numeric_occurrences"],
            1,
        )
        self.assertEqual(
            result["document_types"]["commercial_invoice"]["amount_patterns"]["with_symbol"],
            1,
        )

    def test_amount_anchor_accepts_plain_integer(self):
        result = analyze_records([
            record("commercial_invoice", "plain-amount.json", [
                ("TOTAL AMOUNT", 10, 10), ("5000", 100, 10),
            ])
        ])
        stats = result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]
        self.assertEqual(stats["documents_with_label_anchor"], 1)
        self.assertEqual(stats["documents_with_anchored_value"], 1)
        self.assertEqual(stats["separate_bbox_label_value"], 1)
        self.assertEqual(stats["format_only_unanchored_candidate"], 0)

    def test_amount_anchor_accepts_symbol_and_decimal(self):
        result = analyze_records([
            record("commercial_invoice", "money-amount.json", [
                ("TOTAL AMOUNT", 10, 10), ("$5,000.00", 100, 10),
            ])
        ])
        stats = result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]
        self.assertEqual(stats["documents_with_anchored_value"], 1)
        self.assertEqual(stats["separate_bbox_label_value"], 1)

    def test_quantity_anchor_plain_integer_is_not_amount(self):
        result = analyze_records([
            record("commercial_invoice", "quantity.json", [
                ("QUANTITY", 10, 10), ("5000", 100, 10),
            ])
        ])
        invoice = result["document_types"]["commercial_invoice"]["field_stats"]
        self.assertEqual(invoice["quantity"]["documents_with_anchored_value"], 1)
        self.assertEqual(invoice["amount_total"]["documents_with_anchored_value"], 0)
        self.assertEqual(invoice["amount_total"]["ambiguous_or_unclassified"], 0)

    def test_net_weight_is_not_gross_weight(self):
        result = analyze_records([
            record("packing_list", "net-weight.json", [
                ("NET WEIGHT", 10, 10), ("500 KG", 100, 10),
            ])
        ])
        stats = result["document_types"]["packing_list"]["field_stats"]["gross_weight"]
        self.assertEqual(stats["documents_with_label_anchor"], 0)
        self.assertEqual(stats["documents_with_anchored_value"], 0)
        self.assertEqual(stats["same_bbox_label_value"], 0)
        self.assertEqual(stats["format_only_unanchored_candidate"], 0)
        self.assertEqual(stats["non_target_context_documents"], 1)
        self.assertEqual(stats["exclusive_document_status"], {"non_target_context": 1})

    def test_gross_weight_anchor_accepts_weight_value(self):
        result = analyze_records([
            record("packing_list", "gross-weight.json", [
                ("GROSS WEIGHT", 10, 10), ("614 KG", 100, 10),
            ])
        ])
        stats = result["document_types"]["packing_list"]["field_stats"]["gross_weight"]
        self.assertEqual(stats["documents_with_label_anchor"], 1)
        self.assertEqual(stats["documents_with_anchored_value"], 1)
        self.assertEqual(stats["separate_bbox_label_value"], 1)

    def test_currency_amount_without_anchor_is_format_only(self):
        result = analyze_records([
            record("commercial_invoice", "currency-only.json", [("$5000", 10, 10)])
        ])
        stats = result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]
        self.assertEqual(stats["format_only_unanchored_candidate"], 1)
        self.assertEqual(stats["ambiguous_or_unclassified"], 0)

    def test_plain_integer_without_context_is_unclassified_numeric(self):
        result = analyze_records([
            record("commercial_invoice", "numeric-only.json", [("5000", 10, 10)])
        ])
        stats = result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]
        self.assertEqual(stats["format_only_unanchored_candidate"], 0)
        self.assertEqual(stats["ambiguous_or_unclassified"], 0)
        self.assertEqual(stats["exclusive_document_status"], {"missing": 1})
        self.assertEqual(
            result["document_types"]["commercial_invoice"]["unclassified_numeric_occurrences"],
            1,
        )

    def test_amount_and_weight_anchors_can_share_one_bbox(self):
        result = analyze_records([
            record("commercial_invoice", "same-bbox.json", [("TOTAL AMOUNT 5000", 10, 10)]),
            record("packing_list", "same-bbox-weight.json", [("GROSS WEIGHT 614 KG", 10, 10)]),
        ])
        self.assertEqual(
            result["document_types"]["commercial_invoice"]["field_stats"]["amount_total"]["same_bbox_label_value"],
            1,
        )
        self.assertEqual(
            result["document_types"]["packing_list"]["field_stats"]["gross_weight"]["same_bbox_label_value"],
            1,
        )

    def test_iso_currency_code_without_amount_anchor_is_format_only_amount_but_extracted_currency(self):
        result = analyze_records([
            record("commercial_invoice", "usd-only.json", [("USD 5000", 10, 10)])
        ])
        fields = result["document_types"]["commercial_invoice"]["field_stats"]
        self.assertEqual(fields["amount_total"]["exclusive_document_status"], {"format_only": 1})
        self.assertEqual(fields["currency"]["documents_with_extracted_value"], 1)
        self.assertEqual(fields["currency"]["documents_with_anchored_value"], 0)
        self.assertEqual(fields["currency"]["exclusive_document_status"], {"derived_value": 1})

    def test_attached_units_are_counted(self):
        result = analyze_records([
            record("packing_list", "units.json", [
                ("TOTAL Gross Weight: 614KG", 10, 10),
                ("Number of Packages: 31PKG", 10, 30),
            ])
        ])
        units = result["document_types"]["packing_list"]["units"]
        self.assertEqual(units["KG"], 1)
        self.assertEqual(units["PKG"], 1)

    def test_exclusive_status_is_a_true_per_field_partition(self):
        result = analyze_records([
            record("commercial_invoice", "anchored.json", [("TOTAL AMOUNT", 10, 10), ("5000", 100, 10)]),
            record("commercial_invoice", "format.json", [("$5000", 10, 10)]),
            record("commercial_invoice", "missing.json", [("HELLO", 10, 10)]),
        ])
        total = result["document_types"]["commercial_invoice"]["document_count"]
        for stats in result["document_types"]["commercial_invoice"]["field_stats"].values():
            self.assertEqual(sum(stats["exclusive_document_status"].values()), total)


if __name__ == "__main__":
    unittest.main()

