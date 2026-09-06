# MVP_DEVELOPMENT_GOLD_V4

This is the frozen, prediction-blind development Gold for OCR/extractor
development. It is intentionally not semantic-complete: unsupported field
families remain `ambiguous_gt` and are excluded from the available-field
benchmark denominator.

- Accurate75 cases: `artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases`
- Fast300 cases: `artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases`
- Accurate75 image/TL audit: `artifacts/fintra/gold_audit/semantic-evidence-v4-image-accurate75/semantic_evidence_metrics.json`
- Fast300 image/TL audit: `artifacts/fintra/gold_audit/semantic-evidence-v4-image-balanced300/semantic_evidence_metrics.json`
- Sanity report: `artifacts/fintra/gold_audit/semantic-v4-image-accurate75/MVP_GOLD_SANITY_REPORT.json`

The generator reads original Training TL tokens and the original document
image layout only. OCR and extractor outputs are not inputs to Gold creation
or audit. `FINAL-HOLDOUT #2` is outside this scope.
