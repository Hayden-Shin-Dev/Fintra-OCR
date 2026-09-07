# Extractor v2 comparison result

This report compares the independent `fintra.extraction.v2` implementation
with the frozen production-clean and legacy extractors. All three use the
same frozen Paddle OCR caches, semantic-v4 Gold, normalization, and evaluator.

## Frozen benchmark

| Set | Clean | Legacy | Extractor v2 |
| --- | ---: | ---: | ---: |
| Accurate75 (653 applicable) | 467/653 = 71.52% | 298/653 = 45.64% | 221/653 = 33.84% |
| Fast300 (2409 applicable) | 1830/2409 = 75.97% | 1313/2409 = 54.50% | 1146/2409 = 47.57% |
| v3 75 (600 applicable) | 313/600 = 52.17% | 389/600 = 64.83% | 138/600 = 23.00% |

Document-type normalized accuracy:

| Set | Extractor | CI | Packing List | B/L |
| --- | --- | ---: | ---: | ---: |
| Accurate75 | clean | 78.13% | 68.44% | 52.86% |
| Accurate75 | legacy | 22.81% | 67.68% | 67.14% |
| Accurate75 | v2 | 33.44% | 43.35% | 0.00% |
| Fast300 | clean | 85.53% | 71.68% | 54.61% |
| Fast300 | legacy | 44.30% | 64.95% | 57.00% |
| Fast300 | v2 | 54.70% | 45.94% | 26.28% |
| v3 75 | clean | 52.42% | 52.23% | 51.72% |
| v3 75 | legacy | 67.66% | 59.24% | 65.52% |
| v3 75 | v2 | 27.14% | 29.94% | 10.34% |

The denominator is identical within each dataset. v2 is therefore not an
apples-to-oranges result, but it is not ready to replace the current clean
extractor.

## Implementation status

The independent path is under `fintra/extraction/v2/`:

`OCRResult -> normalized Layout -> semantic anchors -> typed Candidates ->
ranking -> party/scalar/table assignment -> EvidenceField contract`.

`Candidate` is used before selection and retains semantic anchor, relation,
normalized geometry, OCR confidence, type validity, section, score, and reject
reason. The namespace has no imports from legacy, production, refinement,
strategy, or clean extractor modules.

The path covers 69 semantic specifications, 59 document-level slots, and
invoice/packing item-field families. Missing or unsupported evidence remains
nullable rather than being guessed.

## Main observed regressions

The independent v2 currently loses most heavily on invoice table quantity/unit/
unit-price cells, Packing List party fields, and B/L party/scalar fields. The
v3 B/L result is especially weak. A small number of field-level gains exist,
but they do not generalize across all three sets. This is evidence for another
generalized extractor iteration, not a reason to alter Gold or OCR.

## Verification

- Full `unittest discover`: 105 passed.
- v2 direct unit checks: passed.
- v2 compile check: passed.
- Recursive AST audit for forbidden legacy/production imports: passed.
- OCR protection audit: unchanged.

## Decision

`EXTRACTOR_V2_READY_FOR_MVP = NO`

`NEEDS_ONE_MORE_ITERATION`

No production dispatch, existing clean extractor, legacy extractor, OCR
implementation, OCR model/config/cache, Gold, or evaluator was changed by the
v2 comparison adapter.
