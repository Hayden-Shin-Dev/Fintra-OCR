# Fintra OCR/Extractor MVP v1.1 freeze

This is the freeze point for the local backend handoff. It freezes the
interfaces and inputs used for development verification; it does not claim
that the available-field accuracy target has been reached.

| Component | Frozen reference |
|---|---|
| Git branch | `restart/clean-v2` |
| Extractor semantics | clean-room path in final freeze commit |
| Integration boundary | `fintra.services.document_service.extract_document` |
| Evaluator v4 support | `MVP_DEVELOPMENT_GOLD_V4` evaluator |
| Gold | `MVP_DEVELOPMENT_GOLD_V4` |
| Accurate Gold | `artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases` |
| Fast Gold | `artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases` |
| OCR backend | validated Paddle legacy reference, `PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec` |
| OCR policy | Paddle active backend; Modern remains benchmark/reference |
| CLI | `scripts/run_document_extraction.py` |
| Service | `fintra.services.document_service.extract_document` |
| UI | `app.py` |
| Contract | `fintra-document-contract.v1` |

Development metrics at freeze:

- Accurate75-1: 467/653 overall (71.52%), 250/320 CI, 180/263 PL,
  37/70 B/L.
- Fast300: 1830/2409 overall (75.96%), 946/1106 CI, 724/1010 PL,
  160/293 B/L.
- Stage decomposition: `artifacts/fintra/extractor-rebuild/regression/clean-stages-v11/`
- Unit suite: 102 tests passed.

The Accurate75-1 and Fast300 numbers are development-set measurements and
must not be interpreted as a causal comparison between datasets. DEV60 is
diagnostic-only because its historical contract differs. FINAL-HOLDOUT #2 is
a separate one-shot evaluation and is not used for tuning.

The freeze does not alter Azure data, Gold, OCR JSON, or model files.
