# Fintra-owned data flow

1. A caller supplies a document path and obtains an `OCRResult` from an
   explicit OCR adapter.
2. The document type selects exactly one deterministic extractor.
3. Every extracted field retains its OCR source text and polygon when present.
4. Missing evidence is represented as `missing`; ambiguous candidates are
   represented as `ambiguous`.
5. Normalization is applied only while comparing values. It does not overwrite
   the original OCR text.
6. Cross-document and ledger comparisons produce `ValidationFinding` records.
7. `build_review` returns a `TransactionReview`; `review_contract` exposes the
   stable payload for other teams.

No raw OCR file, AI-Hub artifact, checkpoint, or secret is committed by this
application layer.
