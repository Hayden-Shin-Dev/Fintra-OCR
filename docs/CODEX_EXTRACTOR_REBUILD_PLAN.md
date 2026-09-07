# Fintra Extractor Rebuild Plan

## Scope

This work rebuilds the Fintra extractor behind a single clean production entry
point while keeping the frozen OCR outputs and `MVP_DEVELOPMENT_GOLD_V4`
unchanged. Development evaluation uses only the existing Accurate75 #1,
Fast300, and DEV60 sets. The sealed external final-holdout process is not
inspected or terminated by this workflow.

## Frozen inputs

- Branch: `restart/clean-v2`
- Starting revision: `e8feb4c`
- Gold: `MVP_DEVELOPMENT_GOLD_V4`
- OCR: existing Paddle cached outputs
- Existing baseline: active extractor behavior captured at `b6989e1`
- Protected external process output: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3`

## Execution checklist

- [x] Record Git and running-process state
- [x] Create this execution plan
- [x] Reproduce Accurate75 #1, Fast300, and DEV60 baseline
- [x] Probe existing extractor variants with the same inputs/evaluator
- [x] Quantify stage failures and fragment-filter loss
- [x] Implement a clean production extractor entry point
- [x] Generalize shared party-block resolution
- [x] Generalize CI/PL item-table resolution
- [x] Generalize scalar resolution and evidence preservation
- [x] Add regression matrix and service/CLI/UI coverage
- [x] Run three-set regression and freeze the production extractor
- [x] Perform development product acceptance steps; sealed holdout remains external
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
| Clean production boundary | complete | `fintra/extraction/production.py`, `production_engine.py`, `production_refinement.py`, `production_table.py` |
| Three-set regression | complete | `artifacts/fintra/extractor-rebuild/regression/production-*-v3/` |
| Integration smoke | complete | `artifacts/fintra/product-smoke-dev/` |
