# Production extractor architecture

`fintra.services.document_service.extract_document` is the backend boundary.
It runs the configured OCR adapter once and dispatches the resulting
`OCRResult` to `fintra.extraction.production.EXTRACTORS`.

The production call graph is:

```text
OCRResult
  -> normalized Layout / semantic anchors
  -> party and table candidate generation
  -> typed candidate validation and ranking
  -> canonical document fields
  -> source_text / bbox / confidence evidence
```

The production module delegates to the normalized layout strategy and never
imports or calls the historical fixed-template extractors, typed refinement,
or ordered refinement. Those modules remain available only for comparison
probes and historical regression analysis.

Every extracted canonical field keeps its source OCR text and bounding box.
`fintra.extraction.production.candidates_for` exposes a uniform
`FieldCandidate` view with normalized geometry and OCR region identifiers for
diagnostics without changing the v1 canonical JSON contract.

Primary production constraints:

- no case/document/value-specific rules;
- normalized page geometry is the primary coordinate system;
- label-relative and row/column relationships outrank global ordinal order;
- typed values are rejected when their type does not match the field;
- ambiguous or absent evidence is preserved as `ambiguous`/`missing`;
- OCR output and Gold are read-only inputs.
