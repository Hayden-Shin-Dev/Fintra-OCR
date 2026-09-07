import json
import unittest
from pathlib import Path

from fintra.extraction.v2 import extract_document
from fintra.extraction.v2.specs import DOCUMENT_FIELDS, ITEM_FIELDS, SPECS
from fintra.ocr.adapter import OCRRegion, OCRResult


ROOT = Path(__file__).resolve().parents[1]


def _result(document_type: str) -> OCRResult:
    return OCRResult(
        "contract-1",
        document_type,
        "contract.png",
        [
            OCRRegion([[0, 0], [100, 0], [100, 20], [0, 20]], "DOCUMENT NO", index=0),
            OCRRegion([[110, 0], [220, 0], [220, 20], [110, 20]], "DOC-1", index=1),
        ],
        metadata={"page_width": 220, "page_height": 100},
    )


class SchemaV2ContractTests(unittest.TestCase):
    def test_artifact_inventory_is_fully_defined_and_wired(self):
        artifact = json.loads((ROOT / "artifacts/fintra/schema-v2/field_schema_v2.json").read_text(encoding="utf-8"))
        intended = {item["canonical_name"] for item in artifact["fields"]}
        wired = {name for values in DOCUMENT_FIELDS.values() for name in values}
        wired.update(name for values in ITEM_FIELDS.values() for name in values)
        self.assertEqual(len(intended), 72)
        self.assertEqual(intended, set(SPECS))
        self.assertEqual(intended, wired)

    def test_every_applicable_document_slot_has_provenance_keys(self):
        for document_type in DOCUMENT_FIELDS:
            payload = extract_document(_result(document_type)).to_dict()
            for field in DOCUMENT_FIELDS[document_type]:
                self.assertIn(field, payload)
                self.assertIn("source_label", payload[field])
                self.assertIn("semantic_relation", payload[field])
            for item in payload["items"]:
                for field in ITEM_FIELDS.get(document_type, ()):
                    self.assertIn(field, item)
                    self.assertIn("source_label", item[field])
                    self.assertIn("semantic_relation", item[field])

    def test_missing_contract_slot_is_explicit(self):
        payload = extract_document(_result("B/L")).to_dict()
        self.assertIn("port_of_loading", payload)
        self.assertIsNone(payload["port_of_loading"]["value"])
        self.assertEqual(payload["port_of_loading"]["status"], "missing")
        self.assertIsNone(payload["port_of_loading"]["source_label"])
        self.assertIsNone(payload["port_of_loading"]["semantic_relation"])

    def test_dedicated_ui_is_bound_to_production_ocr_and_v2(self):
        source = (ROOT / "extractor_v2_app.py").read_text(encoding="utf-8")
        self.assertIn("from fintra.ocr.paddle_backend import PaddleOCRBackend", source)
        self.assertIn("from fintra.extraction.v2 import EXTRACTORS", source)
        self.assertIn("Source Label", source)
        self.assertIn("Semantic Relation", source)
        self.assertIn("OCR Detected Text", source)


if __name__ == "__main__":
    unittest.main()
