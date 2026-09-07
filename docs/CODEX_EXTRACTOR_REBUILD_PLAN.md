# Fintra Extractor Rebuild Plan

## Scope

This work rebuilds the Fintra extractor behind a single clean production entry
point while keeping the frozen OCR outputs and `MVP_DEVELOPMENT_GOLD_V4`
unchanged. Development evaluation uses only the existing Accurate75 #1,
Fast300, and DEV60 sets. FINAL-HOLDOUT #2 is historical/spent and FINAL-HOLDOUT
#3 is sealed and must not be inspected until the v1.2 freeze.

## Frozen inputs

- Branch: `restart/clean-v2`
- Starting revision: `e8feb4c`
- Gold: `MVP_DEVELOPMENT_GOLD_V4`
- OCR: existing Paddle cached outputs
- Existing baseline: `e8feb4c` / 4f9487f extractor behavior
- Protected external process output: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3`

## Execution checklist

- [x] Record Git and running-process state
- [x] Create this execution plan
- [ ] Reproduce Accurate75 #1, Fast300, and DEV60 baseline
- [ ] Probe existing extractor variants with the same inputs/evaluator
- [ ] Quantify stage failures and fragment-filter loss
- [ ] Implement a clean production extractor entry point
- [ ] Generalize shared party-block resolution
- [ ] Generalize CI/PL item-table resolution
- [ ] Generalize scalar resolution and evidence preservation
- [ ] Add regression matrix and service/CLI/UI coverage
- [ ] Run three-set regression and freeze the production extractor
- [ ] Perform post-freeze holdout/product acceptance steps permitted by policy
- [ ] Update final documentation and commit/push each meaningful unit

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

