import unittest

from fintra.domain.schema import LedgerTransaction, evidence
from fintra.ocr.adapter import OCRRegion, OCRResult
from fintra.services.review_service import build_review, review_contract


def _result(document_id, document_type, lines):
    return OCRResult(
        document_id=document_id,
        document_type=document_type,
        source_file=f"{document_id}.png",
        regions=[
            OCRRegion([[0, i * 30], [200, i * 30], [200, i * 30 + 20], [0, i * 30 + 20]], text, index=i)
            for i, text in enumerate(lines)
        ],
    )


class ReviewServiceTests(unittest.TestCase):
    def test_contract_keeps_deterministic_status_and_downstream_payloads(self):
        review = build_review(
            LedgerTransaction("tx-1", amount=evidence("100.00"), counterparty=evidence("Buyer Co")),
            [_result("ci-1", "Commercial Invoice", ["Invoice No: INV-1", "Buyer: Buyer Co", "Total: USD 100.00"])],
        )
        self.assertEqual(review.overall_review_status, "INCOMPLETE")
        contract = review_contract(review)
        self.assertEqual(contract["schema_version"], "fintra-review-contract.v1")
        self.assertEqual(contract["review"]["overall_review_status"], "INCOMPLETE")
        self.assertIn("deterministic_findings", contract["llm_payload"])
        self.assertIn("validation_findings", contract["rag_context"])

    def test_three_document_fixture_produces_pass_or_explicit_findings(self):
        results = [
            _result("ci-1", "Commercial Invoice", [
                "Invoice No: INV-1", "Seller: Seller Co", "Buyer: Buyer Co", "Total: USD 100.00",
                "ITEM: Widget | 2 EA | 50.00 | 100.00",
            ]),
            _result("pl-1", "Packing List", [
                "Packing List No: PL-1", "Exporter: Seller Co", "Consignee: Buyer Co",
                "Gross Weight: 10", "Weight Unit: KG", "Package Count: 1",
                "ITEM: Widget | 2 EA",
            ]),
            _result("bl-1", "B/L", [
                "B/L No: BL-1", "Shipper: Seller Co", "Consignee: Buyer Co",
                "Gross Weight: 10", "Weight Unit: KG", "Package Count: 1",
            ]),
        ]
        review = build_review(
            LedgerTransaction("tx-1", amount=evidence("100"), counterparty=evidence("Buyer Co")),
            results,
        )
        self.assertEqual(review.overall_review_status, "REVIEW_REQUIRED")
        self.assertGreaterEqual(len(review.validation_results), 5)
        self.assertTrue(all(finding.evidence for finding in review.validation_results if finding.status.value == "match"))

    def test_duplicate_document_type_is_rejected(self):
        item = _result("ci-1", "Commercial Invoice", ["Total: 1"])
        with self.assertRaises(ValueError):
            build_review(LedgerTransaction("tx-1"), [item, item])


if __name__ == "__main__":
    unittest.main()
