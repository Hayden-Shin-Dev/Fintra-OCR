# AI-Hub original pipeline map

Observed from the loaded image `cognet9-aihub-train-release:v1.2`; this is a
map of what was actually inspected, not a README-derived assumption.

```text
transit_config.py
  -> new_detection/tools/test.py
  -> MMDetection 2.20.0 / MMCV 1.4.3
  -> OCRMaskRCNN checkpoint
  -> detection result PKL

detection_model.py (official combined wrapper)
  -> reads detection PKL via mmcv.load
  -> keeps boundary_result score > 0.2
  -> polygon = first 8 coordinates, integer cast
  -> Shapely polygon bounds
  -> image crop: [y_min:int(y_max+1.25), x_min:int(x_max+1.25)]
  -> temporary numbered PNG crops
  -> model_inference.prediction

model_inference.py
  -> RawDataset/natural sort
  -> PIL grayscale
  -> BICUBIC resize 224x224
  -> ToTensor
  -> ViTSTR Model forward, seqlen=25
  -> argmax over class dimension
  -> TokenLabelConverter.decode(preds[:, 1:])
  -> stop at [s], replace comma with `쉼표`
  -> official TXT: 8 coordinates + text
```

Important observed facts:

- The packaged `run_transit.sh` points to stale paths and is not used as the
  executable source of truth for the validated run.
- The validated checkpoint paths are `/workspace/model_store/`.
- `detection_model.py` hardcodes Ray GPU actors and `torch.device('cuda')`.
- `model_inference.py` independently selects CUDA when available; the Modern
  runner makes the device explicit while retaining the remaining operations.
- The official raw TXT does not contain recognition confidence. Modern output
  therefore does not invent a confidence value.

