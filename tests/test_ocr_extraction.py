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


if __name__ == "__main__":
    unittest.main()
