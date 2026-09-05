# Validation rules

The deterministic rules currently implemented in
`fintra/validation/engine.py` are:

- ledger amount ↔ Commercial Invoice total;
- ledger counterparty ↔ invoice buyer;
- purchase counterparty ↔ invoice seller when ledger direction is purchase;
- first comparable invoice item quantity ↔ packing item quantity;
- Packing List gross weight ↔ B/L gross weight after supported unit conversion;
- Packing List package count ↔ B/L package count;
- Packing List consignee ↔ B/L consignee.
- ledger recognition date ↔ B/L shipment/on-board date when both are explicit.

Each finding includes rule ID, values, difference, severity, status, message,
and source evidence. The current item comparison is intentionally MVP-scoped:
it compares the first comparable item and does not claim full table alignment.

Status precedence:

`MISMATCH` > `REVIEW_REQUIRED` > `INCOMPLETE` > `PASS`.

Missing or unparseable evidence is `insufficient_evidence`, not `match`.
Ambiguous evidence is `review_required`. No rule confirms fraud or changes a
ledger entry.
