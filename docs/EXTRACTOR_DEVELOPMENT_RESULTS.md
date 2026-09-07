# Extractor rebuild development results

## Contract and boundary

- Branch: `restart/clean-v2`
- Production entry point: `fintra.services.document_service.extract_document`
- Extractor dispatch: `fintra.extraction.production.EXTRACTORS`
- CLI: `scripts/run_document_extraction.py`
- Canonical contract: `fintra-document-contract.v1`
- Gold: frozen `MVP_DEVELOPMENT_GOLD_V4`
- OCR: frozen Paddle JSON; no OCR rerun was used here

The old `fintra.extraction.documents`, `refinement`, and `table` modules were
not deleted because they are required for historical comparison. They are not
runtime imports of the public production boundary. Production uses the
standalone `production_engine`, `production_refinement`, and
`production_table` parity kernel.

## Current production regression

The clean boundary is parity-preserving against the active extractor. “Before”
is the captured active output and “after” is the clean production output.

| Set | Before | After | Result |
|---|---:|---:|---|
| Accurate75 #1 | 377/653 = 57.73% | 377/653 = 57.73% | no regression |
| Fast300 | 1687/2409 = 70.03% | 1687/2409 = 70.03% | no regression |
| DEV60 legacy | 183/492 = 37.20% | 183/492 = 37.20% | no regression |

By document type:

| Set | CI | Packing List | B/L |
|---|---:|---:|---:|
| Accurate75 #1 | 152/320 = 47.50% | 178/263 = 67.68% | 47/70 = 67.14% |
| Fast300 | 864/1106 = 78.12% | 656/1010 = 64.95% | 167/293 = 57.00% |
| DEV60 legacy | 105/208 = 50.48% | 56/156 = 35.90% | 22/128 = 17.19% |

Primary-field aggregation using the repository definition is available in the
field metrics; current clean-path counts are Accurate75 200/267, Fast300
796/1008, and DEV60 legacy 70/168. The old and new production paths are equal
on all three sets.

## Historical checkpoint comparison

| Revision | Accurate75 #1 | Fast300 | DEV60 legacy | Classification |
|---|---:|---:|---:|---|
| `b8d53ee` | 197/653 = 30.17% | 964/2409 = 40.02% | 186/492 = 37.80% | historical comparison |
| `d23a7cb` | 298/653 = 45.64% | 1316/2409 = 54.63% | 183/492 = 37.20% | historical comparison |
| `055d28f` | 298/653 = 45.64% | 1316/2409 = 54.63% | 183/492 = 37.20% | historical comparison |
| current clean production | 377/653 = 57.73% | 1687/2409 = 70.03% | 183/492 = 37.20% | KEEP |

The historical runs load source revisions in isolated modules for diagnosis;
the worktree was not reset or overwritten.

## Stage decomposition

| Set | Applicable | Raw OCR recoverable | Candidate hit | Resolver correct | Final correct |
|---|---:|---:|---:|---:|---:|
| Accurate75 #1 | 653 | 570 | 361 | 361 | 377 |
| Fast300 | 2409 | 2096 | 1677 | 1677 | 1687 |
| DEV60 legacy | 492 | 239 | 158 | 158 | 183 |

This corresponds to raw OCR recoverability of 87.29%, 87.01%, and 48.58% and
final recovery among raw-recoverable fields of 66.14%, 80.49%, and 76.57%.
The stage evaluator is diagnostic: `candidate_hit` means the selected source
is present in the evidence neighborhood, not that an independent candidate
generator oracle has been proven.

Fragment-filter audit found no `POST_OCR_FILTER_LOSS`: 0/570 Accurate75 and
0/2096 Fast300 recoverable fields were lost by the production region filter.
The Accurate75 comparison found 2 adapter parse gains caused by decoding a
serialized AI-Hub comma escape; this is recorded separately and is not an OCR
accuracy gain.

## Failure decomposition

The current diagnostic classifier over all 3554 evaluated field rows reports:

| Class | Count |
|---|---:|
| `CANDIDATE_GENERATION_FAILURE` | 272 |
| `COLUMN_MAPPING_FAILURE` | 89 |
| `DESCRIPTION_CONTAMINATION` | 180 |
| `ROLE_ASSIGNMENT_FAILURE` | 166 |
| `OCR_UNRECOVERABLE` | 649 |
| `NONE` | 2198 |

The classifier is explicitly diagnostic, not a proof of causal attribution.
It does not claim that the 89 column rows are independently annotated row
errors. Detailed rows are in
`artifacts/fintra/extractor-rebuild/failure-analysis/production-v2/`.

## Field highlights

On Accurate75 #1, strongest supported fields include B/L `shipper` 21/25
(84.00%), CI `buyer` 13/15 (86.67%), PL `exporter` 21/25 (84.00%), and PL
item quantity/unit at 84.00%/84.00% for row 0. Weakest repeated clusters are
CI item descriptions (10.00–22.73%), CI item units (0.00–33.33%), and PL item
descriptions (12.00–41.67%). On Fast300, CI amount/unit price are 95.24–98.89%,
while PL descriptions are 17.00–34.25% and B/L notify party is 32.26%.
These are field-level effects; they do not imply a change to OCR character
accuracy.

## Artifacts

- Baselines: `artifacts/fintra/extractor-rebuild/baseline/`
- Variant probe: `artifacts/fintra/extractor-rebuild/probe/`
- Historical checkpoints: `artifacts/fintra/extractor-rebuild/historical/`
- Production regressions: `artifacts/fintra/extractor-rebuild/regression/`
- Failure analysis: `artifacts/fintra/extractor-rebuild/failure-analysis/`
- Development integration smoke: `artifacts/fintra/product-smoke-dev/`

All local AI-Hub/OCR artifacts remain ignored by Git; the scripts and docs are
versioned, while the local paths above preserve reproducibility on this host.
