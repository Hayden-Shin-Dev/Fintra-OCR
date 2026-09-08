# OCR v2 isolated experiment

OCR v2 is an isolated benchmark implementation. It does not replace
`fintra/ocr/paddle_backend.py`, production dispatch, the extractor, Gold, or
existing OCR caches.

The model names and accurate pass geometry remain the current reference:

- `PP-OCRv6_medium_det`
- `PP-OCRv6_medium_rec`
- accurate detection side limit `1536`
- tile size `1280`, overlap `160`
- focus regions and `1.75x` focus upscale

The output contract keeps every parsed pass region in `raw_regions`. A
separate resolver creates `resolved_regions` using geometry overlap,
containment, normalized text similarity, confidence, text completeness, and
repeat agreement. Fragment merging is conservative and does not use field
names, case IDs, values, company names, or fixed document coordinates.

```text
image
  -> OCR v2 Paddle passes
  -> raw_regions (immutable artifact)
  -> duplicate grouping
  -> conservative fragment merge
  -> resolved_regions
  -> schema/extractor benchmark only after OCR output is written
```

Run one dataset into a new root:

```powershell
.\.venv-paddle-gpu\Scripts\python.exe .\scripts\run_ocr_v2.py `
  --dataset accurate75 --device gpu --mode accurate `
  --output-root .\artifacts\fintra\ocr-v2
```

Valid datasets are `accurate75`, `fast300`, and `v3_75`. The runner resolves
images from `artifacts/fintra/train-scale-v1/cases` and never writes to the
production cache roots.
