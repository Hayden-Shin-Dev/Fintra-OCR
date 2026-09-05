"""Integration service for the Fintra-owned OCR and validation boundary."""

from __future__ import annotations

from typing import Iterable

from fintra.domain.schema import (
    BillOfLading,
    CommercialInvoice,
    DocumentMetadata,
    ExtractionStatus,
    LedgerTransaction,
    PackingList,
    TransactionReview,
    ValidationStatus,
)
from fintra.extraction.documents import EXTRACTORS
from fintra.ocr.adapter import OCRResult
from fintra.validation.engine import validate_transaction


def _extract(result: OCRResult) -> object:
    extractor = EXTRACTORS.get(result.document_type)
    if extractor is None:
        raise ValueError(f"unsupported document type: {result.document_type}")
    return extractor(result)


def _overall_status(review: TransactionReview) -> str:
    statuses = {finding.status for finding in review.validation_results}
    if ValidationStatus.MISMATCH in statuses:
        return "MISMATCH"
    if ValidationStatus.REVIEW_REQUIRED in statuses:
        return "REVIEW_REQUIRED"
    if ValidationStatus.INSUFFICIENT_EVIDENCE in statuses:
        return "INCOMPLETE"
    required_docs = (review.commercial_invoice, review.packing_list, review.bill_of_lading)
    if any(document is None for document in required_docs):
        return "INCOMPLETE"
    return "PASS"


def build_review(transaction: LedgerTransaction, ocr_results: Iterable[OCRResult]) -> TransactionReview:
    """Extract available documents and validate only comparable evidence."""

    extracted: dict[str, object] = {}
    for result in ocr_results:
        if result.document_type in extracted:
            raise ValueError(f"duplicate document type: {result.document_type}")
        extracted[result.document_type] = _extract(result)
    invoice = extracted.get("Commercial Invoice")
    packing = extracted.get("Packing List")
    bill = extracted.get("B/L")
    if invoice is not None and not isinstance(invoice, CommercialInvoice):
        raise TypeError("invoice extractor returned an unexpected object")
    if packing is not None and not isinstance(packing, PackingList):
        raise TypeError("packing extractor returned an unexpected object")
    if bill is not None and not isinstance(bill, BillOfLading):
        raise TypeError("B/L extractor returned an unexpected object")
    findings = validate_transaction(transaction, invoice, packing, bill)
    summary = [
        f"{finding.rule_id}: {finding.status.value}"
        for finding in findings
    ]
    review = TransactionReview(
        ledger_transaction=transaction,
        commercial_invoice=invoice,
        packing_list=packing,
        bill_of_lading=bill,
        validation_results=findings,
        overall_review_status="INCOMPLETE",
        evidence_summary=summary,
    )
    return TransactionReview(
        ledger_transaction=review.ledger_transaction,
        commercial_invoice=review.commercial_invoice,
        packing_list=review.packing_list,
        bill_of_lading=review.bill_of_lading,
        validation_results=review.validation_results,
        overall_review_status=_overall_status(review),
        evidence_summary=review.evidence_summary,
    )


def review_contract(review: TransactionReview) -> dict:
    """Return the stable boundary payload for API/UI/RAG/LLM teammates.

    This function does not call an LLM or a retriever. It only emits their
    documented inputs and the deterministic review object.
    """

    review_payload = review.to_dict()
    findings = [finding.to_dict() for finding in review.validation_results]
    evidence = [item for finding in findings for item in finding.get("evidence", [])]
    return {
        "schema_version": "fintra-review-contract.v1",
        "review": review_payload,
        "rag_context": {
            "transaction_id": review.ledger_transaction.transaction_id,
            "review_status": review.overall_review_status,
            "validation_findings": findings,
            "evidence": evidence,
            "retrieval_query": " ".join(
                str(item.get("message", "")) for item in findings if item.get("message")
            ),
        },
        "llm_payload": {
            "transaction": review.ledger_transaction.to_dict(),
            "documents": {
                key: value for key, value in {
                    "commercial_invoice": review.commercial_invoice.to_dict() if review.commercial_invoice else None,
                    "packing_list": review.packing_list.to_dict() if review.packing_list else None,
                    "bill_of_lading": review.bill_of_lading.to_dict() if review.bill_of_lading else None,
                }.items() if value is not None
            },
            "deterministic_findings": findings,
            "accounting_references": review.accounting_references,
            "constraints": [
                "Use only supplied evidence and references.",
                "Do not change deterministic review status.",
                "Do not claim fraud or definitive accounting treatment.",
            ],
        },
    }
