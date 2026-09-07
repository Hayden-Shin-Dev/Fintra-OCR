# OCR-First V2

This branch starts the next Fintra document pipeline from OCR capture, not from canonical field extraction.

## Goal of this stage

Given one document image, preserve all OCR text evidence and make it easy to inspect visually before any semantic decision is made.

The OCR-only output stores both:

- `raw_regions`: every globalized region emitted by the full/tile/focus/focus-upscaled Paddle passes.
- `normalized_regions`: the existing conservative duplicate-suppressed OCR view.

No `invoice_number`, `buyer`, `currency`, `total_amount`, party role, label/value pair, table column, or other semantic field is assigned in this stage.

## Run the UI

Use the existing isolated Paddle environment.

```powershell
.\.venv-paddle-gpu\Scripts\python.exe -m streamlit run .\ocr_first_app.py -- --device gpu --mode accurate
```

The UI provides:

- image upload
- bbox overlay with region ids
- raw vs normalized OCR view
- confidence filtering
- full OCR region table
- OCR-only JSON
- JSON download

## Architecture boundary

```text
image
  -> Paddle OCR passes
  -> raw_regions (immutable evidence capture)
  -> normalized_regions (duplicate-suppressed view)
  -> [future] layout / reading order
  -> [future] label-value pairing
  -> [future] table structure
  -> [future] document-native semantics
  -> [future] audit projection
```

The frozen production extractor at `af3950f` is not called by this path.
