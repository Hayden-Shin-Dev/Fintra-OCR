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
