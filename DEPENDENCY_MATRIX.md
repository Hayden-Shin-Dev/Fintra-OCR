# Dependency matrix

Source: read-only inspection of `cognet9-aihub-train-release:v1.2` and the
actual files under `/workspace`.

| Area | Original runtime | Modern isolated target | Compatibility decision |
|---|---|---|---|
| Python | 3.7 | PyTorch 2.6 CUDA 12.4 base image | Separate image; never replace original |
| PyTorch | 1.7.1 (`torch-1.7` env) | 2.6.0 CUDA 12.4 | Required for RTX4050 `sm_89`; FP32 only |
| torchvision | 0.8.0a0 | Base-image compatible version | Used only for compatible tensor utilities |
| timm | 0.5.4 in original env | 0.5.4 pinned | Original ViTSTR imports `timm.models.registry`; do not blindly use current timm |
| Recognition model | Original local `Model` + ViTSTR small patch16 224 | Same vendored source | Strict checkpoint load required |
| Recognition preprocessing | PIL grayscale, BICUBIC 224x224, ToTensor; no [-1,1] scale for Transformer | Same | No preprocessing optimization |
| Recognition decoder | `TokenLabelConverter`, `preds[:,1:]`, greedy max, `[s]` termination | Same | No decoding change |
| Detection framework | MMDetection 2.20.0, MMCV 1.4.3 | Not installed in Modern image yet | Custom ops/config/checkpoint require a separate port study |
| Detection model | OCRMaskRCNN, custom `mmdet` modules | Not claimed migrated | No latest MMDetection substitution |
| NumPy | 1.x-era | `<2` | Prevents old source assumptions from changing |
| OpenCV | Original cv2 | Modern headless OpenCV | Only image read/crop; same crop coordinates |
| Geometry | Shapely + integer bounds | Shapely 2.x | Used for the original polygon bounds operation |

The source requirements also include augmentation-only packages (`wand`,
`scikit-image`, etc.). The Modern Recognition runner uses the original
evaluation branch directly and does not activate training augmentations.
