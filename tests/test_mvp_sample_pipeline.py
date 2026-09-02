import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.common_schema import build_common_document_from_form_type
from fintra_ocr.field_extraction import extract_fields
from fintra_ocr.normalization import normalize_fields
from fintra_ocr.prediction_parser import OCRPrediction


def p(text, left, top, right=None, bottom=None, score=0.99):
    right = right if right is not None else left + 100
    bottom = bottom if bottom is not None else top + 20
    return OCRPrediction(text, (left, right, right, left), (top, top, bottom, bottom), score)


class MVPSamplePipelineTest(unittest.TestCase):
    """Regression coverage for the three previously verified Fintra sample values."""

    def test_invoice_sample_extract_normalize_schema(self):
        predictions = [
            p("Invoice No.", 10, 10, 90), p("463059", 120, 10, 180),
            p("Invoice Date", 10, 40, 90), p("20-Apr-2017", 120, 40, 220),
            p("Buyer", 10, 70, 90), p("Same to consignee", 120, 70, 260),
            p("Description of Goods", 10, 110, 170), p("Quantity", 200, 110, 280),
            p("Tube", 10, 140, 170), p("2", 210, 140, 240),
            p("CASE-AIR DRAIN", 10, 170, 170), p("3", 210, 170, 240),
            p("TOTAL AMOUNT", 300, 210, 410), p("$1,216.98", 430, 210, 520),
        ]
        fields = normalize_fields(extract_fields("상업송장", predictions))
        document = build_common_document_from_form_type(
            "상업송장", "IMG_OCR_6_T_NV_000002", fields
        )

        self.assertEqual(fields["invoice_no"].value, "463059")
        self.assertEqual(fields["date"].normalized, "2017-04-20")
        self.assertEqual(fields["buyer"].status, "ambiguous")
        self.assertEqual(fields["quantity"].normalized["items"], [
            {"value": 2, "unit": None}, {"value": 3, "unit": None}
        ])
        self.assertEqual(fields["amount"].normalized["value"], 1216.98)
        self.assertEqual(fields["currency"].status, "ambiguous")
        self.assertEqual(document["processing_status"], "partial")

    def test_packing_sample_extract_normalize_schema(self):
        predictions = [
            p("Invoice No.", 10, 10, 90), p("172224", 120, 10, 180),
            p("Description of Goods", 10, 50, 170), p("Quantity", 200, 50, 280),
            p("Bellows", 10, 80, 170), p("83", 210, 80, 240),
            p("BRACKET", 10, 110, 170), p("98", 210, 110, 240),
            p("Filter Element", 10, 140, 170), p("26", 210, 140, 240),
            p("Number of Packages", 10, 180, 170), p("31 PKG", 200, 180, 270),
            p("TOTAL Gross Weight", 10, 210, 170), p("614KG", 200, 210, 270),
        ]
        fields = normalize_fields(extract_fields("포장명세서", predictions))
        document = build_common_document_from_form_type(
            "포장명세서", "IMG_OCR_6_T_PL_000002", fields
        )

        self.assertEqual(fields["invoice_no"].value, "172224")
        self.assertEqual([item["value"] for item in fields["quantity"].normalized["items"]], [83, 98, 26])
        self.assertEqual(fields["number_of_packages"].normalized, {"value": 31, "unit": "PKG"})
        self.assertEqual(fields["gross_weight"].normalized, {"value": 614, "unit": "KG"})
        self.assertEqual(document["processing_status"], "success")

    def test_bill_sample_extract_normalize_schema(self):
        predictions = [
            p("B/L No.", 10, 10, 90), p("HG290309", 120, 10, 200),
            p("SHIPPER'S", 10, 50, 100), p("GAE WOON CO., LTD.", 130, 50, 300),
            p("Consignee", 10, 80, 100), p("DHHJ FRANCHISING CO., LTD.", 130, 80, 340),
            p("Description of Goods", 10, 120, 180), p("CELL ASSEMBLY", 10, 150, 180),
            p("Number of Packages", 10, 190, 170), p("88 BUNDLES", 200, 190, 300),
            p("Gross Weight", 10, 220, 130), p("884KG", 160, 220, 230),
            p("LADEN ON BOARD", 10, 250, 150), p("JUN 11, 2013", 180, 250, 290),
        ]
        fields = normalize_fields(extract_fields("선하증권", predictions))
        document = build_common_document_from_form_type(
            "선하증권", "IMG_OCR_6_T_BL_000002", fields
        )

        self.assertEqual(fields["bl_no"].value, "HG290309")
        self.assertEqual(fields["shipper"].value, "GAE WOON CO., LTD.")
        self.assertEqual(fields["consignee"].value, "DHHJ FRANCHISING CO., LTD.")
        self.assertEqual(fields["number_of_packages"].normalized, {"value": 88, "unit": "BUNDLES"})
        self.assertEqual(fields["gross_weight"].normalized, {"value": 884, "unit": "KG"})
        self.assertEqual(fields["on_board_date"].normalized, "2013-06-11")
        self.assertEqual(document["processing_status"], "success")


if __name__ == "__main__":
    unittest.main()

