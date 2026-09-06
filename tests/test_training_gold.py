import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_training_gold import build


class TrainingGoldTests(unittest.TestCase):
    def test_build_is_prediction_blind_and_keeps_native_evidence_coordinates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_root = root / "input"
            (input_root / "images").mkdir(parents=True)
            (input_root / "labels").mkdir(parents=True)
            (input_root / "images" / "sample.png").write_bytes(b"not-an-image-for-link-test")
            label = {
                "Images": {"identifier": "DOC-1", "width": 827, "height": 1170},
                "bbox": [
                    {"data": "INV-1", "x": [560, 560, 600, 600], "y": [150, 170, 170, 150]},
                ],
            }
            (input_root / "labels" / "sample.json").write_text(json.dumps(label), encoding="utf-8")
            manifest = {
                "stable_sample_id": "inv01-001-sample",
                "document_id": "DOC-1",
                "document_type": "Commercial Invoice",
                "split": "DEV",
                "source_group": "INV01",
                "source_path": "images/sample.png",
                "label_path": "labels/sample.json",
            }
            (input_root / "manifest.jsonl").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

            metrics = build(input_root, root / "output")
            self.assertTrue(metrics["prediction_blind"])
            self.assertEqual(metrics["documents"], 1)
            case = root / "output" / "cases" / "inv01-001-sample"
            self.assertTrue((case / "image.png").exists())
            self.assertTrue((case / "source_annotation.json").exists())
            fields = json.loads((case / "semantic_gold_fields.json").read_text(encoding="utf-8"))
            invoice_number = next(field for field in fields if field["field_name"] == "invoice_number")
            self.assertEqual(invoice_number["source_token_indices"], [0])
            self.assertAlmostEqual(invoice_number["bbox"][0][0], 560.0)
            self.assertNotIn("prediction", json.dumps(fields).lower())


if __name__ == "__main__":
    unittest.main()
