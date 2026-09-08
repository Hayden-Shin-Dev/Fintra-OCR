# Accurate75 #1 Gold Integrity Audit

This is a read-only audit of Accurate75 #1 only. It does not read the final
holdout #2, modify Gold, regenerate Gold, modify the extractor, or recalculate
evaluation scores.

## Scope and classification

The suspected mapping scope was defined before classification from the
existing evidence diagnostics:

- 15 Commercial Invoice item-description rows
- 11 B/L port rows
- 3 B/L vessel rows
- total suspected rows: 29

Classification:

- `VERIFIED_GOLD_MAPPING_ERROR`: 27
- `SOURCE_LABEL_AMBIGUOUS_OR_WRONG`: 0
- `EXTRACTOR_ERROR`: 2

The source annotation contains word-level coordinates rather than semantic
field labels. The semantic role was therefore checked against the rendered
document label/section at those coordinates, then against the Gold source
token indices and the Gold builder code. The OCR output was used only to
complete the chain; it was not used to create or alter Gold.

## Commercial Invoice descriptions

| Case | Gold value | Classification | Evidence |
|---|---|---|---|
| `inv01-081-IMG_OCR_6_T_NV_003824` | `HEAT EXCHANGER,FUEL` | `EXTRACTOR_ERROR` | Gold tokens are in the Description of Goods cell; active extraction also includes the separate shipping-mark column. |
| `inv01-082-IMG_OCR_6_T_NV_003882` | `FOGLO, FINLAND` | `VERIFIED_GOLD_MAPPING_ERROR` | Tokens are in the Final Destination block, not the item table. |
| `inv01-084-IMG_OCR_6_T_NV_003885` | `7134.60` | `VERIFIED_GOLD_MAPPING_ERROR` | Token is the HS Code cell, not the item description. |
| `inv01-084-IMG_OCR_6_T_NV_003885` | `0149.02` | `VERIFIED_GOLD_MAPPING_ERROR` | Token is the HS Code cell, not the item description. |
| `inv02-082-IMG_OCR_6_T_NV_008783` | `1641.48` | `VERIFIED_GOLD_MAPPING_ERROR` | Token is a numeric HS Code cell. |
| `inv02-082-IMG_OCR_6_T_NV_008783` | `2104.56` | `VERIFIED_GOLD_MAPPING_ERROR` | Token is a numeric HS Code cell. |
| `inv02-082-IMG_OCR_6_T_NV_008783` | `9582.24` | `VERIFIED_GOLD_MAPPING_ERROR` | Token is a numeric HS Code cell. |
| `inv02-083-IMG_OCR_6_T_NV_008944` | `Buffer` | `EXTRACTOR_ERROR` | Gold tokens are in the Description of Goods cell; active extraction also includes the shipping-mark column. |
| `inv02-085-IMG_OCR_6_T_NV_009006` | `1342.38 2` | `VERIFIED_GOLD_MAPPING_ERROR` | Numeric tokens come from the HS Code/quantity area, not description. |
| `inv02-085-IMG_OCR_6_T_NV_009006` | `8142.51 33` | `VERIFIED_GOLD_MAPPING_ERROR` | Numeric tokens come from the HS Code/quantity area, not description. |
| `inv03-083-IMG_OCR_6_T_NV_014331` | `4519.40 22` | `VERIFIED_GOLD_MAPPING_ERROR` | Numeric tokens come from the HS Code/quantity area, not description. |
| `inv03-084-IMG_OCR_6_T_NV_014439` | `3417.61 8` | `VERIFIED_GOLD_MAPPING_ERROR` | Numeric tokens come from the HS Code/quantity area, not description. |
| `inv03-085-IMG_OCR_6_T_NV_014461` | `5626.87 5` | `VERIFIED_GOLD_MAPPING_ERROR` | Numeric tokens come from the HS Code/quantity area, not description. |
| `inv04-082-IMG_OCR_6_T_NV_019353` | `TOULON, FRANCE` | `VERIFIED_GOLD_MAPPING_ERROR` | Tokens are a port/place block above the table, not an item description. |
| `inv04-084-IMG_OCR_6_T_NV_019451` | `OHKAWARA, JAPAN` | `VERIFIED_GOLD_MAPPING_ERROR` | Tokens are a port/place block above the table, not an item description. |

The reproducible builder defect is in `_ci_gold()` and the inherited v3
`_ci_table()` path: `_item_rows()` searches a broad quantity x-range without
first establishing the table header/lower boundary. Numeric terms above the
table can become synthetic item-row centers. The description x-range also
does not model a distinct shipping-mark/HS-code column. This is a Gold
generation/mapping defect, not evidence that the OCR text is missing.

## B/L ports

All 11 suspected B/L port rows are `VERIFIED_GOLD_MAPPING_ERROR`:

`bl01-081`, `bl01-085`, `bl02-081`, `bl02-083`, `bl02-085`, `bl03-085`,
`bl04-081`, `bl05-081`, `bl05-082`, `bl01-084`, and `bl02-084` (full stable
case IDs and values remain in the immutable evaluation CSV).

The source annotation coordinates place the two values under the visible
`Port of Loading` and `Port of Discharge` labels. For example, in
`bl01-081-IMG_OCR_6_T_BL_004108`, `OHSE, JAPAN` is under Port of Loading and
`GUINES, FRANCE` is under Port of Discharge, while the Gold assigns them in
the opposite fields. The Gold token indices preserve the physical tokens but
the canonical field mapping is reversed.

The cause is directly visible in both Gold builders:

- `build_semantic_field_gold.py::_bl_gold()` calls the right/center zone for
  `port_of_loading` and the left zone for `port_of_discharge`.
- `build_semantic_v3_gold.py::_place_line()` repeats the same left/right
  reversal.

This is not `SOURCE_LABEL_AMBIGUOUS_OR_WRONG`: the rendered labels and source
word positions are clear. It is a deterministic Gold mapping error.

## B/L vessel

The following three rows are `VERIFIED_GOLD_MAPPING_ERROR`:

| Case | Gold vessel | Source/document evidence |
|---|---|---|
| `bl01-085-IMG_OCR_6_T_BL_004223` | `CIF` | `CIF` is a delivery/payment term, not a vessel. |
| `bl02-085-IMG_OCR_6_T_BL_009292` | `DAF` | `DAF` is a delivery term, not a vessel. |
| `bl03-085-IMG_OCR_6_T_BL_014293` | `CFR` | `CFR` is a delivery term, not a vessel. |

The source/document section is unambiguous. Both v2 and v3 vessel rules have
an incomplete transport-prefix exclusion set that omits `CIF`, `CFR`, and
`DAF`, allowing these tokens to be selected as the first vessel candidate.

## Chain conclusion

For the 27 verified Gold errors, the chain is:

`source annotation + rendered section` (clear physical value)
→ `Gold builder zone/typed mapping` (incorrect canonical role)
→ `Gold field/value` (wrong role or wrong value)
→ `OCR evidence` (often present because it is a real printed token)
→ `extractor result` (not a valid basis for changing the Gold).

For the two CI description rows classified as extractor errors, the chain is:

`source annotation + rendered Description of Goods label` (correct Gold)
→ `Gold field/value` (correct)
→ `OCR evidence` (correct description present)
→ `active extractor` (shipping-mark and description columns combined).

## Why the initial report said one mismatch

The initial `GOLD_MAPPING_MISMATCH = 1` value came from a conservative failure
classifier. Its Gold check only recognized a small set of obvious lexical
party/reference issues; it did not inspect rendered document labels, token
coordinates, table row boundaries, or the Gold builder's port/vessel mapping
rules. It was therefore not an exhaustive Gold-integrity audit.

The later B/L port, vessel, and CI table findings were discovered by manual
source/document inspection and builder-code tracing. They were not proven by
the initial classifier, and they were not inferred merely from
`extractor != Gold`.

## Impact and decision

The confirmed defects are general builder defects and can affect other Gold
cases generated by the same rules across CI and B/L, not only these case IDs.
However, this step intentionally does not regenerate or edit Gold. No
extractor patch is made in response to a verified Gold error. Gold repair or
deterministic regeneration is a separate decision and must be performed
before using these affected rows as an extractor benchmark.
