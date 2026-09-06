# AI-Hub Training TL → Fintra Gold integrity

This record covers Accurate75 #1 only. The FINAL-HOLDOUT #2 allowlist and its
images, labels, OCR outputs, and metrics are not inputs to this audit.

## Provenance

The original labels were read directly from the local AI-Hub Training TL ZIPs
under `artifacts/aihub/Training/02.원본라벨링데이터/` (the directory is located
dynamically by the audit script so it is not dependent on a console code page).
For all 75 Accurate75 #1 cases:

- the raw TL JSON, `artifacts/fintra/devscale1500/labels/*.json`, and
  `artifacts/fintra/train-scale-v1/cases/*/source_annotation.json` have equal
  parsed JSON content;
- token text and token geometry are equal;
- byte hashes differ because the downstream files were parsed and
  re-serialized.

Therefore `source_annotation.json` is a downstream copy of the TL content,
not the original AI-Hub label file and not a semantic field annotation.

## Gold limitation and confirmed defects

AI-Hub TL is word-level and does not contain Fintra fields such as
`port_of_loading` or `items[].description`. A valid token reference alone
cannot prove the semantic role, so unprovable rows are reported as
`CANNOT_VERIFY` rather than inferred from extractor predictions.

The direct audit found 23 confirmed mapping defects in the old Gold view:

- B/L port loading/discharge assignments were reversed for two paired source
  layouts (four field rows).
- Commercial Invoice descriptions crossed the typed HS/numeric column for
  repeated rows (18 field rows in this allowlist).
- One old description row contained a source numeric column token while a
  textual row remained to its left.

The audit also records six source-label ambiguity/inconsistency rows and 25
explicit not-applicable rows. The exact machine-readable counts are in
`artifacts/fintra/gold_audit/training-tl-gold-integrity/gold_integrity_metrics.json`.

## Reproducible commands

```powershell
python scripts/audit_training_tl_provenance.py
python scripts/audit_training_tl_gold_integrity.py
python scripts/build_semantic_v3_2_gold.py
python scripts/validate_semantic_v3_2_gold.py
```

The corrected candidate is written separately under
`artifacts/fintra/gold_audit/semantic-v3.2-accurate75/cases/`; semantic-v2,
semantic-v3, and semantic-v3.1 are not overwritten.

The existing extractor was re-evaluated without modification using:

```powershell
python scripts/evaluate_field_extraction.py `
  --cases artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1 `
  --output-dir artifacts/fintra/gold_audit/semantic-v3.2-accurate75-evaluation `
  --strategy active `
  --gold-source semantic-v3.2 `
  --gold-root artifacts/fintra/gold_audit/semantic-v3.2-accurate75/cases
```

This is a corrected-Gold candidate evaluation, not a final holdout score.
