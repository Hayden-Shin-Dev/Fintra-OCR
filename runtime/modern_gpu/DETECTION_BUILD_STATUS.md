# Modern Detection image build record

Status: **PASS**

- Image: `fintra-modern-detection:torch260-cu124-mmdet330`
- Base CUDA image: `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel`
- Installed: `mmengine==0.10.7`, `mmcv==2.1.0`, `mmdet==3.3.0`
- CUDA compile target: `TORCH_CUDA_ARCH_LIST=8.9` for RTX 4050
- Build parallelism: `MAX_JOBS=1`, `CMAKE_BUILD_PARALLEL_LEVEL=1`, `NINJAFLAGS=-j1`
- OpenCV runtime libraries: `libxcb1`, `libglib2.0-0`, `libgl1`, `libx11-6`,
  `libxext6`, `libxrender1`

The image export and unpack completed successfully. The build did not run
Detection inference; GPU execution remains the next stage.

## Resolved build issues

1. MMCV source build failed with an empty CUDA architecture list. Fixed by
   explicitly compiling for `sm_89`.
2. Detection startup failed at `import cv2` because `libxcb.so.1` was absent.
   Fixed with a separate runtime-library layer so the successful MMCV build
   layer remains reusable.
3. The Dockerfile keeps the original AI-Hub image and the Modern Recognition
   image unchanged.
