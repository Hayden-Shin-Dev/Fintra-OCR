import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.field_evidence import make_field_evidence
from fintra_ocr.normalization import normalize_field, normalize_fields
from fintra_ocr.prediction_parser import OCRPrediction


def evidence(field_name, value, status="found"):
    prediction = OCRPrediction(value, (10, 20, 20, 10), (10, 10, 20, 20), 0.98)
    return make_field_evidence(field_name, [prediction], (0,), value, status=status)


class NormalizationTest(unittest.TestCase):
    def test_normalizes_supported_dates(self):
        self.assertEqual(normalize_field("date", evidence("date", "20-Apr-2017")).normalized, "2017-04-20")
        self.assertEqual(normalize_field("on_board_date", evidence("on_board_date", "JUN 11, 2013")).normalized, "2013-06-11")
        self.assertEqual(normalize_field("date", evidence("date", "2024-03-22")).normalized, "2024-03-22")
        self.assertEqual(normalize_field("date", evidence("date", "20-Apr-17")).normalized, "2017-04-20")

    def test_ambiguous_numeric_dates_are_not_silently_forced(self):
        date = normalize_field("date", evidence("date", "03.04.2024"))
        self.assertEqual(date.normalization_status, "ambiguous")
        self.assertEqual(
            date.normalized,
            {"candidates": ["2024-03-04", "2024-04-03"]},
        )

    def test_normalizes_amount_without_inventing_currency(self):
        amount = normalize_field("amount", evidence("amount", "$1,216.98"))

        self.assertEqual(amount.normalized["value"], 1216.98)
        self.assertEqual(amount.normalized["symbol"], "$")
        self.assertIsNone(amount.normalized["currency_code"])
        self.assertEqual(amount.raw_text, "$1,216.98")
        self.assertEqual(amount.bbox, ((10, 10), (20, 10), (20, 20), (10, 20)))
        self.assertEqual(amount.confidence, 0.98)
        self.assertEqual(amount.source_indices, (0,))
        self.assertEqual(amount.status, "found")

    def test_normalizes_ambiguous_currency_without_usd_inference(self):
        currency = normalize_field(
            "currency", evidence("currency", "$", status="ambiguous")
        )

        self.assertEqual(currency.status, "ambiguous")
        self.assertEqual(currency.normalized, {"code": None, "symbol": "$"})
        self.assertEqual(currency.normalization_status, "ambiguous")

    def test_keeps_quantity_items_separate(self):
        quantity = normalize_field("quantity", evidence("quantity", "2 | 3"))

        self.assertEqual(
            quantity.normalized,
            {"items": [{"value": 2, "unit": None}, {"value": 3, "unit": None}]},
        )
        self.assertEqual(quantity.value, "2 | 3")

    def test_rejects_weight_unit_as_quantity_unit(self):
        quantity = normalize_field("quantity", evidence("quantity", "10 KG"))
        self.assertEqual(quantity.normalization_status, "failed")
        self.assertIn("unsupported quantity unit", quantity.normalization_reason)

    def test_normalizes_weight_and_package_units_without_conversion(self):
        self.assertEqual(
            normalize_field("gross_weight", evidence("gross_weight", "614KG")).normalized,
            {"value": 614, "unit": "KG"},
        )
        self.assertEqual(
            normalize_field("number_of_packages", evidence("number_of_packages", "88 BUNDLES")).normalized,
            {"value": 88, "unit": "BUNDLES"},
        )

    def test_preserves_ambiguous_buyer_and_source_evidence(self):
        buyer = normalize_field(
            "buyer", evidence("buyer", "Same to consignee", status="ambiguous")
        )

        self.assertEqual(buyer.status, "ambiguous")
        self.assertEqual(buyer.normalized, "Same to consignee")
        self.assertEqual(buyer.raw_text, "Same to consignee")
        self.assertIsNotNone(buyer.bbox)

    def test_parse_failure_keeps_original_value_and_marks_failure(self):
        date = normalize_field("date", evidence("date", "not-a-date"))

        self.assertEqual(date.value, "not-a-date")
        self.assertIsNone(date.normalized)
        self.assertEqual(date.normalization_status, "failed")

    def test_normalize_fields_does_not_change_field_set(self):
        fields = {"date": evidence("date", "20-Apr-2017"), "amount": evidence("amount", "$1,216.98")}

        normalized = normalize_fields(fields)

        self.assertEqual(set(normalized), set(fields))


if __name__ == "__main__":
    unittest.main()

