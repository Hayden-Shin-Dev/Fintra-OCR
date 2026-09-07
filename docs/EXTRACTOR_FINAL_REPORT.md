# Fintra OCR/Extractor rebuild final report

This report closes the development rebuild only. The sealed external final
holdout process was not terminated, inspected, or used for tuning.

## Production handoff

- Branch: `restart/clean-v2`
- Production callable: `fintra.services.document_service.extract_document`
- CLI: `scripts/run_document_extraction.py`
- Output: evidence-bearing `fintra-document-contract.v1` JSON
- UI integration: `app.py` → the same service boundary

The historical `documents.py`, `refinement.py`, and `table.py` remain in the
repository for comparison. They were removed from the production import path,
not deleted, so historical probes remain reproducible.

## Before → after

The clean boundary was accepted only after parity with the active implementation:

- Accurate75 #1: 377/653 (57.73%) → 377/653 (57.73%)
- Fast300: 1687/2409 (70.03%) → 1687/2409 (70.03%)
- DEV60: 183/492 (37.20%) → 183/492 (37.20%)

There is no claimed accuracy improvement from the boundary refactor. The
improvement is isolation, evidence preservation, and backend usability.

## OCR and extractor recovery

- Paddle raw field recoverability: Accurate75 570/653 (87.29%), Fast300
  2096/2409 (87.01%), DEV60 239/492 (48.58%).
- Final correct among those recoverable rows: Accurate75 377/570 (66.14%),
  Fast300 1687/2096 (80.49%), DEV60 183/239 (76.57%).
- Post-filter loss: 0 in Accurate75 and 0 in Fast300; two Accurate75 adapter
  parse gains are reported separately.
- Remaining unrecoverable rows: Accurate75 83, Fast300 313, DEV60 253 under
  the stage evaluator’s frozen contracts.

## Document types and field regressions

| Set | CI | PL | B/L |
|---|---:|---:|---:|
| Accurate75 #1 | 152/320 (47.50%) | 178/263 (67.68%) | 47/70 (67.14%) |
| Fast300 | 864/1106 (78.12%) | 656/1010 (64.95%) | 167/293 (57.00%) |
| DEV60 | 105/208 (50.48%) | 56/156 (35.90%) | 22/128 (17.19%) |

No field-level regression was introduced relative to the active extractor.
The main remaining development weaknesses are CI/PL item description and unit
selection, and B/L notify-party/party-block selection. The detailed field
counts are in each `field_metrics.json` under the regression artifact root.

## Unsupported Gold acceptance

The v4 Gold benchmark supports CI parties/item rows, PL parties/item
rows, and B/L shipper/consignee/notify-party rows. Other canonical keys are
still emitted by the product but remain `ambiguous_gt` in this MVP benchmark
and are excluded from accuracy. See
`docs/UNSUPPORTED_FIELD_PRODUCT_ACCEPTANCE.md`.

## Verification

- `python -m unittest discover -s tests -v`: 90 passed.
- Production static audit: PASS.
- CLI/service fixture smoke: CI, PL, and B/L PASS.
- `app.py` and integration CLI compile: PASS.
- Historical evaluator consistency and three-set regression artifacts are
  preserved.

## Limitations

1. The current standalone production parity kernel retains normalized,
   projected design-coordinate fallback rules internally to preserve active
   behavior. It is isolated from legacy modules but is not a fully
   layout-template-independent resolver yet.
2. Available Gold is an MVP development subset; unsupported fields are not an
   accuracy claim.
3. Stage failure labels are diagnostic projections, not a new ground-truth
   annotation of causal failure.
4. DEV60 uses its historical Gold/OCR contract and must not be compared as an
   equal distribution with Accurate75/Fast300.
5. GPU execution depends on the validated local Paddle environment and was
   not launched by this final documentation smoke.
