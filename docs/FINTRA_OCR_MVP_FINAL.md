# Fintra OCR MVP delivery state

## Scope

This branch delivers the evidence-first Fintra OCR/Extractor MVP boundary for
Commercial Invoice, Packing List, and B/L documents. The validated Paddle OCR
runtime remains the active local backend. The prior Modern runtime remains a
benchmark/reference and is not fused into the production adapter.

The development Gold is frozen as `MVP_DEVELOPMENT_GOLD_V4`. It is a reviewed
MVP benchmark, not a claim of exhaustive semantic annotation:

- Accurate75 Gold: `artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases`
- Fast300 Gold: `artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases`
- Gold sanity report: `artifacts/fintra/gold_audit/semantic-v4-image-accurate75/MVP_GOLD_SANITY_REPORT.json`

Unsupported field families remain `ambiguous_gt` and are excluded from the
available-field denominator by design.

## Frozen development metrics

The current accepted extractor is the clean-room engine under
`fintra/extraction/clean/`; the final freeze commit is recorded in git history.
These are separate development datasets:

| Set | Overall | CI | Packing List | B/L |
|---|---:|---:|---:|---:|
| Accurate75-1 | 467/653 = 71.52% | 250/320 = 78.12% | 180/263 = 68.44% | 37/70 = 52.86% |
| Fast300 | 1830/2409 = 75.96% | 946/1106 = 85.53% | 724/1010 = 71.68% | 160/293 = 54.61% |

The stage decomposition is recorded at
`artifacts/fintra/train-scale-v1/mvp-v4-iter2/stages/` and separates OCR
recoverability from extractor candidate/resolver losses. It uses frozen
Paddle JSON and prediction-blind Gold; it does not modify either artifact.

## Backend contract

The backend-facing entrypoint is:

```python
from fintra.ocr.paddle_backend import PaddleOCRBackend
from fintra.services.document_service import extract_document

payload = extract_document(
    document_path,
    "Commercial Invoice",  # or "Packing List" / "B/L"
    PaddleOCRBackend(device="gpu", mode="accurate"),
)
```

The command-line equivalent and local review UI are documented in
`docs/DOCUMENT_INTEGRATION.md`. The output is
`fintra-document-contract.v1`; every extracted value retains status,
source text, bbox, and confidence where available. `ocr.regions` exposes the
canonical OCR regions for evidence rendering.

## Verification

Run:

```powershell
python -m unittest discover -s tests -q
python scripts/evaluate_mvp_stages.py
```

The stage report intentionally does not access FINAL-HOLDOUT #2. DEV60 is
diagnostic-only for this freeze because its historical field contract differs
from semantic-v4. The separate holdout must be used only once after this
revision is frozen and the final evaluation command is explicitly run.
