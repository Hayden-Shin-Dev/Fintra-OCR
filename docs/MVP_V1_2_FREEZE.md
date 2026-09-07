# Fintra OCR extractor MVP v1.2 freeze

This freeze records the completed extractor rebuild handoff on
`restart/clean-v2`. The frozen benchmark is `MVP_DEVELOPMENT_GOLD_V4` with
the cached Paddle OCR outputs; no Gold or OCR artifact is changed by this
freeze.

## Production boundary

- Service entry point: `fintra.services.document_service.extract_document`
- Extractor dispatch: `fintra.extraction.production.EXTRACTORS`
- CLI: `scripts/run_document_extraction.py`
- Response schema: `fintra-document-contract.v1`
- UI: `app.py` through the same service boundary

The historical `documents.py`, `refinement.py`, and `table.py` files remain
for reproducible comparisons. They are not imported by the production
boundary. The production implementation is the standalone parity kernel in
`fintra/extraction/production_engine.py` and its local helpers.

## Frozen regression results

| Set | Overall | CI | Packing List | B/L |
|---|---:|---:|---:|---:|
| Accurate75 #1 | 377/653 (57.73%) | 152/320 (47.50%) | 178/263 (67.68%) | 47/70 (67.14%) |
| Fast300 | 1687/2409 (70.03%) | 864/1106 (78.12%) | 656/1010 (64.95%) | 167/293 (57.00%) |
| DEV60 legacy | 183/492 (37.20%) | 105/208 (50.48%) | 56/156 (35.90%) | 22/128 (17.19%) |

Raw OCR field recoverability is 570/653 (87.29%), 2096/2409 (87.01%), and
239/492 (48.58%) respectively. Correct rows among those recoverable rows are
377/570, 1687/2096, and 183/239.

## Verification gates

- 90 repository unittest cases pass.
- Production static audit passes.
- Accurate75, Fast300, and DEV60 evaluator CSV/JSON pairs pass consistency
  checks.
- CI, Packing List, and B/L document-file integration smoke tests pass.
- UI/service and CLI modules compile.
- Historical 625-vs-626 discrepancy remains an archival unresolved item only:
  the preserved pair is internally consistent at 626, while the historical
  625-side artifact is not present locally.

## Explicit limitations

The current kernel preserves active behavior and therefore retains a
normalized, projected design-coordinate fallback internally. It is isolated
from legacy imports, but it is not yet a fully template-independent resolver.
The v4 Gold is an MVP development benchmark: unsupported canonical fields are
still emitted by the product but excluded from accuracy denominators when
their Gold status is `ambiguous_gt`.
