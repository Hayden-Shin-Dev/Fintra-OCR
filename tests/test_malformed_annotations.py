import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.label_schema import validate_label_schema
from test_label_schema import valid_logistics_record


class MalformedAnnotationTest(unittest.TestCase):
    def assert_invalid(self, record, expected_message):
        errors = validate_label_schema(record)
        self.assertTrue(any(expected_message in error for error in errors), errors)

    def test_missing_bbox_text_is_invalid(self):
        record = valid_logistics_record()
        del record["bbox"][0]["data"]
        self.assert_invalid(record, "bbox[0] is missing data")

    def test_non_string_id_is_invalid_for_target_schema(self):
        record = valid_logistics_record()
        record["bbox"][0]["id"] = 1
        self.assert_invalid(record, "bbox[0].id must be a string")

    def test_invalid_coordinate_shape_is_invalid(self):
        record = valid_logistics_record()
        record["bbox"][0]["x"] = [1, 2, 3]
        self.assert_invalid(record, "bbox[0].x must contain four coordinates")

    def test_financial_only_bbox_fields_are_invalid_for_target_schema(self):
        record = valid_logistics_record()
        record["bbox"][0]["data_type"] = 1
        self.assert_invalid(record, "bbox[0] contains unexpected field data_type")


if __name__ == "__main__":
    unittest.main()
