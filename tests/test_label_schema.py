import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.label_schema import validate_label_schema


def valid_logistics_record():
    return {
        "Annotation": {"object_recognition": 1, "text_language": 0},
        "DataSet": {
            "category": 0,
            "identifier": "dataset-id",
            "label_path": "labels",
            "name": "dataset",
            "src_path": "images",
            "type": 1,
        },
        "Images": {
            "data_captured": "2022.11.07",
            "form_type": "상업송장",
            "height": 200,
            "identifier": "image-id",
            "type": "PNG",
            "width": 100,
        },
        "bbox": [
            {
                "data": "text",
                "id": "uuid",
                "x": [1, 1, 10, 10],
                "y": [2, 20, 2, 20],
            }
        ],
    }


class LabelSchemaTest(unittest.TestCase):
    def test_logistics_schema_is_valid(self):
        self.assertEqual(validate_label_schema(valid_logistics_record()), [])

    def test_empty_text_and_missing_optional_fields_are_valid(self):
        record = valid_logistics_record()
        record["bbox"][0]["data"] = ""
        self.assertEqual(validate_label_schema(record), [])

    def test_financial_schema_variants_are_outside_target_schema(self):
        record = valid_logistics_record()
        record["Dataset"] = record.pop("DataSet")
        record["Images"]["device_model"] = 0
        record["bbox"][0]["data_type"] = 1

        self.assertNotEqual(validate_label_schema(record), [])


if __name__ == "__main__":
    unittest.main()
