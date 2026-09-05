# Original Docker deletion readiness — final pre-delete audit

Audit date: 2026-09-05. This is a read-only readiness record. No original
container was run, no Detection build/inference was run, and no Docker image
was deleted.

## A. Preserved reference

- Reference manifest: `original_detection_reference_manifest.md`
- Preserved files: **927**
- Preserved bytes: **571,718,337**
- Static recursive import audit: `original_detection_import_audit.md`
- Local Python files visited: **231**; import edges: **1,097**
- All repository-local imports resolved across the preserved Detection source,
  official evaluator, and vendored original Recognition source. The remaining
  unresolved names are standard-library or runtime dependencies such as
  PyTorch, MMCV/MMDetection, OpenCV, NumPy, Ray, Polygon3, and related packages.
- 15 original Detection PKLs, 15 original OCR TXT outputs, and 15 source GT
  JSON files are present under `artifacts/aihub/validation/smoke/`.
- Original Detection checkpoint: 351,297,471 bytes.
- Azure `stfintradevkrc/fintra/model/AI모델.zip` is retained as the user-provided
  source-of-truth archive for restoring the original Docker environment.

## B. Required asset audit

| Required item | Result | Evidence or limitation |
|---|---|---|
| OCRMaskRCNN | PASS | Preserved custom `mmocr/models/textdet/detectors/ocr_mask_rcnn.py` |
| Backbone/FPN/RPN/RoI/bbox/mask configuration | PASS | Preserved `transit_config.py` |
| Backbone/FPN/RPN/RoI/bbox/mask implementations | EXTERNAL RUNTIME | Standard MMDetection classes are imported from the runtime; custom MMDetection/MMOCR source is preserved |
| Custom losses/mask utilities | PASS | Preserved `new_detection/mmocr/core` |
| Custom dataset/pipeline components | PASS | Preserved `new_detection/mmocr/datasets` and transforms |
| Image preprocessing/normalization/resize/padding | PASS | Config and preserved pipeline source |
| Postprocessing/mask-to-quad | PASS | Preserved custom mask/inference utilities; Modern conversion is separately reviewed |
| Score/NMS | PASS | `test_cfg` in preserved config: score 0.1, NMS IoU 0.5; RPN NMS settings preserved |
| Inference entrypoint | PASS | Preserved `new_detection/tools/test.py` and `run_transit.sh` |
| Checkpoint and metadata | PASS | `.pth` plus `transit_detection_model_info.log` |
| Official evaluator | PASS | Preserved `evaluation_method` source and requirements |
| 15-document original Detection PKL | PASS | 15 files, 578,037 bytes |
| GT | PASS | 15 source GT JSON files and evaluator GT artifacts |
| Recognition golden reference | PASS | 15 original OCR TXT files; Modern Recognition parity is already recorded |

The recursive audit records standard dependencies such as PyTorch, MMCV and
MMDetection as external runtime dependencies. Their absence from the local
reference tree is not an unrecorded missing custom file.

## C. Checkpoint ↔ config static correspondence

Static `torch.load(..., map_location='cpu')` was used only to inspect the
checkpoint; no model was instantiated and no inference was executed.

- top-level keys: `meta`, `optimizer`, `state_dict`
- state_dict tensors: **360**
- RPN classification/regression: `[5,256,1,1]` / `[20,256,1,1]`, matching five
  configured anchor ratios
- bbox classification/regression: `[2,1024]` / `[4,1024]`, matching one
  foreground class and class-specific box regression
- shared bbox FC layers: `[1024,12544]` / `[1024,1024]`, matching 256×7×7 ROI
  features and the configured 1024 channels
- mask logits/upsample: `[1,256,1,1]` / `[256,256,2,2]`, matching one mask class
  and the configured mask head
- all static checks: **PASS**

Checkpoint SHA-256 actual and manifest:

`68aaa88026a1526e4ff97ee6e0a73416e7240a6cb1b362aee1a3d939cee6a2cf`

Hash match: **PASS**.

## D. Deletion decision

**Can Modern Detection implementation/parity/evaluation continue without the
local original image, with Azure able to restore it if needed? YES —
reference-complete and externally buildable.**

This does not mean the current C: drive can build the Detection image. C: has
only about 18.58GB free, while the parity-preserving CUDA/MMCV build has a
larger peak requirement. Build and execution must use separate Docker storage
or another GPU machine.

Current Docker metadata:

- original image: `cognet9-aihub-train-release:v1.2`
- image ID: `sha256:92f191e8b5f2c58f2f326b72facab2c6eef56e7ac9e15a26f549957c97d302a8`
- inspect size: 129,863,949,440 bytes
- Docker unique size: **260.4GB**
- containers/volumes/build cache: **0B**
- Modern Recognition image is not a deletion target.

From a technical reference-completeness perspective deletion is now
recoverable from the preserved files and Azure archive. From a reproducibility
and operational perspective, retain the image unless the user explicitly
chooses to reclaim its unique 260.4GB.

## E. One deletion command (not executed by Codex)

If the user accepts the above trade-off, the single original-image deletion
command is:

```powershell
docker image rm cognet9-aihub-train-release:v1.2
```

Do not delete `fintra-modern-gpu:torch260-cu124`.

## F. Space-recovery order after user deletion

1. Run the one deletion command above.
2. Check reclamation with `docker system df -v`; do not use
   `docker system prune -a --volumes`.
3. If build-cache entries remain, use the already approved narrow command
   `docker builder prune -af`, then check `docker system df -v` again.
4. Quit Docker Desktop completely, then run `wsl --shutdown`.
5. Compact only the Docker data VHDX that was previously identified:
   `C:\Users\shinm\AppData\Local\Docker\wsl\disk\docker_data.vhdx`.
   Do not compact or remove `main\ext4.vhdx`.

The VHDX compact operation is:

```powershell
$target = 'C:\Users\shinm\AppData\Local\Docker\wsl\disk\docker_data.vhdx'
@"
select vdisk file="$target"
compact vdisk
exit
"@ | diskpart
```
