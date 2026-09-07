import unittest

from app import _evidence_fields


class LocalUiHelperTests(unittest.TestCase):
    def test_evidence_fields_flattens_items_and_keeps_status(self):
        payload = {
            "metadata": {"document_type": "Commercial Invoice"},
            "items": [{"description": {"value": "Widget", "status": "extracted", "bbox": []}}],
        }
        fields = list(_evidence_fields(payload))
        self.assertEqual(fields[0][0], "items[0].description")
        self.assertEqual(fields[0][1]["status"], "extracted")


if __name__ == "__main__":
    unittest.main()
