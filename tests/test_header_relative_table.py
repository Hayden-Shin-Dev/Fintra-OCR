import unittest

from fintra.extraction.table import extract_header_relative_items
from fintra.ocr.adapter import OCRRegion, OCRResult


def _result(rows):
    regions = []
    for index, (x, y, text) in enumerate(rows):
        regions.append(OCRRegion([[x, y], [x + 80, y], [x + 80, y + 20], [x, y + 20]], text, 0.99, 1, index))
    return OCRResult("fixture", "Commercial Invoice", "fixture.png", regions, metadata={"page_width": 1000, "page_height": 1200})


class HeaderRelativeTableTests(unittest.TestCase):
    def test_columns_follow_header_not_fixed_template_positions(self):
        result = _result([
            (40, 300, "Product Code"), (230, 300, "Description of Goods"),
            (470, 300, "Q'ty/Unit"), (590, 300, "HS Code"),
            (690, 300, "Unit Price"), (830, 300, "Amount"),
            (40, 350, "A-1"), (230, 350, "STEEL BOLT"), (470, 350, "4"),
            (470, 375, "EA"), (590, 350, "7318.15"), (690, 350, "$2.50"), (830, 350, "$10.00"),
        ])
        items = extract_header_relative_items(result)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].description.value, "STEEL BOLT")
        self.assertEqual(items[0].quantity.value, "4")
        self.assertEqual(items[0].unit.value, "EA")
        self.assertEqual(items[0].unit_price.value, "$2.50")
        self.assertEqual(items[0].amount.value, "$10.00")

    def test_multiline_description_and_composite_quantity_unit(self):
        result = _result([
            (100, 300, "Shipping mark"), (300, 300, "Goods description"),
            (580, 300, "Quantity/Unit"), (760, 300, "Price"), (900, 300, "Amount"),
            (100, 350, "BOX-1"), (300, 350, "MACHINE PART"), (300, 375, "ASSEMBLY"),
            (580, 350, "3 PKG"), (760, 350, "10.00"), (900, 350, "30.00"),
        ])
        items = extract_header_relative_items(result)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].description.value, "MACHINE PART ASSEMBLY")
        self.assertEqual(items[0].quantity.value, "3")
        self.assertEqual(items[0].unit.value, "PKG")


if __name__ == "__main__":
    unittest.main()
