import unittest

from fintra.extraction.clean.engine import EXTRACTORS
from fintra.extraction.clean.layout import Layout
from fintra.extraction.clean.party import resolve as resolve_party
from fintra.extraction.clean.scalar import is_identifier
from fintra.extraction.clean.scalar import candidates as scalar_candidates
from fintra.extraction.clean.table import resolve as resolve_table
from fintra.ocr.adapter import OCRRegion, OCRResult


def _result(kind, rows):
    regions = [
        OCRRegion([[x, y], [x + 80, y], [x + 80, y + 20], [x, y + 20]], text, 0.99, 1, index)
        for index, (x, y, text) in enumerate(rows)
    ]
    return OCRResult("clean-fixture", kind, "fixture.png", regions, metadata={"page_width": 1000, "page_height": 1200})


class CleanExtractorTests(unittest.TestCase):
    def test_composite_quantity_unit_uses_one_width(self):
        result = _result("Commercial Invoice", [
            (40, 300, "Product Code"), (230, 300, "Description of Goods"),
            (470, 300, "Q'ty/Unit"), (590, 300, "HS Code"),
            (690, 300, "Unit Price"), (830, 300, "Amount"),
            (40, 350, "A-1"), (230, 350, "STEEL BOLT"), (470, 350, "4"),
            (470, 375, "EA"), (590, 350, "7318.15"),
            (690, 350, "$2.50"), (830, 350, "$10.00"),
        ])
        items = resolve_table(Layout(result))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].description.value, "STEEL BOLT")
        self.assertEqual(items[0].quantity.value, "4")
        self.assertEqual(items[0].unit.value, "EA")

    def test_missing_header_fallback_keeps_rightmost_amount_order(self):
        result = _result("Commercial Invoice", [
            (100, 500, "MACHINE PART"), (520, 500, "7318.15"),
            (620, 500, "3"), (680, 500, "BOX"),
            (800, 500, "$2.50"), (920, 500, "$7.50"),
            (100, 560, "SECOND PART"), (520, 560, "7318.16"),
            (620, 560, "4"), (680, 560, "EA"),
            (800, 560, "$1.00"), (920, 560, "$4.00"),
        ])
        items = resolve_table(Layout(result))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].quantity.value, "3")
        self.assertEqual(items[0].unit.value, "BOX")
        self.assertEqual(items[1].amount.value, "$4.00")

    def test_party_selection_preserves_same_as_value(self):
        result = _result("Packing List", [
            (100, 200, "Seller"), (100, 230, "ACME INDUSTRIES"),
            (100, 300, "Notify Party"), (100, 330, "SAME AS CONSIGNEE"),
        ])
        document = EXTRACTORS["Packing List"](result).to_dict()
        self.assertEqual(document["exporter"]["value"], "ACME INDUSTRIES")

    def test_phone_like_identifier_is_not_a_document_number(self):
        self.assertFalse(is_identifier("01604-0950-6994"))
        self.assertTrue(is_identifier("M2143251NS61189"))

    def test_clean_output_has_source_evidence(self):
        result = _result("Commercial Invoice", [(100, 100, "Seller"), (100, 130, "ACME INDUSTRIES")])
        document = EXTRACTORS["Commercial Invoice"](result).to_dict()
        seller = document["seller"]
        self.assertEqual(seller["status"], "extracted")
        self.assertEqual(seller["source_text"], "ACME INDUSTRIES")
        self.assertIsNotNone(seller["bbox"])

    def test_party_role_conflict_and_right_column_are_rejected(self):
        result = _result("B/L", [
            (100, 100, "Shipper"), (100, 130, "SHIPPER COMPANY LTD."),
            (700, 100, "Vessel"), (700, 130, "OCEAN CARRIER"),
            (100, 220, "Consignee"), (100, 250, "CONSIGNEE COMPANY LTD."),
        ])
        document = EXTRACTORS["B/L"](result).to_dict()
        self.assertEqual(document["shipper"]["value"], "SHIPPER COMPANY LTD.")
        self.assertNotEqual(document["shipper"]["value"], "OCEAN CARRIER")

    def test_table_footer_does_not_contaminate_description(self):
        result = _result("Packing List", [
            (100, 300, "Description"), (450, 300, "Quantity"),
            (100, 350, "STEEL BOLT"), (450, 350, "4"),
            (100, 390, "SIGNED BY EXPORTER"),
        ])
        items = resolve_table(Layout(result))
        self.assertEqual(items[0].description.value, "STEEL BOLT")

    def test_transport_scalar_stays_in_anchor_column(self):
        result = _result("B/L", [
            (100, 300, "Port of Loading"), (100, 340, "OSAKA, JAPAN"),
            (700, 300, "Party to contact"), (700, 340, "OTHER CARRIER"),
        ])
        values = scalar_candidates(Layout(result), "port_of_loading")
        self.assertEqual(values[0].value, "OSAKA, JAPAN")


if __name__ == "__main__":
    unittest.main()
