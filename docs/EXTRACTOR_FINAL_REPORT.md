# Fintra clean-room extractor freeze

This report closes the Accurate75/Fast300 development gate. Gold, frozen Paddle
OCR output, and the sealed external holdout were not modified or inspected.

## Production handoff

- Branch: `restart/clean-v2`
- Production callable: `fintra.services.document_service.extract_document`
- Production extractor namespace: `fintra.extraction.clean.engine`
- CLI: `scripts/run_document_extraction.py`
- Output: `fintra-document-contract.v1` evidence-bearing canonical JSON
- UI integration: `app.py` uses the same service boundary
- Historical comparison: explicit `legacy` strategy from `fintra.extraction.documents`

The clean path is an independent implementation under
`fintra/extraction/clean/`. Its recursive audit has no imports or calls to the
legacy documents/refinement/strategies/table or production-engine modules.

## Development before → after

The before values are the frozen historical extractor baseline. The after
values are the clean engine measured with the same frozen OCR and
`MVP_DEVELOPMENT_GOLD_V4` available-field evaluator.

| Set | Before overall | After overall | Before CI / PL / B/L | After CI / PL / B/L |
|---|---:|---:|---|---|
| Accurate75 #1 | 377/653 (57.73%) | 467/653 (71.52%) | 152/320, 178/263, 47/70 | 250/320, 180/263, 37/70 |
| Fast300 | 1687/2409 (70.03%) | 1830/2409 (75.96%) | 864/1106, 656/1010, 167/293 | 946/1106, 724/1010, 160/293 |
| DEV60 diagnostic | 183/492 (37.20%) | 88/492 (17.89% snapshot) | historical contract | diagnostic only |

DEV60 uses a different historical Gold/OCR contract and is not a production
hard gate or tuning target.

## OCR and extractor recovery

| Set | OCR recoverable | Extractor correct | Recovery among recoverable | Remaining OCR-unrecoverable |
|---|---:|---:|---:|---:|
| Accurate75 #1 | 570/653 (87.29%) | 467 | 467/570 (81.93%) | 83 |
| Fast300 | 2096/2409 (87.01%) | 1830 | 1830/2096 (87.31%) | 313 |

Stage artifacts separate OCR recoverability from candidate/resolver outcomes:
`artifacts/fintra/extractor-rebuild/regression/clean-stages-v11/`.

## Main changes

- normalized page geometry and semantic-anchor discovery
- pre-selection typed `FieldCandidate` generation and ranking
- independent PARTY, SCALAR, and CI/PL ITEM_TABLE resolvers
- wrapped-line reading order and multiline table continuation handling
- typed organization/address boundary for combined party OCR regions
- evidence source text, bbox, confidence, and provenance preserved
- fragment suppression requires text and geometry duplicate evidence

## Unsupported Gold acceptance

The MVP Gold intentionally excludes unsupported field families as
`ambiguous_gt`; this is not a production claim that those fields are absent.
See `docs/UNSUPPORTED_FIELD_PRODUCT_ACCEPTANCE.md`.

## Verification

- recursive production audit: PASS
- full unittest suite: 102 passed
- CLI/service fixture smoke: CI, PL, and B/L PASS
- smoke artifacts: `artifacts/fintra/extractor-rebuild/integration-freeze-smoke/`
- Accurate/Fast metrics: `artifacts/fintra/extractor-rebuild/regression/clean-accurate75-v11/` and `clean-fast300-v11/`

## Limitations

1. B/L party and item fields remain the weakest available-field clusters;
   ambiguous Gold and role/layout mismatches are not fixed by hardcoding.
2. OCR-unrecoverable fields cannot be recovered by the extractor.
3. DEV60 is retained for diagnostics only because its historical contract is
   not comparable to semantic-v4 MVP Gold.
4. GPU execution still depends on the validated local Paddle environment.
