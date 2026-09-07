import unittest

from fintra.extraction.production import EXTRACTORS, FieldCandidate
from fintra.extraction.clean.engine import EXTRACTORS as CLEAN_EXTRACTORS
from fintra.ocr.adapter import OCRRegion, OCRResult
from scripts.audit_production_extractor import audit


def _result(kind="Commercial Invoice"):
    regions = [
        OCRRegion([[100, 100], [250, 100], [250, 120], [100, 120]], "SELLER", 0.99, 1, 0),
        OCRRegion([[100, 130], [300, 130], [300, 150], [100, 150]], "ACME INDUSTRIES", 0.99, 1, 1),
    ]
    return OCRResult("fixture", kind, "fixture.png", regions, metadata={"page_width": 1000, "page_height": 1000})


class ProductionExtractorTests(unittest.TestCase):
    def test_production_dispatch_is_clean_engine(self):
        self.assertEqual(set(EXTRACTORS), set(CLEAN_EXTRACTORS))
        self.assertTrue(all(fn.__module__ == "fintra.extraction.clean.engine" for fn in EXTRACTORS.values()))

    def test_clean_output_preserves_evidence(self):
        document = EXTRACTORS["Commercial Invoice"](_result("Commercial Invoice"))
        self.assertEqual(document.seller.value, "ACME INDUSTRIES")
        self.assertIsNotNone(document.seller.bbox)

    def test_static_audit_passes_with_clean_dispatch(self):
        result = audit()
        self.assertTrue(result["clean_passed"])
        self.assertTrue(result["active_dispatch_clean"])
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
