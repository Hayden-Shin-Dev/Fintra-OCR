import json
import tempfile
import unittest
from pathlib import Path

from fintra.ocr.adapter import FixtureOCRAdapter
from fintra.services.document_service import extract_document


class DocumentServiceTests(unittest.TestCase):
    def test_file_and_fixture_adapter_produce_canonical_document_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document = root / "invoice.png"
            document.write_bytes(b"not parsed by fixture adapter")
            fixture = root / "invoice.json"
            fixture.write_text(json.dumps({
                "document_id": "invoice-1",
                "regions": [
                    {"polygon": [[850, 280], [1000, 280], [1000, 310], [850, 310]], "text": "INV-1"},
                    {"polygon": [[100, 320], [300, 320], [300, 350], [100, 350]], "text": "Seller Co"},
                ],
            }), encoding="utf-8")
            payload = extract_document(document, "Commercial Invoice", FixtureOCRAdapter(root))

            self.assertEqual(payload["schema_version"], "fintra-document-contract.v1")
            self.assertEqual(payload["document"]["metadata"]["document_type"], "Commercial Invoice")
            self.assertEqual(payload["ocr"]["region_count"], 2)
            self.assertIn("seller", payload["document"])

    def test_missing_file_is_rejected_before_ocr(self):
        with self.assertRaises(FileNotFoundError):
            extract_document(Path("does-not-exist.png"), "B/L", FixtureOCRAdapter(Path(".")))


if __name__ == "__main__":
    unittest.main()
