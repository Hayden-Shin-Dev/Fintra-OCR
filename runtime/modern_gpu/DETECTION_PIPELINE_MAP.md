# Original Detection pipeline map

This map records the actual loaded AI-Hub source/config, not a reconstructed
README description.

## Entry and model

```text
transit_config.py
  model.type = OCRMaskRCNN
  backbone = mmdet.ResNet depth=50, out_indices=(0,1,2,3)
  neck = mmdet.FPN, out_channels=256, num_outs=5
  rpn_head = RPNHead, 5 anchor ratios, strides 4/8/16/32/64
  roi_head = StandardRoIHead
    bbox extractor = RoIAlign 7x7
    bbox head = Shared2FCBBoxHead, num_classes=1
    mask extractor = RoIAlign 14x14
    mask head = FCNMaskHead, 4 convs, one class
```

Original environment observed in the Docker image:

- Python 3.7.11
- PyTorch 1.7.1
- CUDA 10.1 build
- MMCV 1.4.3
- MMDetection 2.20.0
- MMOCR 0.4.1+
- checkpoint `/workspace/model_store/transit_detection_model.pth`

Checkpoint inspection (read-only, before modernization):

- top-level keys: `meta`, `optimizer`, `state_dict`
- `state_dict`: 360 tensors; the key namespace is the standard MMDetection
  ResNet/FPN/RPN/ROI-head namespace
- representative shapes: RPN conv `(256,256,3,3)`, RPN class `(5,256,1,1)`,
  RPN regression `(20,256,1,1)`, bbox classifier `(2,1024)`, bbox regressor
  `(4,1024)`, shared FC `(1024,12544)` then `(1024,1024)`, mask head four
  `(256,256,3,3)` convolutions and one-class mask logits `(1,256,1,1)`
- the Modern runner uses `strict=True`; missing, unexpected, or shape-mismatch
  keys fail the run. The original checkpoint is never rewritten or converted.

## Test image path

The original test entrypoint builds `cfg.data.test`, loads `IcdarDataset`,
and applies:

```text
LoadImageFromFile(color_type=color_ignore_orientation)
MultiScaleFlipAug(img_scale=(1920,1920), flip=False)
  Resize(keep_ratio=True)
  RandomFlip()
  Normalize(mean=[123.675,116.28,103.53],
            std=[58.395,57.12,57.375], to_rgb=True)
  ImageToTensor(keys=['img'])
  Collect(keys=['img'])
```

For the Modern one-image runner, `LoadImageFromFile`, `Resize`, and
`PackDetInputs` are retained and normalization is delegated to the modern
`DetDataPreprocessor` with the same values and BGR-to-RGB conversion.

## Output conversion

The custom `OCRMaskRCNN.simple_test` calls `get_boundary`. The observed
conversion is:

1. Take each predicted binary mask and find foreground coordinates.
2. Convert `(row, column)` to `(x, y)` points.
3. Run `cv2.minAreaRect` and `cv2.boxPoints` for `text_repr_type='quad'`.
4. Append the detector score.
5. The combined OCR wrapper keeps only `score > 0.2`.
6. It integer-casts the first eight coordinates before crop generation.

Modern Detection uses the standard current MaskRCNN graph and implements this
custom mask-to-quad conversion in `modern_detection.py`; it does not silently
replace the graph with a text detector or another OCR model.

## Modernization strategy

Selected strategy: **A-compatible graph attempt with an explicit strict-load
gate**. The current MMDetection graph is declared with the inspected original
architecture and exact model/test values. This is the smallest route that can
prove whether the checkpoint is directly loadable; if strict loading fails,
the run stops and a separately reviewed conversion/port is required. No
non-strict loading, key dropping, checkpoint conversion, or architecture
substitution is hidden in the runner.

The only intended output-side adaptation is the original OCRMaskRCNN
mask-to-quad conversion, because the Modern graph returns standard mask
instances rather than the original custom `boundary_result` wrapper. Detection
parity records candidate counts, score-threshold counts, one-to-one IoU
matches, coordinate differences, and score differences; equal counts alone do
not constitute parity.
