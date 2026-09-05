# Fintra OCR V2 — AI-Hub OCR baseline report

Status: `PARTIAL`

The 15-document smoke baseline completed end-to-end on real AI-Hub Validation
data: Commercial Invoice 5, Packing List 5, and B/L 5. It used the original
AI-Hub weights, vocabulary, crop/preprocessing, decoder, and recognition logic.
Recognition ran through a separate CPU reference runner because bundled
PyTorch 1.7.1 cannot execute RTX 4050 `sm_89`.

This is **AI-Hub original weights/code CPU reference baseline**. It is not an
official GPU baseline and not an official AI-Hub reproduced score.

## IoU evaluation — micro aggregate

| Threshold | Documents | GT regions | Predictions | Matched | Detection precision | Detection recall | Detection F1 | Exact recognition | CER | E2E exact recall |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 15 | 1498 | 1786 | 1396 | 0.781635 | 0.931909 | 0.850183 | 839/1396 | 0.144931 | 0.560080 |
| 0.8 | 15 | 1498 | 1786 | 1073 | 0.600784 | 0.716288 | 0.653471 | 619/1073 | 0.137398 | 0.413218 |

Macro document-level Detection F1 is `0.855888` at IoU 0.5 and `0.665740`
at IoU 0.8. Macro exact recognition accuracy is `0.589605` and `0.566825`.

## IoU by document type

Detailed results are in `artifacts/aihub/validation/smoke/aggregate/metrics.*`.

- Commercial Invoice: 5 documents, 412 GT, 437 predictions, 362 matches at IoU 0.5, micro Detection F1 `0.852768`, exact accuracy `0.508287`, CER `0.185550`.
- Packing List: 5 documents, 480 GT, 512 predictions, 466 matches at IoU 0.5, micro Detection F1 `0.939516`, exact accuracy `0.671674`, CER `0.120875`.
- B/L: 5 documents, 606 GT, 837 predictions, 568 matches at IoU 0.5, micro Detection F1 `0.787249`, exact accuracy `0.602113`, CER `0.137214`.

## AI-Hub bundled official evaluator

The bundled `evaluation_method/script.py` was run against all 15 cases. Its
matching is pseudo-character-center inclusion with area precision constraint
`0.5`, not polygon IoU.

| Type | Documents | Detection P | Detection R | Detection Hmean | E2E P | E2E R | E2E Hmean | Recognition score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Commercial Invoice | 5 | 0.921796 | 0.895144 | 0.908275 | 0.759489 | 0.794863 | 0.776774 | 0.874372 |
| Packing List | 5 | 0.958625 | 0.975057 | 0.966771 | 0.869110 | 0.913508 | 0.890756 | 0.930739 |
| B/L | 5 | 0.815620 | 0.933144 | 0.870433 | 0.675691 | 0.875533 | 0.762739 | 0.937088 |
| **Overall** | **15** | **0.884820** | **0.935252** | **0.909337** | **0.750748** | **0.864492** | **0.803615** | **0.918105** |

## Execution and preservation

- Existing CI-01 Detection/Recognition result was reused; it was not rerun.
- New 14 cases ran CPU Detection and Recognition with the original checkpoint and runtime dictionary.
- Raw TXT, Detection PKLs, source GT JSONs, official evaluator results, matches/errors, and debug overlays are under `artifacts/aihub/validation/smoke/`.
- `sample.zip` was not used. Azure blobs were read only; downloaded ZIP copies were deleted after extraction.

## Remaining status

- Full 31-document target: not run; this report covers the 15-document smoke set.
- Official GPU baseline: blocked by original PyTorch 1.7.1 `sm_89` incompatibility.
- Modern RTX4050 migration, field extraction, PaddleOCR, LLM/RAG, fine-tuning, and threshold tuning: not started.
- Git worktree metadata remains broken; no main branch change or push was made.
