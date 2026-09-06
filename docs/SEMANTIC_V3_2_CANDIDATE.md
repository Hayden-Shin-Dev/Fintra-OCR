# semantic-v3.2 Accurate75 #1 candidate

`semantic-v3.2` is a separate, prediction-blind Gold candidate generated from
AI-Hub Training TL/source annotations. It does not replace semantic-v2,
semantic-v3, or semantic-v3.1.

## Candidate checks

- Cases: 75 (CI 25 / Packing List 25 / B/L 25)
- Changed Gold fields versus the prior Accurate75 #1 view: 160
- Validation: `0` invalid fields / `PASS`
- Final-Holdout #2 accessed: no

The candidate preserves the prior reviewed item cardinality; it does not add
discovered table rows merely to change the evaluation denominator.

## Frozen extractor re-evaluation

The existing active extractor was run without code changes against the
candidate Gold:

- Overall: 326 / 532 = 61.28%
- Commercial Invoice: 72 / 206 = 34.95%
- Packing List: 110 / 153 = 71.90%
- B/L: 144 / 173 = 83.24%

The prior view in the same 75-case evaluation was 362 / 518 = 69.88%. The
drop is not interpreted as an OCR regression: the corrected candidate exposes
additional applicable row/column mappings and therefore changes the benchmark
contract. Both views remain preserved for comparison.

## Artifacts

- `artifacts/fintra/gold_audit/training-tl-provenance/`
- `artifacts/fintra/gold_audit/training-tl-gold-integrity/`
- `artifacts/fintra/gold_audit/semantic-v3.2-accurate75/cases/`
- `artifacts/fintra/gold_audit/v3.1_to_v3.2_accurate75_diff.csv`
- `artifacts/fintra/gold_audit/semantic-v3.2-accurate75/v3_2_validation_metrics.json`
- `artifacts/fintra/gold_audit/semantic-v3.2-accurate75-evaluation/`
