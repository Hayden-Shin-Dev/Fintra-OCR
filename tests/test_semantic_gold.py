import unittest

from scripts.build_semantic_field_gold import _gold


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


if __name__ == "__main__":
    unittest.main()
