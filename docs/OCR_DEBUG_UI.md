# OCR-only Debug UI

The OCR debug UI is deliberately separate from the production Fintra UI and
does not call the extractor, Gold, label/value pairing, table resolver, or
semantic candidate selection.

## Run

From the repository root, using the validated Paddle environment:

```powershell
.\.venv-paddle-gpu\Scripts\python.exe -m streamlit run .\ocr_debug_app.py -- --device gpu --mode accurate
```

For a CPU smoke test:

```powershell
.\.venv-paddle-gpu\Scripts\python.exe -m streamlit run .\ocr_debug_app.py -- --device cpu --mode fast
```

The UI accepts PNG, JPG/JPEG, BMP, and TIFF images. GPU/CPU and
accurate/fast are explicit controls; the default is GPU + accurate.

## What it shows

- uploaded image with OCR polygon overlay and region IDs;
- raw pass-preserving OCR regions and normalized duplicate-suppressed regions;
- image width/height, pass count, region counts, confidence filter, device,
  mode, and model names;
- region table with text, confidence, bbox, page, and source pass;
- reading-order OCR text and raw OCR JSON;
- downloadable OCR-only JSON (`fintra-ocr-capture.json`).

The JSON contains immutable `raw_regions` and a separate
`normalized_regions` view. Normalization is not allowed to overwrite raw
evidence. No canonical field such as `buyer`, `invoice_number`, or
`port_of_loading` is assigned in this path.

## Boundary

```text
image -> validated Paddle OCR -> raw_regions
                         \-> normalized_regions
```

`app.py` remains the document-extraction UI. `ocr_debug_app.py` is an
OCR-observability entrypoint only.
