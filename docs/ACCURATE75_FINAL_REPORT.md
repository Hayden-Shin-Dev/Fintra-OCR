# Accurate balanced75 frozen holdout

This report uses only the 75 IDs in
`artifacts/fintra/train-scale-v1/parallel/accurate-balanced75.txt`.
The selected set is exactly CI 25, Packing List 25, and B/L 25. The extra
case in the holdout output directory was not evaluated.

## Frozen extractor result

| Scope | Correct | Applicable | Normalized accuracy |
|---|---:|---:|---:|
| Overall | 333 | 518 | 64.29% |
| Primary overall | 156 | 205 | 76.10% |
| Commercial Invoice | 93 | 181 | 51.38% |
| Commercial Invoice primary | 50 | 74 | 67.57% |
| Packing List | 108 | 154 | 70.13% |
| Packing List primary | 57 | 69 | 82.61% |
| B/L | 132 | 183 | 72.13% |
| B/L primary | 49 | 62 | 79.03% |

Complete field-level metrics are in the holdout `field_metrics.json`.

## Failure classification

Recoverable-but-wrong count: 134. The diagnostic cause split is stored in
`recoverable_error_causes.csv` and `error_cause_metrics.json`.

The conservative three-way failure matrices are stored under `*-failure-analysis`:

- `OCR_MISSING`: required evidence is not recoverable from Accurate OCR.
- `GOLD_AMBIGUOUS_OR_MISMATCH`: the frozen semantic mapping is a reference or
  country-only value, or otherwise structurally ambiguous under the diagnostic
  rule. It is not removed from the denominator.
- `EXTRACTOR_WRONG`: the frozen OCR contains recoverable gold evidence and the
  extractor did not return the correct normalized value.

Accurate holdout errors were not used to change the extractor, Gold, or OCR.

## Fast comparison

| Dataset | Overall | Primary | CI | PL | B/L |
|---|---:|---:|---:|---:|---:|
| Fast balanced300 | 1673/2339 (71.53%) | 829/941 (88.10%) | 688/1023 (67.25%) | 467/595 (78.49%) | 518/721 (71.84%) |
| Accurate balanced75 | 333/518 (64.29%) | 156/205 (76.10%) | 93/181 (51.38%) | 108/154 (70.13%) | 132/183 (72.13%) |

These are different subsets and are not a causal improvement/regression
comparison.

## Provenance

- Extractor freeze: `d23a7cb`
- Evaluation output: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-holdout/evaluation-frozen-d23a7cb`
- Accurate OCR output: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-holdout/cases`
- Gold: frozen semantic-v3.1
- External `paddle-ocr-accurate-holdout` was not terminated or used for tuning.
