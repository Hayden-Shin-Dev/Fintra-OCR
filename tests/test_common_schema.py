import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.common_schema import (
    build_common_document,
    build_common_document_from_form_type,
    document_type_from_form_type,
    validate_common_document,
)
from fintra_ocr.field_evidence import make_field_evidence
from fintra_ocr.normalization import normalize_fields
from fintra_ocr.prediction_parser import OCRPrediction


def evidence(field_name, value, status="found", reason=None):
    prediction = OCRPrediction(value or "", (10, 20, 20, 10), (10, 10, 20, 20), 0.98)
    return make_field_evidence(field_name, [prediction], (0,), value, status=status, reason=reason)


class CommonSchemaTest(unittest.TestCase):
    def test_maps_actual_form_types_to_public_document_types(self):
        self.assertEqual(document_type_from_form_type("\uc0c1\uc5c5\uc1a1\uc7a5"), "commercial_invoice")
        self.assertEqual(document_type_from_form_type("\ud3ec\uc7a5\uba85\uc138\uc11c"), "packing_list")
        self.assertEqual(document_type_from_form_type("\uc120\ud558\uc99d\uad8c"), "bill_of_lading")

    def test_builds_invoice_with_common_field_container(self):
        fields = normalize_fields({
            "date": evidence("date", "20-Apr-2017"),
            "amount": evidence("amount", "$1,216.98"),
            "buyer": evidence("buyer", "Same to consignee", status="ambiguous"),
            "currency": evidence("currency", "$", status="ambiguous"),
        })

        document = build_common_document("commercial_invoice", "sample-id", fields)

        self.assertEqual(document["processing_status"], "partial")
        self.assertEqual(document["fields"]["date"]["normalized"], "2017-04-20")
        self.assertEqual(document["fields"]["amount"]["normalized"]["value"], 1216.98)
        self.assertEqual(document["fields"]["currency"]["status"], "ambiguous")
        self.assertEqual(document["fields"]["buyer"]["bbox"], [[10, 10], [20, 10], [20, 20], [10, 20]])
        validate_common_document(document)

    def test_keeps_quantity_array_and_measurement_objects(self):
        fields = normalize_fields({
            "quantity": evidence("quantity", "83 | 98 | 26"),
            "number_of_packages": evidence("number_of_packages", "31 PKG"),
            "gross_weight": evidence("gross_weight", "614KG"),
        })

        document = build_common_document_from_form_type("\ud3ec\uc7a5\uba85\uc138\uc11c", "packing-id", fields)

        self.assertEqual(document["processing_status"], "success")
        self.assertEqual(
            document["fields"]["quantity"]["normalized"]["items"],
            [{"value": 83, "unit": None}, {"value": 98, "unit": None}, {"value": 26, "unit": None}],
        )
        self.assertEqual(document["fields"]["number_of_packages"]["normalized"], {"value": 31, "unit": "PKG"})
        self.assertEqual(document["fields"]["gross_weight"]["normalized"], {"value": 614, "unit": "KG"})

    def test_rejects_field_outside_document_contract(self):
        with self.assertRaises(ValueError):
            build_common_document("packing_list", "packing-id", {"date": evidence("date", "20-Apr-2017")})


if __name__ == "__main__":
    unittest.main()
