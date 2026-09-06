import unittest

from scripts.build_semantic_field_gold import _gold
from scripts.build_semantic_v3_gold import build_v3, v2
from scripts.build_semantic_v3_2_gold import _ci_table_v2
from scripts.validate_semantic_v3 import _field_valid


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

    def test_v32_ci_table_keeps_rows_and_resolves_numeric_columns(self):
        payload = {"bbox": [
            token("SKU-1", 70, 1000),
            token("Widget", 250, 1000, 360, 1024),
            token("1234.56", 700, 1000, 790, 1024),
            token("8", 865, 1000),
            token("EA", 1045, 1000),
            token("$12.50", 1250, 1000),
            token("$100.00", 1435, 1000),
            token("SKU-2", 70, 1110),
            token("Second Widget", 250, 1110, 390, 1134),
            token("2222.22", 700, 1110, 790, 1134),
            token("3", 865, 1110),
            token("BOX", 1045, 1110),
            token("$20.00", 1250, 1110),
            token("$60.00", 1435, 1110),
        ]}
        fields = {field["field_name"]: field for field in _ci_table_v2(v2._tokens(payload))}
        self.assertEqual(fields["items[0].quantity"]["value"], "8")
        self.assertEqual(fields["items[0].unit"]["value"], "EA")
        self.assertEqual(fields["items[0].unit_price"]["value"], "$12.50")
        self.assertEqual(fields["items[0].amount"]["value"], "$100.00")
        self.assertEqual(fields["items[1].quantity"]["value"], "3")
        self.assertEqual(fields["items[1].unit"]["value"], "BOX")

    def test_v3_invariants_reject_numeric_description_voyage_party_and_incoterm_vessel(self):
        self.assertFalse(_field_valid({"field_name": "items[0].description", "value": "7646.00"}, ["7", "PC", "$7646.00"], "Commercial Invoice")[0])
        self.assertFalse(_field_valid({"field_name": "shipper", "value": "PRINCESS OF LUCK V.427"}, [], "B/L")[0])
        self.assertFalse(_field_valid({"field_name": "vessel", "value": "DAF"}, [], "B/L")[0])


if __name__ == "__main__":
    unittest.main()
