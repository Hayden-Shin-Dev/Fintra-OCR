# OCR stage comparison — exact 15-document golden set

This report compares the Modern and Paddle outputs on the same frozen 15-document
golden set and the same AI-Hub ground truth:

- Commercial Invoice: `ci-001`, `ci-005`, `ci-009`, `ci-013`, `ci-017`
- Packing List: `pl-001`, `pl-005`, `pl-009`, `pl-013`, `pl-017`
- B/L: `bl-001`, `bl-005`, `bl-009`, `bl-013`, `bl-017`

The primary numbers below come from the bundled AI-Hub evaluator with `--E2E
--TRANSCRIPTION`. Its detection matching is pseudo-character-center inclusion
plus area precision constraint 0.5; it is not polygon IoU.

## Primary AI-Hub evaluator results

| Type | Docs | Modern Det P | Modern Det R | Modern Det H | Paddle Det P | Paddle Det R | Paddle Det H | Modern E2E P | Modern E2E R | Modern E2E H | Paddle E2E P | Paddle E2E R | Paddle E2E H | Modern recognition score | Paddle recognition score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Commercial Invoice | 5 | 90.16% | 89.51% | 89.83% | 64.67% | 92.51% | 76.13% | 76.07% | 79.56% | 77.77% | 49.72% | 92.19% | 64.60% | 87.51% | 81.64% |
| Packing List | 5 | 94.87% | 97.51% | 96.17% | 62.91% | 90.44% | 74.21% | 86.83% | 91.38% | 89.05% | 47.15% | 90.38% | 61.97% | 93.14% | 80.67% |
| B/L | 5 | 78.54% | 93.31% | 85.29% | 49.17% | 93.12% | 64.36% | 67.58% | 87.48% | 76.25% | 22.53% | 92.75% | 36.25% | 93.61% | 82.58% |
| **Overall** | **15** | **86.22%** | **93.53%** | **89.73%** | **56.74%** | **92.14%** | **70.23%** | **75.09%** | **86.45%** | **80.37%** | **32.73%** | **91.87%** | **48.26%** | **91.81%** | **81.73%** |

Therefore the requested headline comparison is:

| Metric | Modern | Paddle |
|---|---:|---:|
| Detection Hmean | **89.73%** | **70.23%** |
| Recognition score | **91.81%** | **81.73%** |
| E2E OCR Hmean | **80.37%** | **48.26%** |

The recognition score is the AI-Hub evaluator's character-based score. It is
not the same as Fintra field evidence coverage or extractor accuracy.

## Supplementary local geometric metrics

The following values use the repository's polygon-IoU evaluator on the same 15
documents. They are provided because the AI-Hub evaluator does not expose IoU
0.5/0.8 metrics.

### Detection Hmean by IoU threshold

| Type | Modern IoU 0.5 | Paddle IoU 0.5 | Modern IoU 0.8 | Paddle IoU 0.8 |
|---|---:|---:|---:|---:|
| Commercial Invoice | 85.38% | 29.40% | 70.05% | 10.65% |
| Packing List | 93.86% | 30.06% | 71.90% | 8.81% |
| B/L | 78.78% | 20.56% | 60.47% | 10.75% |
| **Overall** | **85.04%** | **25.76%** | **66.40%** | **10.14%** |

Overall local detection precision/recall/Hmean were:

- IoU 0.5: Modern `78.21% / 93.19% / 85.04%`; Paddle `26.10% / 25.43% / 25.76%`
- IoU 0.8: Modern `61.06% / 72.76% / 66.40%`; Paddle `10.27% / 10.01% / 10.14%`

### Recognition on locally matched regions at IoU 0.5

These are character score and CER on geometrically matched regions; exact and
normalized exact are text-match rates among those matched regions. In this
15-document run normalized exact happened to equal exact.

| Type | Modern char score | Paddle char score | Modern CER | Paddle CER | Modern exact | Paddle exact | Modern normalized | Paddle normalized |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Commercial Invoice | 81.52% | 90.14% | 18.48% | 9.86% | 51.10% | 81.03% | 51.10% | 81.03% |
| Packing List | 87.85% | 91.17% | 12.15% | 8.83% | 67.17% | 84.21% | 67.17% | 84.21% |
| B/L | 86.14% | 83.51% | 13.86% | 16.49% | 60.04% | 70.45% | 60.04% | 70.45% |
| **Overall** | **85.51%** | **88.20%** | **14.49%** | **11.80%** | **60.10%** | **78.48%** | **60.10%** | **78.48%** |

## Interpretation

Paddle has a higher character score on the locally matched regions, but its
detection precision and geometric recall are much lower. That explains why its
official end-to-end Hmean is only 48.26% despite an 81.73% recognition score.
The previously reported Paddle primary recoverability of 93.37% is a separate
raw field-evidence metric on 60 documents; it must not be used as Paddle OCR
recognition accuracy.

Sources of the recorded values:

- Modern: `artifacts/aihub/modern_gpu/official_evaluation/official_metrics.md`
- Paddle: `artifacts/fintra/paddle_official_15/official_metrics.json`
- Supplementary stage output: `artifacts/fintra/ocr_stage_eval/ocr_stage_metrics.json`

