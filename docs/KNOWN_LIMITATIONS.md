# Known limitations

- The Modern OCR runtime remains an external execution boundary; this package
  does not alter or reimplement the validated model.
- The command adapter requires an explicit caller-supplied command template.
  It does not guess a Docker command or model path.
- Extraction is deterministic and conservative, not a learned field model.
- Table extraction currently recognizes an explicit `ITEM:` row format and the
  validation MVP compares the first comparable item.
- Date normalization refuses ambiguous day/month inputs.
- Company and currency normalization support conservative aliases only.
- No accounting corpus is bundled in this workstream. RAG/LLM integration is
  therefore a downstream dependency and must use the documented contract.
- No frontend or persistence implementation is included here.
- Synthetic tests are interface tests, not a replacement for the real
  AI-Hub 15-document OCR evaluation already recorded in the migration reports.
