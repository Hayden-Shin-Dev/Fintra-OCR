# Production extractor architecture

`fintra.services.document_service.extract_document` is the backend boundary.
The clean-room candidate is available at
`fintra.extraction.clean.engine.EXTRACTORS`; the backend dispatch remains on
the historical path until the three-set regression gate is closed.

The production call graph is:

```text
OCRResult
  -> normalized Layout / semantic anchors
  -> party and table candidate generation
  -> typed candidate validation and ranking
  -> canonical document fields
  -> source_text / bbox / confidence evidence
```

The clean candidate is standalone and never imports or calls the historical
fixed-template extractors, typed refinement, ordered refinement, or legacy
table resolver. Those modules remain available only for comparison probes and
historical regression analysis. It uses normalized geometry, semantic anchors,
typed candidates, and pre-selection ranking.

Every clean-candidate canonical field keeps its source OCR text and bounding
box. The clean party, scalar, and table resolvers construct `FieldCandidate`
objects before selecting the final `EvidenceField`; the legacy
`fintra.extraction.production` candidate view remains comparison-only.

Primary production constraints:

- no case/document/value-specific rules;
- normalized page geometry is the primary coordinate system;
- label-relative and row/column relationships outrank global ordinal order;
- typed values are rejected when their type does not match the field;
- ambiguous or absent evidence is preserved as `ambiguous`/`missing`;
- OCR output and Gold are read-only inputs.
