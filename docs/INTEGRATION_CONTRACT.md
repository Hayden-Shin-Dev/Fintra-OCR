# Fintra-owned integration contract

This document defines the boundary delivered by the Fintra OCR/validation
workstream. It does not implement the frontend, retrieval system, or LLM.

## Input

`build_review(transaction, ocr_results)` accepts one `LedgerTransaction` and
zero or more `OCRResult` values. Each OCR result must identify one of:

- `Commercial Invoice`
- `Packing List`
- `B/L`

The adapter preserves the raw OCR output path/content and each region's text,
polygon, confidence, and page. Extracted values retain `source_text` and
`bbox` evidence. Missing values are `missing`; multiple candidates are
`ambiguous`.

## Output

`review_contract(review)` returns:

- `schema_version`: `fintra-review-contract.v1`
- `review`: canonical `TransactionReview` JSON
- `rag_context`: deterministic findings and evidence for a teammate's retriever
- `llm_payload`: structured transaction/documents/findings/references input for
  a teammate's evidence-only assistant

The contract does not authorize downstream components to modify
`overall_review_status`. Valid status values are `PASS`, `REVIEW_REQUIRED`,
`MISMATCH`, and `INCOMPLETE`.

## Status semantics

`MISMATCH` takes precedence over `REVIEW_REQUIRED`; `REVIEW_REQUIRED` takes
precedence over `INCOMPLETE`. Missing documents, missing fields, and
unparseable values are never silently treated as a match.

## Downstream constraints

The RAG/LLM team may append retrieved references or an explanatory response,
but must preserve the deterministic findings and evidence. No component may
claim fraud, change accounting treatment, or automatically alter ledger data.
