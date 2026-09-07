# Extractor v2 UI

`extractor_v2_app.py` is a separate Streamlit inspection UI for the frozen
production Paddle OCR backend and the independent Audit Field Schema v2
contract.

It does not modify `app.py`, the production dispatch, OCR configuration, OCR
models, OCR caches, Gold, or the evaluator.

## Run

From the repository root, inside the already validated Paddle environment:

```powershell
streamlit run .\extractor_v2_app.py -- --device gpu --mode accurate
```

Use `--device cpu` only for a local smoke test. `accurate` and `fast` select
the same production Paddle backend modes used elsewhere; the UI does not
implement a second OCR path.

## UI contract

- Structured Fields v2 renders every applicable document slot for CI, Packing
  List, and B/L, including `None` and `missing` values.
- Each field displays value, validation marker, extraction status, source
  label, source text, semantic relation, confidence, and bbox.
- Item rows are shown in a separate table with every item schema column.
- OCR Detected Text is shown separately from structured fields with text,
  confidence, polygon/bbox, and page.
- Uploads without a reference are marked `?` (unverified). A reference JSON
  can be supplied with `--reference-json` for an inspection case; it is never
  used to change extraction.

## Contract artifacts

The 72-field inventory and output wiring are audited by:

```powershell
python .\scripts\audit_schema_v2_contract.py
```

The report is written to
`artifacts/fintra/schema-v2/schema_contract_audit.json` and
`artifacts/fintra/schema-v2/SCHEMA_V2_CONTRACT_AUDIT.md`.
