import unittest

from fintra.extraction.production import EXTRACTORS, FieldCandidate, candidates_for
from fintra.extraction.clean.engine import EXTRACTORS as CLEAN_EXTRACTORS
from fintra.extraction.strategies import STRATEGIES
from fintra.ocr.adapter import OCRRegion, OCRResult
from scripts.audit_production_extractor import audit


def _result(kind="Commercial Invoice"):
    regions = [
        OCRRegion([[100, 100], [250, 100], [250, 120], [100, 120]], "SELLER", 0.99, 1, 0),
        OCRRegion([[100, 130], [300, 130], [300, 150], [100, 150]], "ACME INDUSTRIES", 0.99, 1, 1),
    ]
    return OCRResult("fixture", kind, "fixture.png", regions, metadata={"page_width": 1000, "page_height": 1000})


class ProductionExtractorTests(unittest.TestCase):
    def test_legacy_dispatch_remains_comparison_only_until_clean_gate(self):
        self.assertEqual(set(EXTRACTORS), set(STRATEGIES))
        self.assertTrue(all(fn.__module__ == "fintra.extraction.production" for fn in EXTRACTORS.values()))
        self.assertTrue(all(fn.__module__ == "fintra.extraction.clean.engine" for fn in CLEAN_EXTRACTORS.values()))

    def test_candidate_view_preserves_normalized_geometry(self):
        document = EXTRACTORS["Commercial Invoice"](_result("Commercial Invoice"))
        candidates = candidates_for(document, _result("Commercial Invoice"))
        self.assertTrue(all(isinstance(item, FieldCandidate) for item in candidates))
        seller = next((item for item in candidates if item.field_name == "seller"), None)
        self.assertIsNotNone(seller)
        self.assertEqual(seller.normalized_geometry, (0.1, 0.13, 0.3, 0.15))

    def test_static_audit_passes(self):
        result = audit()
        self.assertTrue(result["clean_passed"])
        self.assertFalse(result["active_dispatch_clean"])
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
