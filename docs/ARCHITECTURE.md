# Fintra MVP architecture boundary

## Owned by this workstream

`fintra/ocr` consumes the validated Modern OCR output without changing model
weights, preprocessing, decoding, or thresholds. `fintra/extraction` converts
OCR regions into evidence-bearing fields for Commercial Invoice, Packing List,
and B/L. `fintra/normalization` provides conservative comparisons, and
`fintra/validation` produces deterministic cross-document findings.

`fintra/services/review_service.py` is the integration boundary. It combines
the ledger, available documents, extracted fields, and validation findings into
`TransactionReview` and `fintra-review-contract.v1`.

## Not owned here

Frontend/UI, persistence infrastructure, RAG retrieval, embedding indexes, and
LLM provider integration belong to other workstreams. This repository provides
their structured input contract but does not silently replace their
implementation.

## Evidence flow

```text
Modern OCR output
        |
        v
OCRResult (raw output + regions)
        |
        v
document extractor -> EvidenceField(source_text, bbox, status)
        |
        v
normalization -> deterministic validation findings
        |
        v
TransactionReview -> downstream integration contract
```
