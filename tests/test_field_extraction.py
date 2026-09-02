import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.field_extraction import extract_fields
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
            prediction("56 PKG", 10, 170),
            prediction("Total", 10, 210),
            prediction("$1,216.98", 100, 210),
        ]

        fields = extract_fields("상업송장", predictions)

        self.assertEqual(fields["invoice_no"].value, "172224")
        self.assertEqual(fields["date"].value, "Feb 23, 2013")
        self.assertEqual(fields["buyer"].value, "ACME CO., LTD.")
        self.assertEqual(fields["quantity"].value, "56 PKG")
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

    def test_rejects_financial_form_types(self):
        with self.assertRaises(ValueError):
            extract_fields("재무상태표", [])


if __name__ == "__main__":
    unittest.main()
