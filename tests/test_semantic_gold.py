import unittest

from scripts.build_semantic_field_gold import _gold
from scripts.build_semantic_v3_gold import build_v3


def token(text, x1, y1, x2=None, y2=None):
    x2 = x2 if x2 is not None else x1 + 20
    y2 = y2 if y2 is not None else y1 + 20
    return {"data": text, "x": [x1, x1, x2, x2], "y": [y1, y2, y1, y2]}


class SemanticGoldTests(unittest.TestCase):
    def test_bl_number_and_shipment_date_use_their_typed_zones(self):
        payload = {"bbox": [
            token("HG732993", 1230, 306, 1330, 330),
            token("APR", 1233, 234, 1280, 258),
            token("24,", 1290, 234, 1320, 258),
            token("2009", 1330, 234, 1390, 258),
        ]}
        fields = {field["field_name"]: field for field in _gold(payload, "B/L")}
        self.assertEqual(fields["bl_number"]["value"], "HG732993")
        self.assertEqual(fields["shipment_date"]["value"], "APR 24, 2009")

    def test_party_gold_keeps_the_company_line_only(self):
        payload = {"bbox": [
            token("TELIANT", 78, 310, 180, 334),
            token("MORTGAGE", 188, 310, 300, 334),
            token("226,", 73, 738, 120, 762),
        ]}
        fields = {field["field_name"]: field for field in _gold(payload, "B/L")}
        self.assertEqual(fields["shipper"]["value"], "TELIANT MORTGAGE")
        self.assertNotIn("226", fields["shipper"]["value"])

    def test_prediction_is_not_an_input_to_gold(self):
        payload = {"bbox": [token("SOURCE", 100, 300)]}
        fields = _gold(payload, "B/L")
        self.assertTrue(all("predicted" not in field for field in fields))

    def test_bl_gross_gold_rejects_cbm_from_total_row(self):
        payload = {"bbox": [
            token("70KG", 1182, 1428, 1246, 1451),
            token("547.88", 1353, 1425, 1426, 1447),
            token("CBM", 1438, 1426, 1492, 1448),
            token("TOTAL", 1059, 1435, 1119, 1451),
        ]}
        fields = {field["field_name"]: field for field in _gold(payload, "B/L")}
        self.assertEqual(fields["gross_weight"]["value"], "70KG")

    def test_v3_bl_uses_party_order_and_vessel_aligned_port_rows(self):
        payload = {"bbox": [
            token("SHIPPER CO LTD", 90, 240, 300, 260),
            token("CONSIGNEE CO LTD", 90, 440, 330, 460),
            token("NOTIFY PARTY CO LTD", 90, 640, 350, 660),
            token("VESSEL ONE", 90, 920, 240, 944),
            token("INITIAL PLACE, COUNTRY", 490, 840, 720, 864),
            token("LOAD PORT, COUNTRY", 490, 920, 720, 944),
            token("DISCHARGE PORT, COUNTRY", 90, 990, 350, 1014),
            token("DELIVERY PORT, COUNTRY", 90, 1080, 350, 1104),
        ]}
        fields = {field["field_name"]: field for field in build_v3(payload, "B/L")}
        self.assertEqual(fields["shipper"]["value"], "SHIPPER CO LTD")
        self.assertEqual(fields["consignee"]["value"], "CONSIGNEE CO LTD")
        self.assertEqual(fields["notify_party"]["value"], "NOTIFY PARTY CO LTD")
        self.assertEqual(fields["vessel"]["value"], "VESSEL ONE")
        self.assertEqual(fields["port_of_loading"]["value"], "LOAD PORT, COUNTRY")
        self.assertEqual(fields["port_of_discharge"]["value"], "DISCHARGE PORT, COUNTRY")

    def test_v3_ci_splits_quantity_and_unit_from_one_source_token(self):
        payload = {"bbox": [
            token("Conveyor", 521, 1100, 650, 1124),
            token("Device", 672, 1100, 770, 1124),
            token("7 PC", 933, 1100, 980, 1124),
            token("$9.11", 1143, 1100, 1238, 1124),
            token("$63.77", 1354, 1100, 1497, 1124),
        ]}
        fields = {field["field_name"]: field for field in build_v3(payload, "Commercial Invoice")}
        self.assertEqual(fields["items[0].quantity"]["value"], "7")
        self.assertEqual(fields["items[0].unit"]["value"], "PC")


if __name__ == "__main__":
    unittest.main()
