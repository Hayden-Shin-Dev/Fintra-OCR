import unittest

from fintra.extraction.documents import extract_bill_of_lading, extract_packing_list
from fintra.ocr.adapter import OCRRegion, OCRResult


def region(text, x1, y1, x2, y2, index):
    return OCRRegion([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], text, index=index)


def transformed(result, scale, offset_x=0, offset_y=0):
    regions = []
    for item in result.regions:
        polygon = [[x * scale + offset_x, y * scale + offset_y] for x, y in item.polygon]
        regions.append(OCRRegion(polygon, item.text, item.confidence, item.page, item.index))
    return OCRResult(
        result.document_id,
        result.document_type,
        result.source_file,
        regions,
        metadata={
            "page_width": 1654 * scale,
            "page_height": 2340 * scale,
            "page_origin_x": offset_x,
            "page_origin_y": offset_y,
        },
    )


class DocumentLayoutExtractionTests(unittest.TestCase):
    def test_bl_structural_zones_separate_number_parties_and_total_weight(self):
        result = OCRResult(
            "bl-1", "B/L", "bl.png", [
                region("HG732993", 1230, 305, 1347, 328, 0),
                region("TELIANT MORTGAGE", 77, 312, 337, 335, 1),
                region("NONGS DRUG STORES", 73, 500, 356, 523, 2),
                region("QILGRIM'S PRIDE", 73, 702, 356, 725, 3),
                region("ARGOLIKOS", 71, 946, 217, 970, 4),
                region("AYAMONTE, SPAIN", 485, 946, 714, 972, 5),
                region("YIZHENG, CHINA", 70, 1011, 273, 1038, 6),
                region("70KG", 1182, 1428, 1246, 1451, 7),
                region("TOTAL", 1056, 1433, 1121, 1453, 8),
                region("TOTAL", 1258, 2085, 1319, 2103, 9),
                region("BACKSHELL", 607, 1211, 752, 1235, 10),
            ],
        )
        document = extract_bill_of_lading(result)
        self.assertEqual(document.bl_number.value, "HG732993")
        self.assertEqual(document.shipper.value, "TELIANT MORTGAGE")
        self.assertEqual(document.consignee.value, "NONGS DRUG STORES")
        self.assertEqual(document.notify_party.value, "QILGRIM'S PRIDE")
        self.assertEqual(document.gross_weight.value, "70KG")

    def test_packing_party_headings_are_not_returned_as_values(self):
        result = OCRResult(
            "pl-1", "Packing List", "pl.png", [
                region("Seller", 136, 282, 215, 304, 0),
                region("Solutions Co., Ltd.", 244, 320, 473, 344, 1),
                region("Consignee", 136, 492, 250, 514, 2),
                region("Boccomi Co., Ltd.", 137, 532, 352, 557, 3),
                region("Description", 250, 1000, 400, 1020, 4),
                region("Quantity", 850, 1000, 950, 1020, 5),
                region("Widget", 140, 1080, 250, 1102, 6),
                region("4", 850, 1080, 870, 1102, 7),
            ],
        )
        document = extract_packing_list(result)
        self.assertEqual(document.exporter.value, "Solutions Co., Ltd.")
        self.assertEqual(document.consignee.value, "Boccomi Co., Ltd.")
        self.assertEqual(len(document.items), 1)
        self.assertEqual(document.items[0].description.value, "Widget")
        self.assertEqual(document.items[0].quantity.value, "4")

    def test_typed_date_and_last_port_line_are_selected(self):
        result = OCRResult(
            "bl-2", "B/L", "bl.png", [
                region("DATE SHIPPED", 1230, 204, 1390, 225, 0),
                region("APR 24, 2009", 1230, 234, 1390, 258, 1),
                region("CFS/CFS", 485, 878, 596, 903, 2),
                region("AYAMONTE, SPAIN", 485, 946, 714, 972, 3),
            ],
        )
        document = extract_bill_of_lading(result)
        self.assertEqual(document.shipment_date.value, "APR 24, 2009")
        self.assertEqual(document.port_of_loading.value, "AYAMONTE, SPAIN")

    def test_notify_same_as_consignee_is_not_truncated_at_inline_heading(self):
        result = OCRResult(
            "bl-3", "B/L", "bl.png", [
                region("Notify Party (No claim shall attach for failure to notify)", 90, 600, 620, 625, 0),
                region("SAME AS CONSIGNEE", 90, 640, 350, 665, 1),
            ],
        )
        document = extract_bill_of_lading(result)
        self.assertEqual(document.notify_party.value, "SAME AS CONSIGNEE")

    def test_template_zones_follow_page_scale_and_origin(self):
        base = OCRResult(
            "bl-scale", "B/L", "bl.png", [
                region("HG732993", 1230, 305, 1347, 328, 0),
                region("TELIANT MORTGAGE", 77, 312, 337, 335, 1),
                region("NONGS DRUG STORES", 73, 500, 356, 523, 2),
                region("QILGRIM'S PRIDE", 73, 702, 356, 725, 3),
                region("ARGOLIKOS", 71, 946, 217, 970, 4),
                region("AYAMONTE, SPAIN", 485, 946, 714, 972, 5),
                region("YIZHENG, CHINA", 70, 1011, 273, 1038, 6),
                region("70KG", 1182, 1428, 1246, 1451, 7),
                region("TOTAL", 1056, 1433, 1121, 1453, 8),
                region("BACKSHELL", 607, 1211, 752, 1235, 10),
            ],
        )
        expected = extract_bill_of_lading(base).to_dict()
        for scale, offset_x, offset_y in ((0.75, 17, 23), (1.25, 31, 19)):
            actual = extract_bill_of_lading(transformed(base, scale, offset_x, offset_y)).to_dict()
            for field in ("bl_number", "shipper", "consignee", "notify_party", "vessel", "port_of_loading", "port_of_discharge", "goods_description"):
                self.assertEqual(actual[field]["value"], expected[field]["value"], field)


if __name__ == "__main__":
    unittest.main()
