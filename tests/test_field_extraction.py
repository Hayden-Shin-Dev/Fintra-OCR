import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.field_extraction import extract_fields, find_label_spans
from fintra_ocr.prediction_parser import OCRPrediction


def prediction(text, left, top, right=100, bottom=None, score=0.9):
    if bottom is None:
        bottom = top + 20
    return OCRPrediction(text, (left, right, right, left), (top, top, bottom, bottom), score)


class FieldExtractionTest(unittest.TestCase):
    def test_extracts_invoice_embedded_and_table_fields(self):
        predictions = [
            prediction("Invoice No. 172224", 10, 10),
            prediction("Date: Feb 23, 2013", 10, 50),
            prediction("Buyer: ACME CO., LTD.", 10, 90),
            prediction("Q'ty / Unit", 10, 130),
            prediction("Description of Goods", 100, 130),
            prediction("CASE-AIR DRAIN", 100, 170),
            prediction("2", 10, 170),
            prediction("Total", 10, 210),
            prediction("$1,216.98", 100, 210),
        ]

        fields = extract_fields("상업송장", predictions)

        self.assertEqual(fields["invoice_no"].value, "172224")
        self.assertEqual(fields["date"].value, "Feb 23, 2013")
        self.assertEqual(fields["buyer"].value, "ACME CO., LTD.")
        self.assertEqual(fields["quantity"].value, "2")
        self.assertEqual(fields["goods_description"].value, "CASE-AIR DRAIN")
        self.assertEqual(fields["amount"].value, "$1,216.98")
        self.assertEqual(fields["amount"].status, "found")
        self.assertEqual(fields["amount"].raw_text, "$1,216.98")

    def test_extracts_packing_and_bill_of_lading_fields(self):
        packing = [
            prediction("Invoice No. 172224", 10, 10),
            prediction("Description of Goods", 100, 50),
            prediction("Diplexer", 100, 90),
            prediction("Quantity", 10, 50),
            prediction("3", 10, 90),
            prediction("Number of Packages: 31 PKG", 10, 130),
            prediction("TOTAL Gross Weight: 614KG", 10, 170),
        ]
        bill = [
            prediction("B/L No. HG290309", 10, 10),
            prediction("Consignor/Shipper", 10, 50),
            prediction("GAE WOON CO., LTD.", 150, 50),
            prediction("Consignee", 10, 90),
            prediction("DHHJ FRANCHISING CO., LTD.", 150, 90),
            prediction("Description of Goods", 100, 130),
            prediction("CELL ASSEMBLY", 100, 170),
            prediction("SAY : 88 BUNDLES ONLY", 10, 210),
            prediction("Gross Weight", 10, 250),
            prediction("884KG", 150, 250),
            prediction("LADEN ON BOARD", 10, 290),
            prediction("JUN 11, 2013", 150, 290),
        ]

        packing_fields = extract_fields("포장명세서", packing)
        bill_fields = extract_fields("선하증권", bill)

        self.assertEqual(packing_fields["invoice_no"].value, "172224")
        self.assertEqual(packing_fields["number_of_packages"].value, "31 PKG")
        self.assertEqual(packing_fields["gross_weight"].value, "614KG")
        self.assertEqual(bill_fields["bl_no"].value, "HG290309")
        self.assertEqual(bill_fields["shipper"].value, "GAE WOON CO., LTD.")
        self.assertEqual(bill_fields["consignee"].value, "DHHJ FRANCHISING CO., LTD.")
        self.assertEqual(bill_fields["number_of_packages"].value, "88 BUNDLES")
        self.assertEqual(bill_fields["on_board_date"].value, "JUN 11, 2013")

    def test_unstable_field_is_missing_instead_of_using_an_unrelated_number(self):
        fields = extract_fields(
            "포장명세서",
            [prediction("PACKING LIST", 10, 10), prediction("614KG", 10, 50)],
        )

        self.assertEqual(fields["quantity"].status, "missing")
        self.assertIsNone(fields["quantity"].value)
        self.assertIn("header", fields["quantity"].reason)

    def test_buyer_reference_is_ambiguous_but_keeps_evidence(self):
        fields = extract_fields(
            "상업송장",
            [prediction("Buyer", 10, 10), prediction("Same to consignee", 150, 10)],
        )

        self.assertEqual(fields["buyer"].status, "ambiguous")
        self.assertEqual(fields["buyer"].value, "Same to consignee")
        self.assertEqual(fields["buyer"].raw_text, "Same to consignee")
        self.assertIsNotNone(fields["buyer"].bbox)

    def test_rejects_financial_form_types(self):
        with self.assertRaises(ValueError):
            extract_fields("재무상태표", [])

    def test_quantity_key_value_row_accepts_plain_integer(self):
        fields = extract_fields(
            "상업송장",
            [prediction("Quantity", 10, 10, 80), prediction("5000", 100, 10, 160)],
        )
        self.assertEqual(fields["quantity"].value, "5000")
        self.assertEqual(fields["quantity"].status, "found")
        self.assertEqual(fields["amount"].status, "missing")

    def test_unit_price_is_not_a_quantity_label(self):
        fields = extract_fields(
            "상업송장",
            [prediction("Unit Price", 10, 10, 80), prediction("5000", 100, 10, 160)],
        )
        self.assertEqual(fields["quantity"].status, "missing")

    def test_seller_is_not_buyer(self):
        fields = extract_fields(
            "상업송장",
            [prediction("Seller", 10, 10, 80), prediction("ACME LTD", 100, 10, 200)],
        )
        self.assertEqual(fields["buyer"].status, "missing")

    def test_generic_bill_date_is_not_on_board_date(self):
        fields = extract_fields(
            "선하증권",
            [prediction("Date", 10, 10, 80), prediction("2024-01-01", 100, 10, 200)],
        )
        self.assertEqual(fields["on_board_date"].status, "missing")

    def test_split_invoice_and_bill_numbers_are_anchored(self):
        invoice_predictions = [
            prediction("Invoice", 10, 10, 60),
            prediction("No.", 70, 10, 100),
            prediction("463059", 110, 10, 170),
        ]
        bill_predictions = [
            prediction("B/L", 10, 10, 50),
            prediction("No.", 60, 10, 90),
            prediction("HG290309", 100, 10, 180),
        ]
        self.assertEqual(extract_fields("상업송장", invoice_predictions)["invoice_no"].value, "463059")
        self.assertEqual(extract_fields("선하증권", bill_predictions)["bl_no"].value, "HG290309")
        self.assertTrue(find_label_spans(invoice_predictions, "invoice_no"))
        self.assertTrue(find_label_spans(bill_predictions, "bl_no"))

    def test_vertical_gross_weight_label_connects_same_row_value(self):
        fields = extract_fields(
            "선하증권",
            [
                prediction("GROSS", 10, 10, 80),
                prediction("WEIGHT", 10, 50, 80),
                prediction("614KG", 100, 50, 170),
            ],
        )
        self.assertEqual(fields["gross_weight"].value, "614KG")

    def test_table_columns_do_not_bleed_into_each_other(self):
        fields = extract_fields(
            "상업송장",
            [
                prediction("Description", 10, 10, 90),
                prediction("Quantity", 100, 10, 180),
                prediction("Amount", 300, 10, 380),
                prediction("ABC-123", 10, 50, 90),
                prediction("10", 110, 50, 150),
                prediction("$5000", 310, 50, 370),
                prediction("XYZ-456", 10, 80, 90),
                prediction("20", 110, 80, 150),
                prediction("$6000", 310, 80, 370),
            ],
        )
        self.assertEqual(fields["goods_description"].value, "ABC-123 | XYZ-456")
        self.assertEqual(fields["quantity"].value, "10 | 20")
        self.assertNotIn("5000", fields["quantity"].value)

    def test_net_weight_does_not_extract_as_gross_weight(self):
        fields = extract_fields(
            "포장명세서",
            [prediction("NET WEIGHT", 10, 10, 90), prediction("500 KG", 100, 10, 180)],
        )
        self.assertEqual(fields["gross_weight"].status, "missing")

    def test_real_gt_label_variants_from_previous_full_profile(self):
        invoice = extract_fields(
            "상업송장",
            [
                prediction("Invoice-Number", 10, 10, 110), prediction("463059", 130, 10, 200),
                prediction("INV.DATE:", 10, 40, 90), prediction("20-Apr-2017", 130, 40, 230),
                prediction("Goods", 10, 80, 90), prediction("ABC-123", 10, 110, 90),
            ],
        )
        bill = extract_fields(
            "선하증권",
            [
                prediction("B/LNo.:", 10, 10, 90), prediction("HG290309", 120, 10, 200),
                prediction("SHIPPER'S", 10, 50, 100), prediction("GAE WOON CO., LTD.", 130, 50, 300),
                prediction("Consignee's", 10, 80, 110), prediction("DHHJ CO., LTD.", 130, 80, 260),
                prediction("G.WEIGHT", 10, 120, 100), prediction("884KG", 130, 120, 200),
            ],
        )

        self.assertEqual(invoice["invoice_no"].value, "463059")
        self.assertEqual(invoice["date"].value, "20-Apr-2017")
        self.assertEqual(invoice["goods_description"].value, "ABC-123")
        self.assertEqual(bill["bl_no"].value, "HG290309")
        self.assertEqual(bill["shipper"].value, "GAE WOON CO., LTD.")
        self.assertEqual(bill["consignee"].value, "DHHJ CO., LTD.")
        self.assertEqual(bill["gross_weight"].value, "884KG")

    def test_old_false_positive_labels_stay_rejected(self):
        invoice = extract_fields(
            "상업송장",
            [
                prediction("Seller", 10, 10, 80), prediction("ACME LTD", 100, 10, 200),
                prediction("Unit", 10, 50, 80), prediction("5000", 100, 50, 160),
                prediction("Price", 10, 90, 80), prediction("6000", 100, 90, 160),
            ],
        )
        bill = extract_fields(
            "선하증권",
            [prediction("DATED", 10, 10, 80), prediction("2024-03-22", 100, 10, 200)],
        )

        self.assertEqual(invoice["buyer"].status, "missing")
        self.assertEqual(invoice["quantity"].status, "missing")
        self.assertEqual(invoice["amount"].status, "missing")
        self.assertEqual(bill["on_board_date"].status, "missing")


if __name__ == "__main__":
    unittest.main()

