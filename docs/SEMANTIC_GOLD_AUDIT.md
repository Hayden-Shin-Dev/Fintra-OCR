# Semantic gold audit and audited baseline

This milestone audits the frozen `semantic-v2` gold independently of the
extractor.  The audit reads only AI-Hub `gt.json` token text/geometry and the
existing semantic gold.  It does not read Modern/Paddle OCR predictions and
does not modify the frozen semantic-v2 files.

## Frozen comparison

- Frozen extractor commit: `b8d53ee`
- Previous semantic-v2 result: 61.71% (253/410), preserved under the existing
  `artifacts/fintra/paddle_strategy_eval/head_active_semantic` artifact.
- Current semantic-v2 result: 64.39% (264/410), preserved under the existing
  `artifacts/fintra/paddle_strategy_eval/invoice_number_semantic` artifact.

The current re-evaluation uses the Paddle recognition case root and reproduces
64.39% on 410 applicable fields.  This is a field-extractor score, not OCR
character accuracy.

## Prediction-blind audit

The generated files are:

- `artifacts/fintra/gold_audit/semantic-v2/suspect_gold.csv`
- `artifacts/fintra/gold_audit/semantic-v2/gold_audit_metrics.json`
- `artifacts/fintra/gold_audit/semantic-v2/GOLD_AUDIT.md`

Results: 410 available fields, 139 `SUSPECT_GOLD`, and 271 valid.  A label is
reported as `UNANNOTATED_LABEL` when that semantic label is not an exact word
token in the source annotation; this is recorded, not silently invented.

## Audited semantic-v3

`build_semantic_v3_gold.py` creates a separate gold root:

- `artifacts/fintra/gold_audit/semantic-v3/cases/`
- `artifacts/fintra/gold_audit/gold_diff.csv`

The generalized, prediction-blind changes are:

- party values are selected from ordered company-like lines within the party
  block; address/phone/country-only lines are not treated as party names;
- B/L vessel and port values use the same-column row aligned to the vessel
  row, avoiding the later delivery/terminal row;
- CI table columns use relative table geometry and split a combined source
  token such as `7 PC` into typed quantity and unit values while retaining the
  same source token index;
- fields without a unique typed source candidate remain `ambiguous_gt`.

The diff currently contains 251 changed fields: Commercial Invoice 162, B/L
63, Packing List 26.  All changed rows record old/new value, status, source
token indices, and whether indices changed.  The v3 active extractor
re-evaluation is stored at:

- `artifacts/fintra/gold_audit/semantic-v3-paddle-evaluation/field_results.csv`
- `artifacts/fintra/gold_audit/semantic-v3-paddle-evaluation/field_metrics.json`

With the unchanged `b8d53ee` extractor, v3 reports 325/482 normalized matches
(67.43%).  By type: CI 68.37% (134/196), Packing 79.02% (113/143), B/L
54.55% (78/143).  The Paddle raw-OCR recoverable-but-extractor-wrong report
contains 135 rows, led by description 27, unit 22, consignee 18, shipper 10,
and unit_price 10.  This comparison is not a claim that v3 gold is finally
human-certified; it is a separately reproducible audited candidate and must
remain distinct from semantic-v2.

## Semantic-v3.1 strict validation

`validate_semantic_v3.py` validates semantic-v3 prediction-blind using source
annotation text, token geometry, field types, table row ordering, and
document-relative structure. It reads no OCR prediction or extractor output.
The semantic-v2 and semantic-v3 roots are not modified.

Outputs:

- `artifacts/fintra/gold_audit/semantic-v3.1/v3_invalid_gold.csv`
- `artifacts/fintra/gold_audit/semantic-v3.1/v3_1_validation_metrics.json`
- `artifacts/fintra/gold_audit/semantic-v3.1/v3_to_v3_1_diff.csv`
- `artifacts/fintra/gold_audit/semantic-v3.1/cases/`

The v3 candidate contained 482 available fields. Strict validation found 22
invalid candidates: Commercial Invoice 19, B/L 3, and Packing List 0. The
v3.1 output has zero residual invariant violations (`PASS`). It retained 460
v3 available candidates, used 17 structurally valid semantic-v2 fallbacks,
and marked unresolved/rejected candidates ambiguous where no strict source
backed value remained. The v3.1 diff contains 25 field changes.

Using the unchanged frozen `b8d53ee` extractor and stored Paddle OCR outputs:

- field results: `artifacts/fintra/gold_audit/semantic-v3.1-paddle-evaluation/field_results.csv`
- metrics: `artifacts/fintra/gold_audit/semantic-v3.1-paddle-evaluation/field_metrics.json`
- recoverable errors: `artifacts/fintra/gold_audit/semantic-v3.1-paddle-evaluation/recoverable_but_wrong.csv`

The v3.1 baseline is 337/475 normalized matches (70.95%) overall and 154/192
(80.21%) across primary fields. Overall by type: CI 146/191 (76.44%), Packing
113/143 (79.02%), and B/L 78/141 (55.32%). Primary by type: CI 67/74
(90.54%), Packing 63/70 (90.00%), and B/L 24/48 (50.00%). The frozen
extractor was not changed. The raw Paddle OCR recoverable-but-wrong
diagnostic contains 117 rows.

The full unittest suite still has two pre-existing layout failures, which are
not mixed into this gold work:

- `test_packing_party_headings_are_not_returned_as_values`: the layout
  extractor returns the heading `Consignee` instead of the expected company
  line.
- `test_typed_date_and_last_port_line_are_selected`: the layout extractor
  returns no value where the fixture expects `AYAMONTE, SPAIN`.
