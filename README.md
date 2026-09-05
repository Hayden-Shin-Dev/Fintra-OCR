# Fintra OCR V2

Fintra (Finance + Trace) is an evidence-first transaction review application.
This branch owns the validated AI-Hub Modern OCR integration boundary,
document field extraction, canonical schema, normalization, and deterministic
cross-document validation.

## Current status

The AI-Hub Modern Detection -> Recognition pipeline was executed on 15 prepared
Validation documents and evaluated with the bundled evaluator. See
`MODERN_DETECTION_E2E_RESULT.md` for the recorded metrics and local artifact
paths. This is a Modern runtime result, not a claim of an official AI-Hub GPU
baseline.

The application layer is implemented in `fintra/`:

- `fintra/ocr` - raw OCR adapter and output preservation;
- `fintra/extraction` - Commercial Invoice, Packing List, and B/L extractors;
- `fintra/domain` - evidence-bearing canonical schema;
- `fintra/normalization` - conservative value normalization;
- `fintra/validation` - ledger and cross-document findings;
- `fintra/services` - `TransactionReview` integration contract.

Frontend/UI, RAG retrieval, LLM provider integration, and persistence are
outside this workstream. Their input boundary is documented in
`docs/INTEGRATION_CONTRACT.md`.

## Setup and tests

Python 3.10+ is supported. The core package has no mandatory third-party
dependency.

```powershell
python -m unittest discover -s tests -v
```

Optional API/retrieval dependencies are declared in `pyproject.toml` for the
teams that own those components. No model, checkpoint, raw dataset, Docker
archive, generated OCR artifact, or secret belongs in Git.

## Documentation

- `docs/ARCHITECTURE.md` - ownership and evidence flow;
- `docs/DATA_FLOW.md` - adapter to review contract flow;
- `docs/FIELD_SCHEMA.md` - canonical field definitions;
- `docs/VALIDATION_RULES.md` - deterministic rules and status semantics;
- `docs/INTEGRATION_CONTRACT.md` - downstream service contract;
- `docs/KNOWN_LIMITATIONS.md` - current limitations;
- `docs/TESTING.md` - test commands and scope.

Work only on `restart/clean-v2`; do not merge or push to `main`.
