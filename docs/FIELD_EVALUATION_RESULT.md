# Fintra field extraction result

This is the result of the 60-case run using the existing Modern OCR JSONs:
20 Commercial Invoice, 20 Packing List, and 20 B/L cases from actual AI-Hub
Validation data. No OCR model, checkpoint, preprocessing, or GPU inference
was changed or rerun during field-extractor iterations.

## Final status

`FIELD_EXTRACTION_STATUS=NEEDS_IMPROVEMENT`

The requested 90% target was not reached and must not be claimed.

| Metric | Overall | Commercial Invoice | Packing List | B/L |
|---|---:|---:|---:|---:|
| Normalized field accuracy | 31.71% | 41.46% | 34.33% | 21.57% |
| Wrong extraction rate | 60.00% | 56.10% | 48.51% | 73.20% |
| Missing rate | 7.56% | 0.81% | 17.16% | 4.58% |
| Predicted ambiguous rate | 0.73% | 1.63% | 0.00% | 0.65% |

Denominator: 410 available semantic-v2 gold fields. Gold exclusions: 383
`ambiguous_gt`, 20 `not_applicable`. The original 492-field legacy audit is
kept separately and is not mixed into this denominator.

## Main error findings

The frozen audit of all 492 legacy available rows found:

- 45.12% operational OCR evidence-present rate
- 54.88% OCR-limited rows
- 9.96% extraction-error estimate among all rows
- 241 `OCR_TEXT_ERROR`, 26 `TABLE_ROW_ERROR`, 12 `MULTILINE_BLOCK_ERROR`, 9 `OCR_REGION_MISSING`
- 182 rows with gold-review flags

This evidence rate is an operational ceiling signal, not a mathematical proof.
It does establish that extractor-only changes cannot honestly support a 90%
claim from the current OCR outputs. Several legacy gold mappings were also
incorrect; for example, `bl-002` mapped its shipment date to `bl_number`.

## Weakest fields and priority

1. B/L shipper and goods description: verify B/L layout variants and obtain visually reviewed field gold; current recognition has substantial character and region errors.
2. Commercial Invoice and Packing List party fields: verify party-block boundaries and review OCR spelling damage; normalization must not silently correct names.
3. Packing List table row alignment and missing quantities: add layout-variant tests and retain numeric-only row anchors.
4. B/L port/vessel/date variants: add per-template structural adapters only after independent visual gold review.
5. Keep validation engine rules separate: its deterministic fixture evaluation is 25/25, but that is not a production transaction-coverage score.

## Validation engine

`VALIDATION_STATUS=PASS` for the explicit 25-scenario fixture suite:

- rule accuracy: 100%
- match precision: 100%
- mismatch precision: 100%
- review-required correctness: 100%
- insufficient-evidence correctness: 100%

## Artifacts

- `artifacts/fintra/field_eval/field_results.csv`
- `artifacts/fintra/field_eval/field_metrics.json`
- `artifacts/fintra/field_eval/FIELD_EXTRACTION_EVALUATION.md`
- `artifacts/fintra/field_eval/error_analysis.csv`
- `artifacts/fintra/field_eval/error_analysis.json`
- `artifacts/fintra/validation_eval/validation_results.csv`
- `artifacts/fintra/validation_eval/validation_metrics.json`
