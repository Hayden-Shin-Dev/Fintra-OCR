import unittest
from decimal import Decimal

from fintra.domain.schema import CommercialInvoice, DocumentMetadata, LedgerTransaction, evidence
from fintra.normalization.values import compare_values, normalize_date, normalize_weight, parse_amount
from fintra.validation.engine import validate_transaction


class NormalizationTests(unittest.TestCase):
    def test_amount_and_weight_are_conservative(self):
        self.assertEqual(parse_amount("USD 1,234.50"), Decimal("1234.50"))
        self.assertEqual(normalize_weight("1,000", "g"), (Decimal("1"), "KG"))
        self.assertIsNone(normalize_date("01/02/2024"))

    def test_compare_amount_tolerance(self):
        self.assertEqual(compare_values("10.00", "10.009", kind="amount")[0], "match")
        self.assertEqual(compare_values("10.00", "11.00", kind="amount")[0], "mismatch")


class ValidationTests(unittest.TestCase):
    def test_ledger_invoice_match_is_deterministic(self):
        ledger = LedgerTransaction("tx-1", amount=evidence("100.00"), counterparty=evidence("Buyer Co"))
        invoice = CommercialInvoice(
            DocumentMetadata("ci-1", "Commercial Invoice"),
            buyer=evidence("Buyer Co"), total_amount=evidence("100.00"),
        )
        findings = validate_transaction(ledger, invoice, None, None)
        self.assertEqual(findings[0].status.value, "match")
        self.assertEqual(findings[1].status.value, "match")

    def test_missing_data_is_not_called_a_match(self):
        findings = validate_transaction(LedgerTransaction("tx-1"), CommercialInvoice(DocumentMetadata("ci-1", "Commercial Invoice")), None, None)
        self.assertTrue(all(item.status.value == "insufficient_evidence" for item in findings))


if __name__ == "__main__":
    unittest.main()
