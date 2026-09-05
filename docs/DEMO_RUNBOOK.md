# Service-layer demo runbook

1. Construct a `LedgerTransaction` from the backend team's transaction input.
2. Use `FixtureOCRAdapter` for a test fixture or an explicitly configured
   `CommandOCRAdapter` for the validated Modern OCR runtime.
3. Pass the resulting `OCRResult` values to `build_review`.
4. Serialize `review_contract(review)` as the service response or handoff
   payload.
5. Preserve `review.validation_results` and `review.evidence_summary` when a
   downstream UI, retriever, or assistant consumes the payload.

Example import:

```python
from fintra.services import build_review, review_contract
review = build_review(ledger_transaction, ocr_results)
payload = review_contract(review)
```

The function does not invoke a GPU, API credential, retriever, or LLM.
