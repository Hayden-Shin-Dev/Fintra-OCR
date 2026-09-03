import unittest

from fintra_ocr.field_evidence import make_field_evidence, missing_field
from fintra_ocr.hybrid_pipeline import HybridPolicy, arbitrate_field, run_hybrid_document
from fintra_ocr.prediction_parser import OCRPrediction


def prediction(text: str, left: int, top: int, right: int, bottom: int, score: float):
    return OCRPrediction(
        text,
        (left, right, right, left),
        (top, top, bottom, bottom),
        score,
    )


class FakeBackend:
    def __init__(self, name, predictions):
        self.name = name
        self.predictions = predictions

    def predict_bytes(self, image_bytes):
        return list(self.predictions)


class HybridPipelineTest(unittest.TestCase):
    def evidence(self, value: str, score: float, index: int = 0):
        return make_field_evidence(
            "invoice_no",
            [prediction(value, 10 + index, 10, 40 + index, 25, score)],
            (0,),
            value,
        )

    def test_high_confidence_fallback_fills_missing_primary(self):
        primary = missing_field("invoice_no", "no primary candidate")
        fallback = self.evidence("INV-2", 0.95)
        selected = arbitrate_field(primary, fallback)
        self.assertEqual(selected.status, "found")
        self.assertEqual(selected.value, "INV-2")

    def test_weak_conflict_is_ambiguous(self):
        selected = arbitrate_field(self.evidence("INV-A", 0.93), self.evidence("INV-B", 0.94))
        self.assertEqual(selected.status, "ambiguous")

    def test_clear_fallback_conflict_wins(self):
        selected = arbitrate_field(self.evidence("INV-A", 0.70), self.evidence("INV-B", 0.96))
        self.assertEqual(selected.status, "found")
        self.assertEqual(selected.value, "INV-B")

    def test_same_value_keeps_higher_confidence_evidence(self):
        selected = arbitrate_field(self.evidence("INV-A", 0.70), self.evidence("INV-A", 0.96))
        self.assertEqual(selected.status, "found")
        self.assertEqual(selected.confidence, 0.96)

    def test_hybrid_runner_rebases_fallback_source_indices(self):
        primary = FakeBackend("primary", [prediction("noise", 0, 0, 20, 20, 0.5)])
        fallback = FakeBackend(
            "fallback",
            [
                prediction("Invoice No", 30, 30, 100, 50, 0.95),
                prediction("INV-2", 30, 55, 100, 75, 0.95),
            ],
        )
        result = run_hybrid_document(
            b"image",
            "\uc0c1\uc5c5\uc1a1\uc7a5",
            "doc-1",
            primary,
            fallback,
            policy=HybridPolicy(),
        )
        self.assertEqual(result.document["document_id"], "doc-1")
        self.assertEqual(result.document["fields"]["invoice_no"]["value"], "INV-2")
        self.assertEqual(result.fields["invoice_no"].source_indices, (2,))
        self.assertEqual(len(result.predictions), 3)


if __name__ == "__main__":
    unittest.main()
