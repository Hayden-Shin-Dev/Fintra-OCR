# Fast balanced300 extractor freeze

This is the final fast-scale extractor report for the frozen Paddle OCR cache
and frozen semantic-v3.1 gold. No OCR output, cache, or gold was changed.

## Frozen result

| Scope | Correct | Applicable | Normalized accuracy |
|---|---:|---:|---:|
| Overall | 1673 | 2339 | 71.53% |
| Primary overall | 829 | 941 | 88.10% |
| Commercial Invoice | 688 | 1023 | 67.25% |
| Commercial Invoice primary | 332 | 402 | 82.59% |
| Packing List | 467 | 595 | 78.49% |
| Packing List primary | 276 | 297 | 92.93% |
| B/L | 518 | 721 | 71.84% |
| B/L primary | 221 | 242 | 91.32% |

The complete field-level `correct`, `applicable`, `accuracy`, `wrong`, and
`missing` values are in the frozen `field_metrics.json`. Recoverable OCR
evidence selected but not correctly extracted is in
`recoverable_but_wrong.csv`.

## Failure analysis

The scale failure matrices are stored separately for Packing List,
Commercial Invoice, and B/L. They classify failures as
`EXTRACTOR_WRONG`, `OCR_MISSING`, or `GOLD_AMBIGUOUS_OR_MISMATCH` using only
the frozen OCR output and semantic-v3.1 gold. They do not modify either input.

## Freeze decision

The last accepted extractor change is commit `d23a7cb`:
header-relative Packing List unit selection and invoice-date selection. It
passed 69 full tests before the integration artifact was added; the final
repository test count is 71 PASS. CI and B/L balanced300 scores did not
regress, and DEV-60 improved from `372/475` to `375/475`.

The external `paddle-ocr-accurate-holdout` remains an unseen validation set
and was not stopped, read for tuning, or included in this report.

## Backend integration

`fintra.services.document_service.extract_document` and
`scripts/run_document_extraction.py` implement
`fintra-document-contract.v1`: a document file plus an explicitly configured
OCR adapter produces canonical evidence-bearing JSON without backend changes
to internal OCR or extractor code. See `docs/DOCUMENT_INTEGRATION.md`.
