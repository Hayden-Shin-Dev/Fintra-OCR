# Fintra OCR/Extractor MVP v1.1 freeze

This is the freeze point for the local backend handoff. It freezes the
interfaces and inputs used for development verification; it does not claim
that the available-field accuracy target has been reached.

| Component | Frozen reference |
|---|---|
| Git branch | `restart/clean-v2` |
| Extractor semantics | `4f9487f` |
| Integration boundary | `2581717` |
| Evaluator v4 support | `f54b0bb` |
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

- Accurate75-1: 377/653 overall (57.73%), 152/320 CI, 178/263 PL,
  47/70 B/L.
- Fast300: 1687/2409 overall (70.03%), 864/1106 CI, 656/1010 PL,
  167/293 B/L.
- Stage decomposition: `artifacts/fintra/train-scale-v1/mvp-v4-iter2/stages/`
- Unit suite before final report: 84 tests passed.

The Accurate75-1 and Fast300 numbers are development-set measurements and
must not be compared as a causal improvement claim. FINAL-HOLDOUT #2 is a
separate one-shot evaluation and is not used for tuning.

The freeze does not alter Azure data, Gold, OCR JSON, or model files.
