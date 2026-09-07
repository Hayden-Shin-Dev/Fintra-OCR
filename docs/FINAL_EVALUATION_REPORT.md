# Fintra OCR MVP final evaluation

This report was produced after the v1.1 freeze. FINAL-HOLDOUT #2 was not used
for extractor tuning or Gold generation. The frozen Paddle OCR JSON, the
prediction-blind v4 Gold, and the frozen extractor were evaluated once.

## FINAL-HOLDOUT #2 selection

- Allowlist: `artifacts/fintra/train-scale-v1/parallel/accurate-final-balanced75.txt`
- Cache: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout/cases`
- Selected: 75 documents exactly: CI 25, Packing List 25, B/L 25.
- Source-group distribution: each of INV01..INV05, PL01..PL05, BL01..BL05
  contributes 5 documents.
- Overlap with Accurate75-1: 0; overlap with Fast300: 0.
- Final Gold: `artifacts/fintra/gold_audit/semantic-v4-image-final-balanced75/cases`
- Gold image/TL audit: 610 available fields, all `VERIFIED_CORRECT`; 75 images
  present; no CANNOT_VERIFY available field.

## Frozen extractor result

| Scope | Correct / available | Normalized accuracy |
|---|---:|---:|
| Overall | 392 / 610 | 64.26% |
| Commercial Invoice | 138 / 270 | 51.11% |
| Packing List | 208 / 265 | 78.49% |
| B/L | 46 / 75 | 61.33% |

### Available field results

| Document | Field | Correct / available | Accuracy |
|---|---|---:|---:|
| CI | buyer | 14/16 | 87.50% |
| CI | seller | 12/24 | 50.00% |
| CI | item description (rows 0/1/2) | 8/22; 4/15; 0/9 | 36.36%; 26.67%; 0.00% |
| CI | item quantity (rows 0/1/2) | 16/22; 10/15; 3/9 | 72.73%; 66.67%; 33.33% |
| CI | item unit (rows 0/1/2) | 8/22; 4/15; 0/9 | 36.36%; 26.67%; 0.00% |
| CI | item unit_price (rows 0/1/2) | 16/22; 10/15; 4/9 | 72.73%; 66.67%; 44.44% |
| CI | item amount (rows 0/1/2) | 16/22; 10/15; 3/9 | 72.73%; 66.67%; 33.33% |
| PL | exporter | 23/25 | 92.00% |
| PL | consignee | 22/24 | 91.67% |
| PL | item description (rows 0/1/2) | 6/25; 13/25; 13/22 | 24.00%; 52.00%; 59.09% |
| PL | item quantity (rows 0/1/2) | 22/25; 22/25; 22/22 | 88.00%; 88.00%; 100.00% |
| PL | item unit (rows 0/1/2) | 21/25; 22/25; 22/22 | 84.00%; 88.00%; 100.00% |
| B/L | shipper | 18/25 | 72.00% |
| B/L | consignee | 19/25 | 76.00% |
| B/L | notify_party | 9/25 | 36.00% |

Fields not listed above had no available v4 Gold rows in this 75-document
sample and therefore are not silently treated as zero-accuracy fields.

## Stage and failure result

- OCR recoverable: 540/610 = 88.52%.
- Recoverable-but-wrong: 160.
- Extractor failure clusters: ITEM_TABLE 120, PARTY_BLOCK 40.
- OCR failure clusters: fragmentation/merge 36, recognition 34.
- Detailed rows: `artifacts/fintra/train-scale-v1/final-evaluation/accurate-final-balanced75/recoverable_but_wrong.csv`
- Stage report: `artifacts/fintra/train-scale-v1/final-evaluation/accurate-final-balanced75/stages/`

These holdout failures are diagnostic only; no post-freeze code or Gold change
was made from them.

## Development-set comparison

| Set | Overall | CI | Packing List | B/L |
|---|---:|---:|---:|---:|
| Fast300 | 1687/2409 = 70.03% | 864/1106 = 78.12% | 656/1010 = 64.95% | 167/293 = 57.00% |
| Accurate75-1 | 377/653 = 57.73% | 152/320 = 47.50% | 178/263 = 67.68% | 47/70 = 67.14% |
| FINAL-HOLDOUT #2 | 392/610 = 64.26% | 138/270 = 51.11% | 208/265 = 78.49% | 46/75 = 61.33% |

These are different samples and are not a causal accuracy comparison.

## Integration smoke

The service and CLI were exercised with one existing frozen Paddle fixture for
each document type. All three produced valid `fintra-document-contract.v1`
JSON and preserved OCR region evidence:

- CI: 73 regions, valid canonical JSON.
- Packing List: 71 regions, valid canonical JSON.
- B/L: 153 regions, valid canonical JSON.

The UI is `app.py`; the direct command and dependency setup are in
`docs/DOCUMENT_INTEGRATION.md`. The agent did not launch a new GPU inference
process; the documented command is ready for the validated local Paddle
environment.

## Delivery

- Branch: `restart/clean-v2`
- Freeze/evaluator source: `f54b0bb` (pushed to `origin/restart/clean-v2`).
- Integration boundary: `fintra.services.document_service.extract_document`
- CLI: `scripts/run_document_extraction.py`
- UI: `app.py`
- Contract: `fintra-document-contract.v1`
- Final evaluation artifacts are intentionally ignored by Git because they
  contain local AI-Hub data and OCR output.
