# Modern RTX4050 Runtime Migration Report

## Status

| Component | Status | Evidence |
|---|---|---|
| Golden CPU baseline preserved | PASS | Existing 15-document artifacts were not rerun or modified |
| Original dependency/pipeline audit | PASS | `DEPENDENCY_MATRIX.md`, `ORIGINAL_PIPELINE_MAP.md` |
| Modern Recognition runtime prepared | PASS (prepared) | `runtime/modern_gpu/modern_recognition.py`, isolated Dockerfile |
| Recognition GPU smoke execution | PASS | User-run artifacts report `CUDA_CAPABILITY=8.9`, checkpoint load, and CUDA device execution |
| Recognition 15-document parity | PASS | 15/15 parity files pass; 1,786 regions, 0 changed ordered bbox/text records |
| Modern Detection migration | PASS | `runtime/modern_gpu/RUN_DETECTION_GPU.ps1`; 15 Detection outputs and parity artifacts |
| Modern full OCR | PASS | `MODERN_DETECTION_E2E_RESULT.md`; 15 Detection → Recognition cases and bundled evaluator output |

## Reference naming

The existing reference remains **AI-Hub original weights/code CPU reference
baseline**. The Modern result, once executed, must be described as a Modern
runtime parity result, not as an official GPU baseline or an official AI-Hub
reproduced score.

## Prepared artifacts

- Original Recognition checkpoint extracted read-only to
  `artifacts/aihub/runtime/transit_recog_model.pth`.
- Original runtime dictionary remains
  `artifacts/aihub/runtime/unidocs_dict_transit_runtime.txt`.
- Original Recognition source is vendored unchanged under
  `runtime/modern_gpu/vendor/original_recognition/`.
- The Modern runner emits official-compatible TXT plus structured JSON and
  records checkpoint load, region counts, exceptions, and empty text counts.
- `compare_recognition.py` performs ordered bbox/text parity against the
  existing CPU-reference TXT.
- Modern Detection is isolated in a separate MMEngine/MMCV 2.1/MMDetection 3.3
  CUDA-development image. Its config retains the inspected ResNet-50/FPN/Mask R-CNN graph and
  preprocessing values; checkpoint loading is strict and output conversion
  retains the original mask-to-quad operation.
- `RUN_DETECTION_GPU.ps1` first executes CI-01 Detection and writes a detailed
  original-PKL comparison, then expands to 15 cases, feeds those Detection
  regions to the existing Modern Recognition runner, and invokes the bundled
  AI-Hub evaluator without changing the CPU reference artifacts.

## Modern Detection and full OCR result

The user-run `RUN_DETECTION_GPU.ps1` completed Modern Detection and Modern
Recognition over all 15 prepared Validation documents, followed by the bundled
AI-Hub evaluator. The aggregate result and artifact inventory are recorded in
`MODERN_DETECTION_E2E_RESULT.md`.

## Recorded Modern Recognition result

The user-run `RUN_GPU.ps1` completed the Modern Recognition stage over the
prepared CI/PL/B-L 15-document smoke set. Artifact inspection confirms:

- device: `cuda`, capability `8.9` (RTX4050)
- `num_class`: 370 for every case
- checkpoint/load exceptions: 0
- recognition exceptions: 0
- regions: 1,786 total
- ordered bbox/text changes against the CPU reference TXT: 0
- parity: 15/15 PASS
- empty recognized text records: 2 (preserved as output data, not treated as an exception)

This is a Modern runtime parity result using the **AI-Hub original weights/code
CPU reference baseline** as the comparison reference. It is not an official
AI-Hub GPU score.

## Original Detection reference audit

The original image was not run for this audit. A stopped container was created
only to copy required files, then removed. The complete hash inventory is in
`runtime/modern_gpu/original_detection_reference_manifest.md`.

- extracted inventory: 927 files, 571,718,337 bytes;
- original config, `run_transit.sh`, `detection_model.py`, complete
  `new_detection` source tree, and bundled official evaluator: present;
- original Detection checkpoint and metadata: present;
- CPU golden Detection PKL/TXT and Validation GT for all 15 prepared cases:
  present;
- original image ID: `sha256:92f191e8b5f2c58f2f326b72facab2c6eef56e7ac9e15a26f549957c97d302a8`;
- Docker unique size: 260.4GB; Modern Recognition unique size: 10.12GB;
- build cache, containers, and volumes: 0B.

For Modern Detection implementation, 15-case parity, and the bundled
evaluator, the original image is no longer a runtime dependency once the
isolated Detection image is built externally (YES). The evaluator requires
`Polygon3`; a real import test showed that the existing Modern runtime lacks
it and cannot build it without a compiler. `Polygon3` is therefore included
in the isolated CUDA-development Detection image. The original image remains
preserved as the exact-environment reproducibility artifact, so deleting it is
not considered safe (NO).

The current C: free space is 18.58GB. The Detection runner now blocks before
Docker build when free space is below 30GB. A parity-preserving build must use
separate Docker storage or another GPU machine; `mmcv-lite`, CPU-only ops,
non-strict loading, and torchvision substitutions are not accepted.

The final deletion-readiness record is
`runtime/modern_gpu/ORIGINAL_DOCKER_DELETION_READINESS.md`. It documents the
static recursive import audit, checkpoint key/shape correspondence, manifest
hash match, the 15 PKL/GT/golden-output counts, and Azure
`stfintradevkrc/fintra/model/AI모델.zip` as the source-of-truth recovery archive.
