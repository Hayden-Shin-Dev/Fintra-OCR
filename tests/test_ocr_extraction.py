import unittest

from fintra.extraction.documents import extract_bill_of_lading, extract_commercial_invoice, extract_packing_list, _regions
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

    def test_duplicate_equal_tokens_are_not_ambiguous(self):
        result = OCRResult(
            "ci-currency", "Commercial Invoice", "invoice.png", [
                OCRRegion([[1, 1], [20, 1], [20, 20], [1, 20]], "USD", index=0),
                OCRRegion([[1, 30], [20, 30], [20, 50], [1, 50]], "USD", index=1),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.currency.status.value, "extracted")
        self.assertEqual(invoice.currency.value, "USD")

    def test_corrupted_party_heading_is_not_returned_as_value(self):
        result = OCRResult(
            "bl-party-heading", "B/L", "bl.png", [
                OCRRegion([[100, 300], [300, 300], [300, 325], [100, 325]], "Shippor/ Exporer", index=0),
                OCRRegion([[100, 340], [330, 340], [330, 365], [100, 365]], "ACME LOGISTICS CO.", index=1),
            ],
        )
        bl = extract_bill_of_lading(result)
        self.assertEqual(bl.shipper.value, "ACME LOGISTICS CO.")
        self.assertEqual(bl.shipper.source_text, "ACME LOGISTICS CO.")

    def test_inline_party_heading_is_removed_from_value(self):
        result = OCRResult(
            "ci-inline-party-heading", "Commercial Invoice", "invoice.png", [
                OCRRegion([[100, 310], [300, 310], [300, 335], [100, 335]], "Buyer: BETA INC", index=0),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.buyer.value, "BETA INC")
        self.assertEqual(invoice.buyer.source_text, "Buyer: BETA INC")

    def test_date_heading_is_not_returned_as_inline_date_value(self):
        result = OCRResult(
            "ci-date-heading", "Commercial Invoice", "invoice.png", [
                OCRRegion([[906, 390], [1063, 390], [1063, 418], [906, 418]], "Date of Issue", index=0),
                OCRRegion([[1109, 388], [1265, 388], [1265, 414], [1109, 414]], "13-Nov-2011", index=1),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.invoice_date.value, "13-Nov-2011")

    def test_party_heading_prefers_below_value_over_adjacent_column(self):
        result = OCRResult(
            "ci-party-column", "Commercial Invoice", "invoice.png", [
                OCRRegion([[170, 680], [300, 680], [300, 705], [170, 705]], "Consignee", index=0),
                OCRRegion([[890, 680], [1050, 680], [1050, 705], [890, 705]], "09-23-2002", index=1),
                OCRRegion([[170, 720], [350, 720], [350, 745], [170, 745]], "BETA INC", index=2),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.buyer.value, "BETA INC")

    def test_package_mark_is_not_included_in_item_description(self):
        result = OCRResult(
            "ci-package-mark", "Commercial Invoice", "invoice.png", [
                OCRRegion([[150, 1000], [280, 1000], [280, 1020], [150, 1020]], "DESCRIPTION", index=0),
                OCRRegion([[820, 1000], [900, 1000], [900, 1020], [820, 1020]], "QUANTITY", index=1),
                OCRRegion([[250, 1100], [310, 1100], [310, 1120], [250, 1120]], "PKGS", index=2),
                OCRRegion([[400, 1100], [550, 1100], [550, 1120], [400, 1120]], "Widget", index=3),
                OCRRegion([[820, 1100], [850, 1100], [850, 1120], [820, 1120]], "2", index=4),
            ],
        )
        invoice = extract_commercial_invoice(result)
        self.assertEqual(invoice.items[0].description.value, "Widget")

    def test_bl_label_candidates_do_not_select_later_template_text(self):
        result = OCRResult(
            "bl-labels", "B/L", "bl.png", [
                OCRRegion([[100, 850], [280, 850], [280, 875], [100, 875]], "VESSEL NAME", index=0),
                OCRRegion([[100, 885], [250, 885], [250, 910], [100, 910]], "OCEAN STAR", index=1),
                OCRRegion([[500, 850], [680, 850], [680, 875], [500, 875]], "PORT OF LOADING", index=2),
                OCRRegion([[500, 885], [680, 885], [680, 910], [500, 910]], "BUSAN, KOREA", index=3),
                OCRRegion([[100, 950], [300, 950], [300, 975], [100, 975]], "PORT OF DISCHARGE", index=4),
                OCRRegion([[100, 985], [280, 985], [280, 1010], [100, 1010]], "OSAKA, JAPAN", index=5),
            ],
        )
        bl = extract_bill_of_lading(result)
        self.assertEqual(bl.vessel.value, "OCEAN STAR")
        self.assertEqual(bl.port_of_loading.value, "BUSAN, KOREA")
        self.assertEqual(bl.port_of_discharge.value, "OSAKA, JAPAN")

    def test_bl_number_is_extracted_from_combined_date_header(self):
        result = OCRResult(
            "bl-combined-header", "B/L", "bl.png", [
                OCRRegion([[1200, 250], [1500, 250], [1500, 285], [1200, 285]], "06-NOV-2011 | HG787486", index=0),
            ],
        )
        self.assertEqual(extract_bill_of_lading(result).bl_number.value, "HG787486")

    def test_contained_paddle_fragment_is_removed_but_adjacent_word_is_kept(self):
        result = OCRResult(
            "ci-fragments", "Commercial Invoice", "invoice.png", [
                OCRRegion([[100, 100], [420, 100], [420, 125], [100, 125]], "ACME MACHINERY CO., LTD.", index=0),
                OCRRegion([[290, 99], [420, 126], [420, 126], [290, 126]], "Y CO., LTD.", index=1),
                OCRRegion([[430, 100], [510, 100], [510, 125], [430, 125]], "TOKYO", index=2),
            ],
        )
        self.assertEqual([region.text for region in _regions(result)], ["ACME MACHINERY CO., LTD.", "TOKYO"])

    def test_overlapping_corrupted_paddle_fragment_is_removed(self):
        result = OCRResult(
            "ci-overlap-fragment", "Commercial Invoice", "invoice.png", [
                OCRRegion([[176, 577], [503, 577], [503, 608], [176, 608]], "Derry Law Firm Co., Ltd.", index=0),
                OCRRegion([[374, 572], [506, 572], [506, 610], [374, 610]], "n Co., Ltd.", index=1),
            ],
        )
        self.assertEqual([region.text for region in _regions(result)], ["Derry Law Firm Co., Ltd."])

    def test_packing_date_accepts_full_header_date_box(self):
        result = OCRResult(
            "pl-date-header", "Packing List", "packing.png", [
                OCRRegion([[1222, 269], [1408, 269], [1408, 302], [1222, 302]], "Jan 08, 2002", index=0),
                OCRRegion([[1223, 271], [1277, 271], [1277, 302], [1223, 302]], "Jan", index=1),
            ],
        )
        self.assertEqual(extract_packing_list(result).date.value, "Jan 08, 2002")

    def test_invoice_number_is_separated_from_combined_header_date(self):
        result = OCRResult(
            "ci-invoice-header", "Commercial Invoice", "invoice.png", [
                OCRRegion([[913, 291], [1151, 291], [1151, 317], [913, 317]], "Invoice No. and date", index=0),
                OCRRegion([[918, 329], [1017, 329], [1017, 361], [918, 361]], "763488", index=1),
                OCRRegion([[1206, 330], [1365, 330], [1365, 360], [1206, 360]], "21-Mar-2002", index=2),
            ],
        )
        self.assertEqual(extract_commercial_invoice(result).invoice_number.value, "763488")

    def test_ordered_refinement_does_not_reintroduce_removed_fragment(self):
        result = OCRResult(
            "ci-fragments", "Commercial Invoice", "invoice.png", [
                OCRRegion([[100, 320], [420, 320], [420, 345], [100, 345]], "ACME MACHINERY CO., LTD.", index=0),
                OCRRegion([[290, 319], [420, 346], [420, 346], [290, 346]], "Y CO., LTD.", index=1),
            ],
        )
        self.assertEqual(extract_commercial_invoice(result).seller.value, "ACME MACHINERY CO., LTD.")


if __name__ == "__main__":
    unittest.main()
