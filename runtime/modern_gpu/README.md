# Modern RTX4050 Runtime Migration

This directory is an isolated runtime for checking whether the AI-Hub
original Recognition model can run on a modern CUDA/PyTorch stack. It does
not modify the 129GB original Docker image, the original source files, or the
golden CPU-reference artifacts.

## Current scope

Recognition is prepared first. It consumes the already-produced CPU-reference
Detection TXT regions, so Detection is not rerun and no GT data is used to
create input regions. The runner preserves the original ViTSTR model,
checkpoint, dictionary construction, crop geometry, 224x224 bicubic grayscale
preprocessing, FP32 execution, sequence length, greedy decoder, and official
TXT output format. The only runtime changes are explicit device ownership and
sequential batching.

Detection is prepared as a separate migration because the original stack is
MMDetection 2.20.0 + MMCV 1.4.3 with custom ops and a custom OCRMaskRCNN
implementation. The isolated Detection image uses a CUDA development base so
MMCV's CUDA operators can be compiled, and declares the inspected
ResNet-50/FPN/Mask R-CNN graph with the original preprocessing and test
values, then uses strict checkpoint loading and the original mask-to-quad
conversion. It does not alter or rebuild the original image.

## GPU execution

After reviewing the files and ensuring the original checkpoint artifact is
present, run this one command from the project root. The script builds the
separate Modern image, runs a CI-01 Recognition smoke test, then all 15
prepared documents and ordered TXT parity checks.

```powershell
powershell -ExecutionPolicy Bypass -File .\runtime\modern_gpu\RUN_GPU.ps1
```

Codex does not execute this GPU command. A successful build alone is not a
parity result; the generated `modern_recognition/parity.json` files and
checkpoint/device logs must be inspected afterward.

After Recognition has passed, run the Detection/full-OCR chain with:

```powershell
powershell -ExecutionPolicy Bypass -File .\runtime\modern_gpu\RUN_DETECTION_GPU.ps1
```

That script first runs CI-01 Modern Detection and compares it with the
existing original Detection PKL. Only after that execution succeeds does it
expand Detection to the 15 prepared cases, feed the Modern Detection regions
to the existing Modern Recognition runner, and invoke the bundled AI-Hub
official evaluator. All outputs are written below
`artifacts/aihub/modern_gpu/`; the CPU-reference artifacts are read-only
inputs.
