# Fintra Extractor Rebuild Plan

## Scope

This work builds and freezes a clean-room extractor while keeping the frozen
OCR outputs and `MVP_DEVELOPMENT_GOLD_V4` unchanged. The historical extractor
is retained only as an explicitly labelled comparison path. The clean-room
engine is active after the Accurate75 #1 and Fast300 gate; DEV60 remains a
diagnostic-only historical contract and is not a production hard gate. The
sealed external final-holdout process is not inspected or terminated by this
workflow.

## Frozen inputs

- Branch: `restart/clean-v2`
- Starting revision: `e8feb4c`
- Gold: `MVP_DEVELOPMENT_GOLD_V4`
- OCR: existing Paddle cached outputs
- Existing baseline: active historical extractor behavior captured at `2c96720`
- Protected external process output: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3`

## Execution checklist

- [x] Record Git and running-process state
- [x] Create this execution plan
- [x] Reproduce Accurate75 #1, Fast300, and DEV60 baseline
- [x] Probe existing extractor variants with the same inputs/evaluator
- [x] Quantify stage failures and fragment-filter loss
- [x] Implement a clean-room extractor candidate entry point
- [x] Generalize shared party-block resolution
- [x] Generalize CI/PL item-table resolution
- [x] Generalize scalar resolution and evidence preservation
- [x] Add regression matrix and service/CLI/UI coverage
- [x] Run three-set regression for the clean candidate
- [x] Switch backend production dispatch to clean candidate (Accurate75/Fast300 gate)
- [x] Freeze production extractor after the development gate
- [ ] Perform development product acceptance steps; sealed holdout remains external
- [x] Update final documentation and commit/push each meaningful unit

## Safety rules

- Do not modify Gold, cached OCR, or raw AI-Hub data.
- Do not inspect FINAL-HOLDOUT #3 content before the v1.2 freeze.
- Do not terminate the protected external Accurate OCR processes.
- Do not hardcode case IDs, GT literals, company/port/product names, or absolute
  template coordinates in the clean production path.
- Keep legacy modules available for comparison only; production must not call
  them.

## Progress log

| Phase | Status | Revision/artifact |
|---|---|---|
| Initial state capture | complete | `e8feb4c` |
| Plan | complete | this file |
| Baseline | complete | `artifacts/fintra/extractor-rebuild/baseline/` |
| Variant probe | complete | `artifacts/fintra/extractor-rebuild/probe/` |
| Stage/failure analysis | complete | `artifacts/fintra/extractor-rebuild/regression/production-stages-v3/`, `failure-analysis/` |
| Clean-room boundary | complete | `fintra/extraction/clean/{layout,candidate,party,scalar,table,engine}.py` |
| Accurate/Fast regression | complete | `artifacts/fintra/extractor-rebuild/regression/clean-*-v11/` |
| Integration smoke | complete | `artifacts/fintra/product-smoke-dev/` |

## Clean candidate gate (current)

The clean namespace recursively imports only the OCR adapter, canonical schema,
normalization primitives, and its own clean modules. It does not import or call
the historical `documents`, `refinement`, `strategies`, `table`,
`production_engine`, or `production_refinement` modules.

Latest production metrics:

| Set | Overall | CI | PL | B/L | Status |
|---|---:|---:|---:|---:|---|
| Accurate75 #1 | 467/653 (71.52%) | 78.12% | 68.44% | 52.86% | frozen |
| Fast300 | 1830/2409 (75.96%) | 85.53% | 71.68% | 54.61% | frozen |
| DEV60 | 88/492 (17.89%) | 22.60% | 13.46% | 15.62% | diagnostic only |

The DEV60 rows use the historical legacy field contract while Accurate75 and
Fast300 use semantic-v4 MVP Gold. This contract mismatch is retained as a
diagnostic limitation and is not used to block clean production dispatch.
