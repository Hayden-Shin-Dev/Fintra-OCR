import unittest

from fintra.extraction.documents import extract_commercial_invoice
from fintra.ocr.adapter import OCRRegion, OCRResult


class OCRExtractionTests(unittest.TestCase):
    def test_inline_labels_keep_source_evidence(self):
        result = OCRResult(
            document_id="ci-1",
            document_type="Commercial Invoice",
            source_file="invoice.png",
            regions=[
                OCRRegion([[0, 0], [100, 0], [100, 20], [0, 20]], "Invoice No: INV-42", index=0),
                OCRRegion([[0, 30], [100, 30], [100, 50], [0, 50]], "Total Amount: USD 125.50", index=1),
                OCRRegion([[0, 60], [100, 60], [100, 80], [0, 80]], "ITEM: Widget | 2 EA | 10.00 | 20.00", index=2),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.invoice_number.value, "INV-42")
        self.assertEqual(invoice.invoice_number.source_text, "Invoice No: INV-42")
        self.assertEqual(invoice.total_amount.value, "USD 125.50")
        self.assertEqual(len(invoice.items), 1)

    def test_missing_field_is_explicit(self):
        result = OCRResult("ci-2", "Commercial Invoice", "invoice.png", [])
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.seller.status.value, "missing")

    def test_aihub_value_only_layout_is_supported(self):
        result = OCRResult(
            "ci-layout", "Commercial Invoice", "invoice.png", [
                OCRRegion([[1111, 307], [1195, 307], [1195, 329], [1111, 329]], "529294", index=0),
                OCRRegion([[1111, 391], [1266, 391], [1266, 413], [1111, 413]], "13-Nov-2011", index=1),
                OCRRegion([[173, 325], [602, 325], [602, 351], [173, 351]], "Kanse Machinery Eng Co., Ltd.", index=2),
                OCRRegion([[169, 585], [626, 585], [626, 612], [169, 612]], "Tkender Newton Realty Co., Ltd.", index=3),
                OCRRegion([[1326, 1551], [1454, 1551], [1454, 1575], [1326, 1575]], "$7,754.30", index=4),
                OCRRegion([[571, 1847], [629, 1847], [629, 1871], [571, 1871]], "USD", index=5),
                OCRRegion([[178, 1060], [399, 1060], [399, 1083], [178, 1083]], "Oil Tank Cover,", index=6),
                OCRRegion([[181, 1093], [415, 1093], [415, 1115], [181, 1115]], "For Transmission", index=7),
                OCRRegion([[889, 1060], [905, 1060], [905, 1082], [889, 1082]], "3", index=8),
                OCRRegion([[971, 1060], [1017, 1060], [1017, 1082], [971, 1082]], "BOX", index=9),
                OCRRegion([[1146, 1060], [1216, 1060], [1216, 1084], [1146, 1084]], "$9.74", index=10),
                OCRRegion([[1350, 1059], [1435, 1059], [1435, 1084], [1350, 1084]], "$33.13", index=11),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.invoice_number.value, "529294")
        self.assertEqual(invoice.seller.value, "Kanse Machinery Eng Co., Ltd.")
        self.assertEqual(invoice.buyer.value, "Tkender Newton Realty Co., Ltd.")
        self.assertEqual(invoice.total_amount.value, "$7,754.30")
        self.assertEqual(invoice.items[0].quantity.value, "3")


if __name__ == "__main__":
    unittest.main()
