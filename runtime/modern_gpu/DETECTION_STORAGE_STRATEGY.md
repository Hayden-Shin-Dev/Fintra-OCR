# Modern Detection storage strategy

## Current finding

The original image is retained locally because it is the exact AI-Hub
environment and remains a reproducibility artifact. The current C: free space
is below the safe build threshold, so the Detection Dockerfile must not be
started on this disk.

Docker currently reports no build cache, containers, or volumes. The remaining
image usage is intentional:

| Image | Docker image size | Unique size | Decision |
|---|---:|---:|---|
| `cognet9-aihub-train-release:v1.2` | 260GB | 260.4GB | preserve |
| `fintra-modern-gpu:torch260-cu124` | 10.1GB | 10.12GB | preserve |

The unique sizes come from `docker system df -v`; the `docker image ls` size is
not treated as a reclaimable-space claim. Both images currently have zero
containers and zero shared layers. Deleting either would release approximately
its unique size, but deletion is not authorized in this migration.

## Feasibility without the original Docker image

The Modern Detection implementation no longer needs to execute the original
container for its reference comparison. The hash inventory in
`original_detection_reference_manifest.md` records the preserved:

- original transit config and entrypoint;
- original Detection-to-Recognition wrapper;
- complete `new_detection` source tree, including custom `OCRMaskRCNN`,
  mask-to-quad code, dataset/pipeline code, and test entrypoint;
- bundled official evaluator source;
- original Detection checkpoint and metadata;
- all 15 CPU Detection PKLs, original OCR TXT files, and Validation GT files.

For the current Modern Migration scope, implementation, 15-case original-PKL
parity comparison, and the bundled official evaluator can proceed without
starting the original Docker container again once the isolated Modern
Detection image is built externally: **YES**. The evaluator's `Polygon3`
dependency is now included in that CUDA-development image. It cannot be
installed in the existing Modern runtime image without a compiler. The
original image remains preserved because it is the exact-environment artifact;
deleting it is therefore not considered safe: **NO**.

The final pre-delete audit is recorded in
`ORIGINAL_DOCKER_DELETION_READINESS.md`. It confirms the reference-complete
answer is **YES** for externally built Modern Detection implementation/parity/
evaluation, while retaining the operational recommendation to delete the
original image only after the user explicitly accepts loss of the local exact
environment. The Azure `stfintradevkrc/fintra/model/AI모델.zip` archive remains
the source-of-truth recovery artifact.

## Build decision for the current disk

There is no verified parity-preserving local build strategy within 18.58GB.
MMCV CUDA operators require a CUDA development toolchain or a compatible
prebuilt wheel. The failed source build already demonstrated substantial
temporary layers. A smaller final image does not remove that peak build-space
requirement. `mmcv-lite`, CPU-only ops, torchvision substitutions, non-strict
loading, or a different detector would change inference semantics and are
rejected.

The safe strategy is to build/run the isolated Modern Detection image in a
separately provisioned Docker storage location or on another GPU machine,
while bind-mounting this project's reference and checkpoint artifacts. The
local runner fail-fast blocks a Detection build below 30GB free so C: cannot
be exhausted again.
