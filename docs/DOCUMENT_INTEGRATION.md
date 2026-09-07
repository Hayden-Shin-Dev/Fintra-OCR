# Single-document integration

The backend-facing boundary is `fintra.services.document_service.extract_document`.
It accepts a document file, a supported document type, and a configured
`OCRAdapter`, then returns `fintra-document-contract.v1` JSON. The returned
`document` object is the evidence-bearing canonical schema; extracted fields
retain status, source text, bounding box, and confidence. OCR runtime metadata
is under `ocr`.

The backend does not import document-specific resolver functions. It only
chooses the document type and supplies an adapter. The validated OCR command
can be configured with `CommandOCRAdapter`; a JSON fixture can be used for
integration tests with `FixtureOCRAdapter`.

Example:

```powershell
python scripts/run_document_extraction.py `
  --document C:\data\invoice.png `
  --document-type "Commercial Invoice" `
  --ocr-command 'python run_ocr.py --image {document_path} --type "{document_type}" --output {output_json}' `
  --output artifacts\integration\invoice.json `
  --pretty
```

The command template must explicitly produce the OCR JSON path supplied as
`{output_json}`. The service does not select or replace an OCR model.

The service dispatches to the clean production entry point
`fintra.extraction.production.EXTRACTORS`. Backend code does not import the
historical extractor modules.

## Direct validated Paddle runtime

The validated Paddle runtime can be selected explicitly for local MVP use:

```powershell
python scripts/run_document_extraction.py `
  --document C:\data\invoice.png `
  --document-type "Commercial Invoice" `
  --paddle `
  --paddle-device gpu `
  --paddle-mode accurate `
  --output artifacts\integration\invoice.json `
  --pretty
```

Run this command from the project root inside the already validated Paddle
environment. Use `--paddle-device cpu` only for a CPU smoke test. The command
returns the same `fintra-document-contract.v1` shape as a configured adapter;
the `ocr.regions` array carries the text, polygon, confidence, and page used
as evidence by the canonical fields.

## Local review UI

Install the UI-only dependencies into the validated Paddle environment:

```powershell
python -m pip install -r requirements-ui.txt
streamlit run app.py -- --device gpu --mode accurate
```

The UI accepts one document image and one of the three supported document
types. It calls `extract_document` directly, supports selected/all evidence
boxes and a raw OCR expander, and shows the canonical JSON. Backend code does
not need to import or modify the document-specific extractors. See
`docs/LOCAL_TEST_UI_GUIDE.md` for the exact command.
