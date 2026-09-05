# Isolated Paddle reference runtime

This runtime is a separate comparison backend. It does not replace or modify
the validated Modern OCR runtime.

The versions below are the versions recorded and tested by the previous
Fintra project:

- Python 3.13
- `paddlepaddle==3.2.0`
- `paddleocr==3.7.0`
- PaddleX 3.7.2 (installed as a PaddleOCR dependency in the old project)
- models: `PP-OCRv6_medium_det` and `PP-OCRv6_medium_rec`

Create a dedicated virtual environment and install
`runtime/paddle/requirements-paddle.txt` there. Do not install these packages
into the Modern OCR environment. Paddle downloads model files on first use;
the model cache is external to this repository and must not be confused with
the AI-Hub original model archive.

The recovered backend preserves the old accurate-mode policy: one full-page
pass, overlapping 1280px tiles for large pages, three generic focus bands, a
1.75x retry for focus bands, and IoU/text based duplicate removal. Its only
new boundary is conversion to the V2 `OCRResult` / `OCRRegion` schema.

## Current 60-case benchmark

The runner uses the already prepared current Validation cases under
`artifacts/fintra/field_eval/cases`. It writes only to the separate
`artifacts/fintra/paddle_field_eval` tree and never overwrites Modern outputs.

Smoke test (one CI, one Packing List, one B/L):

```powershell
python .\scripts\run_paddle_field_eval.py --smoke --device cpu
```

Full same-benchmark run (CI20 / Packing20 / B/L20):

```powershell
python .\scripts\run_paddle_field_eval.py --device cpu
```

The actual Paddle model inference is intentionally not run as part of the
repository unit tests. Run it only in this isolated environment after the
smoke output is reviewed.
