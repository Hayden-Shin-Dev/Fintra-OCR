# Field schema

The canonical classes live in `fintra/domain/schema.py`.

## EvidenceField

| Field | Meaning |
|---|---|
| `value` | Extracted value, if available |
| `normalized_value` | Optional comparison value; never replaces raw value |
| `confidence` | OCR/extractor confidence when supplied |
| `source_text` | Original OCR region text |
| `bbox` | Source polygon |
| `page` | 1-based page number |
| `extraction_method` | Rule or adapter identifier |
| `status` | `extracted`, `ambiguous`, or `missing` |

Document classes are `CommercialInvoice`, `PackingList`, and `BillOfLading`.
Each includes `DocumentMetadata` and typed evidence fields. Line-item fields
use the same evidence structure.

## TransactionReview

`TransactionReview` contains the ledger transaction, the three optional
documents, validation findings, overall status, evidence summary, accounting
references, and an optional downstream AI review response. Its deterministic
status is not delegated to an LLM.
