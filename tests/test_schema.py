import unittest

from fintra.domain.schema import (
    CommercialInvoice,
    DocumentMetadata,
    EvidenceField,
    ExtractionStatus,
    TransactionReview,
    evidence,
)


class SchemaTests(unittest.TestCase):
    def test_extracted_evidence_requires_a_value(self):
        with self.assertRaises(ValueError):
            EvidenceField(status=ExtractionStatus.EXTRACTED)

    def test_document_and_nested_fields_are_jsonable(self):
        document = CommercialInvoice(
            metadata=DocumentMetadata("doc-1", "Commercial Invoice"),
            invoice_number=evidence("INV-1", source_text="Invoice No: INV-1"),
        )
        payload = document.to_dict()
        self.assertEqual(payload["metadata"]["document_id"], "doc-1")
        self.assertEqual(payload["invoice_number"]["status"], "extracted")
        self.assertEqual(payload["invoice_number"]["source_text"], "Invoice No: INV-1")

    def test_transaction_review_defaults_to_incomplete(self):
        review = TransactionReview(
            ledger_transaction=__import__("fintra.domain.schema", fromlist=["LedgerTransaction"]).LedgerTransaction("tx-1")
        )
        self.assertEqual(review.overall_review_status, "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
