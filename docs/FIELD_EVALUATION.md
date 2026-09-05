# Fintra field extraction evaluation

## Scope

The evaluation uses the actual AI-Hub Validation source and label ZIP pairs downloaded from Azure. It selects four documents from each of the five `INV`, `PL`, and `BL` ZIP pairs: 20 Commercial Invoices, 20 Packing Lists, and 20 B/L documents (60 documents total). No `sample.zip`, prior OCR output, or alternate OCR model is used.

The selected images and labels are prepared by:

```powershell
python .\scripts\prepare_field_eval_cases.py `
  --zip-root .\artifacts\fintra\field_eval\source_zips `
  --output-root .\artifacts\fintra\field_eval
```

The source ZIPs contain word-level OCR annotations rather than semantic field labels. Gold fields therefore use only annotation text and coordinates inside template zones inspected from the actual documents. A field is `ambiguous_gt` when the document does not establish one unambiguous value; a field absent from the inspected template is `not_applicable`. Neither category enters the accuracy denominator.

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

The field evaluator reports exact matches, normalized matches, wrong, missing, ambiguous, and not-applicable states. Normalization is representation-only: company case/punctuation/whitespace, ISO dates, Decimal numbers, known currency codes, and unit case. It does not convert semantically different units or infer missing values.

## Validation engine fixture evaluation

The deterministic cross-document rules can be evaluated without GPU/OCR:

```powershell
python .\scripts\evaluate_validation_engine.py `
  --output-dir .\artifacts\fintra\validation_eval
```

This produces `validation_results.csv`, `validation_metrics.json`, and `VALIDATION_EVALUATION.md` for explicit match, mismatch, ambiguous, and insufficient-evidence fixtures. It is a rule-engine regression evaluation, not a claim about production transaction coverage.
