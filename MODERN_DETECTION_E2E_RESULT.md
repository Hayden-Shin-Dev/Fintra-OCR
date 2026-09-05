# Modern Detection + End-to-End OCR Result

## Status

`PASS — MODERN_DETECTION_15_AND_FULL_E2E_EXECUTED`

The Modern Detection and Modern Recognition runtimes were executed on the
prepared 15-document Validation smoke set (Commercial Invoice 5, Packing List
5, B/L 5). The bundled AI-Hub evaluator completed successfully over the
generated submission.

This result is named **Modern runtime with AI-Hub bundled official evaluator**.
It is not described as an official AI-Hub GPU baseline or as an official
AI-Hub reproduced score. The original model weights were retained; no model,
threshold, preprocessing, decoder, or postprocessing tuning was applied.

## Runtime evidence

- GPU: NVIDIA GeForce RTX 4050 Laptop GPU
- CUDA capability: 8.9
- Detection checkpoint load: PASS
- Detection raw candidates in CI-01: 330
- CI-01 original-PKL parity: 112 thresholded matches, mean bbox IoU 1.0
- Recognition parity: 15/15 PASS, 1,786 regions, 0 ordered bbox/text changes
- Official evaluator documents: 15
- Detection JSON artifacts: 15
- Detection parity JSON artifacts: 15
- End-to-end case directories: 15

The evaluator emitted a “NVIDIA Driver was not detected” warning because the
evaluator container is CPU-side. This did not prevent evaluation and is not a
Modern inference failure; GPU execution had already completed in the Detection
and Recognition stages.

## AI-Hub evaluator aggregate

Metric source: the bundled `evaluation_method/script.py`. Its matching method
uses pseudo-character-center inclusion and an area precision constraint of 0.5,
not polygon IoU.

| Document type | Docs | Detection P | Detection R | Detection Hmean | E2E P | E2E R | E2E Hmean | Recognition score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Commercial Invoice | 5 | 0.901558 | 0.895144 | 0.898340 | 0.760672 | 0.795567 | 0.777728 | 0.875145 |
| Packing List | 5 | 0.948661 | 0.975057 | 0.961678 | 0.868348 | 0.913832 | 0.890510 | 0.931376 |
| B/L | 5 | 0.785358 | 0.933144 | 0.852896 | 0.675760 | 0.874822 | 0.762513 | 0.936089 |
| **Overall** | **15** | **0.862241** | **0.935252** | **0.897264** | **0.750941** | **0.864492** | **0.803726** | **0.918105** |

Overall evaluator raw counts:

- Detection correct recall / precision counts: 9,490 / 9,495
- Ground-truth / detected characters: 10,147 / 11,012
- End-to-end correct recall / precision counts: 8,772 / 8,777
- Recognition characters / scored characters: 11,688 / 9,561
- End-to-end missed / false-positive characters: 1,375 / 2,910

## Local artifacts

The generated data is intentionally ignored by Git and remains local:

`artifacts/aihub/modern_gpu/official_evaluation/`

Important files:

- `official_metrics.json` — full per-type and overall evaluator metrics
- `official_metrics.md` — compact evaluator table
- `official_output/results.zip` — evaluator result archive
- `gt.zip` — evaluator GT input archive
- `submission.zip` — evaluator submission archive
- `detection_parity/` — 15 original-vs-Modern Detection comparisons
- `end_to_end/` — 15 Detection-to-Recognition outputs

The executable implementation and reproducibility instructions are tracked in
`runtime/modern_gpu/`; large checkpoints and generated artifacts are excluded
by `.gitignore`.

