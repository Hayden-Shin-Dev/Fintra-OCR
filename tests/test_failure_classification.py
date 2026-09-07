import unittest

from scripts.classify_extractor_failures import classify


class FailureClassificationTests(unittest.TestCase):
    def test_unrecoverable_is_ocr_stage(self):
        self.assertEqual(classify({"raw_ocr_recoverable": "False"}), "OCR_UNRECOVERABLE")

    def test_item_field_with_evidence_is_column_stage(self):
        self.assertEqual(classify({
            "raw_ocr_recoverable": "True",
            "extractor_correct": "False",
            "predicted_value": "EA",
            "extractor_source_text": "EA",
            "field_name": "items[0].unit",
            "candidate_hit": "True",
        }), "COLUMN_MAPPING_FAILURE")

    def test_party_field_with_evidence_is_role_stage(self):
        self.assertEqual(classify({
            "raw_ocr_recoverable": "True",
            "extractor_correct": "False",
            "predicted_value": "ACME",
            "extractor_source_text": "ACME",
            "field_name": "consignee",
            "candidate_hit": "True",
        }), "ROLE_ASSIGNMENT_FAILURE")


if __name__ == "__main__":
    unittest.main()
