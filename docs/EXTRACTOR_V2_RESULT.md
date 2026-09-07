# Extractor v2 compatibility and semantic-overlay result

This report records the v2 compatibility baseline and conservative semantic
overlay. The v2 entry point wraps the frozen Production Clean extractor; it
does not replace OCR, Gold, normalization, or the evaluator.

## Frozen benchmark

| Set | Clean | Legacy | Extractor v2 |
| --- | ---: | ---: | ---: |
| Accurate75 (653 applicable) | 467/653 = 71.52% | 298/653 = 45.64% | 469/653 = 71.82% |
| Fast300 (2409 applicable) | 1830/2409 = 75.97% | 1313/2409 = 54.50% | 1830/2409 = 75.97% |
| v3 75 (600 applicable) | 313/600 = 52.17% | 389/600 = 64.83% | 314/600 = 52.33% |

Document-type normalized accuracy:

| Set | Extractor | CI | Packing List | B/L |
| --- | --- | ---: | ---: | ---: |
| Accurate75 | clean | 78.13% | 68.44% | 52.86% |
| Accurate75 | legacy | 22.81% | 67.68% | 67.14% |
| Accurate75 | v2 overlay | 78.13% | 69.20% | 52.86% |
| Fast300 | clean | 85.53% | 71.68% | 54.61% |
| Fast300 | legacy | 44.30% | 64.95% | 57.00% |
| Fast300 | v2 overlay | 85.53% | 71.68% | 54.61% |
| v3 75 | clean | 52.42% | 52.23% | 51.72% |
| v3 75 | legacy | 67.66% | 59.24% | 65.52% |
| v3 75 | v2 overlay | 52.42% | 52.87% | 51.72% |

The denominator is identical within each dataset. The overlay preserves the
clean result when no strong typed evidence is available; it is not yet ready
to replace the current clean extractor.

The table above is read from the existing frozen evaluation artifacts (no OCR
or Gold regeneration):

- `artifacts/fintra/extractor-v2-safe-accurate75/field_metrics.json`
- `artifacts/fintra/extractor-v2-safe-fast300/field_metrics.json`
- `artifacts/fintra/extractor-v2-safe-v3/field_metrics.json`

## Implementation status

The v2 path is under `fintra/extraction/v2/`:

`OCRResult -> Production Clean baseline -> scoped semantic overlay -> stable
v2 contract`.

`Candidate` is used before selection and retains semantic anchor, relation,
normalized geometry, OCR confidence, type validity, section, score, and reject
reason. The overlay has no imports from legacy, production, refinement, or
strategy modules. The baseline adapter intentionally calls the frozen Clean
extractor.

The checked-in Audit Field Schema v2 artifact contains 72 unique semantic
fields, split into 59 document-level slots and 13 item-level slots. The v2
contract emits all applicable slots for CI (52 total), Packing List (46 total),
and B/L (41 total); unavailable evidence is represented as a nullable
`missing` slot. The earlier `packing_list_number` and `date` names remain only
as compatibility slots for the initial v2 preview and are not counted in the
72-field audited inventory.

## Root-cause fixes included

- B/L retains `shipment_date` as a contract field.
- Headerless three-number rows infer quantity/unit-price/amount in that order.
- Layout adjacency protects only semantic headings, so value cells are not
  removed merely because another fuzzy alias matched them.
- Party anchor inventory is document-scoped; fuzzy `CONSIGNEE` is not accepted
  as a `SHIPPER` heading, and incompatible `SAME AS` relations are rejected.
- Existing baseline values are not overwritten by weak overlay candidates.

## Field/UI completeness

- Inventory audit: `artifacts/fintra/schema-v2/schema_contract_audit.json`
- Contract audit report: `artifacts/fintra/schema-v2/SCHEMA_V2_CONTRACT_AUDIT.md`
- Dedicated v2 UI: `extractor_v2_app.py`
- The UI calls the frozen production `PaddleOCRBackend` directly, then
  `fintra.extraction.v2.EXTRACTORS`; it does not use the active clean service
  dispatch.
- Every applicable document slot is rendered, including `None`/`missing`
  values and `source_label`/`semantic_relation` provenance columns. Item rows
  and raw OCR regions are displayed separately.

## Main remaining limitations

The overlay still leaves most party and free-text row-association errors to
Production Clean. It is not yet a broad ITEM_TABLE/PARTY_BLOCK replacement.
The v3 set is a generalization check only and was not used to create rules.

## Verification

- Full `unittest discover`: 109 passed.
- Schema v2 contract tests: passed; 72/72 intended fields defined and wired.
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
