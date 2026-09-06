# Paddle GPU field evaluation

Date: 2026-09-06  
Branch: `restart/clean-v2`

## Scope

The isolated Paddle backend was run on the same 60 prepared AI-Hub
Validation cases used by the Modern field evaluation: Commercial Invoice 20,
Packing List 20, and B/L 20. The same `semantic-v2` gold and active extractor
were used. Modern artifacts were not overwritten.

Paddle runtime:

- `paddlepaddle-gpu==3.2.2` CUDA 12.9 wheel
- `paddleocr==3.7.0`
- `PP-OCRv6_medium_det`
- `PP-OCRv6_medium_rec`
- accurate mode: full page, overlapping tiles, focus bands, upscale retry, and duplicate removal
- RTX 4050 Laptop GPU, compute capability 8.9

This is a Paddle GPU comparison runtime. It is not byte-identical to the
historical CPU `paddlepaddle==3.2.0` runtime.

## Results

| Backend | Applicable fields | Exact accuracy | Normalized accuracy | Wrong | Missing | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| Modern | 410 | 32.68% | 32.68% | 57.07% | 9.51% | — |
| Paddle GPU | 410 | 37.07% | 37.56% | 53.66% | 8.54% | 0.24% |

| Document type | Applicable | Modern recoverable | Paddle recoverable | Paddle normalized accuracy |
|---|---:|---:|---:|---:|
| CI | 123 | 51 | 49 | 39.84% |
| Packing | 134 | 50 | 53 | 39.55% |
| B/L | 153 | 33 | 52 | 33.99% |

Paddle recovered 154/410 fields versus Modern 134/410, an improvement of 20
fields or 4.88 percentage points. Paddle-only wins were 65 fields; Modern-only
wins were 45 fields.

The gold-selected oracle union is 199/410 (48.54%). This is diagnostic only
and is not a deployable score or routing policy.

## Smoke and artifacts

The one-document-per-type GPU smoke completed before the full run. The full
run produced 60 canonical Paddle JSON files and the same-extractor report at:

- `artifacts/fintra/paddle_gpu_field_eval/field_results.csv`
- `artifacts/fintra/paddle_gpu_field_eval/field_metrics.json`
- `artifacts/fintra/paddle_gpu_field_eval/PADDLE_VS_MODERN.md`
- `artifacts/fintra/paddle_gpu_field_eval/comparison/paddle_vs_modern.json`

## Decision

Paddle is a better overall candidate on this benchmark, driven mainly by B/L
and Packing results. CI should remain Modern unless a later routing policy
proves a reliable Paddle advantage. Neither backend is near the 90% target;
the next improvement work must remain in field extraction/routing and evidence
handling, without changing the validated Modern OCR checkpoint.
