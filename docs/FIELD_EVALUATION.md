# Fintra field extraction evaluation

## Scope

The evaluation uses the actual AI-Hub Validation source and label ZIP pairs downloaded from Azure. It selects four documents from each of the five `INV`, `PL`, and `BL` ZIP pairs: 20 Commercial Invoices, 20 Packing Lists, and 20 B/L documents (60 documents total). No `sample.zip`, prior OCR output, or alternate OCR model is used.

The selected images and labels are prepared by:

```powershell
python .\scripts\prepare_field_eval_cases.py `
  --zip-root .\artifacts\fintra\field_eval\source_zips `
  --output-root .\artifacts\fintra\field_eval
```

The source ZIPs contain word-level OCR annotations rather than semantic field labels. Two gold tracks are preserved:

- `legacy`: the original fixed-zone gold used for the frozen baseline and audit. It contains known semantic mapping defects and must not be presented as validated field accuracy.
- `semantic-v2`: a reproducible relative-zone/type-constrained projection from the AI-Hub word annotations. It is independent of recognition predictions, but still requires human visual sign-off before being treated as a production accuracy claim.

Build the independent track with:

```powershell
python .\scripts\build_semantic_field_gold.py `
  --cases .\artifacts\fintra\field_eval\cases
```

Then evaluate it with the already-generated recognition JSONs (no GPU rerun):

```powershell
python .\scripts\evaluate_field_extraction.py `
  --cases .\artifacts\fintra\field_eval\cases `
  --output-dir .\artifacts\fintra\field_eval `
  --strategy active `
  --gold-source semantic-v2
```

A field is `ambiguous_gt` when the source annotations do not establish one typed value; a field absent from the inspected template is `not_applicable`. Neither category enters the accuracy denominator. Recognition spelling errors are not repaired by normalization.

## GPU execution

The runner invokes the already-built Modern Detection and Modern Recognition images. It does not build images, change OCR checkpoints, change OCR source, or run on `sample.zip`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\RUN_FIELD_EVAL_GPU.ps1
```

This is a GPU command and must be run by the operator. It writes one detection JSON and one raw/structured recognition output under each case directory, then invokes the host evaluator.

## Outputs

After all 60 cases finish:

- `artifacts/fintra/field_eval/field_results.csv`
- `artifacts/fintra/field_eval/field_metrics.json`
- `artifacts/fintra/field_eval/FIELD_EXTRACTION_EVALUATION.md`

The current canonical report uses `gold_source=semantic-v2`, 60 existing AI-Hub
Validation recognition outputs, and a fixed available-gold denominator. The
latest run is `FIELD_EXTRACTION_STATUS=NEEDS_IMPROVEMENT`; its normalized field
accuracy is approximately 30.73% overall (CI 41.46%, Packing List 34.33%, B/L
18.95%). These numbers are not an official OCR score: the source OCR itself
contains unrecoverable character errors and the semantic projection awaits
visual sign-off.

The field evaluator reports exact matches, normalized matches, wrong, missing, ambiguous, and not-applicable states. Normalization is representation-only: company case/punctuation/whitespace, ISO dates, Decimal numbers, known currency codes, and unit case. It does not convert semantically different units or infer missing values.

The frozen legacy audit is under `artifacts/fintra/field_eval/error_analysis.*`.
It audited all 492 available legacy rows and measured an operational token
evidence-present rate of about 45.12%. This is an OCR/evidence ceiling signal,
not a mathematical proof; it explains why a 90% extractor target cannot be
claimed from the current outputs without a new OCR run or human-corrected gold.

## Validation engine fixture evaluation

The deterministic cross-document rules can be evaluated without GPU/OCR:

```powershell
python .\scripts\evaluate_validation_engine.py `
  --output-dir .\artifacts\fintra\validation_eval
```

This produces `validation_results.csv`, `validation_metrics.json`, and `VALIDATION_EVALUATION.md` for explicit match, mismatch, ambiguous, and insufficient-evidence fixtures. It is a rule-engine regression evaluation, not a claim about production transaction coverage.
