# MVP unsupported-field product acceptance

`MVP_DEVELOPMENT_GOLD_V4` is a development benchmark, not a semantic-complete
annotation of every canonical field. A field with `ambiguous_gt` is excluded
from accuracy denominators; it is not silently counted as a zero or as a
correct prediction.

## Benchmark-supported families

- Commercial Invoice: `seller`, `buyer`, and item `description`, `quantity`,
  `unit`, `unit_price`, `amount`.
- Packing List: `exporter`, `consignee`, and item `description`, `quantity`,
  `unit`.
- B/L: `shipper`, `consignee`, and `notify_party`.

These are the field families with available v4 Gold rows in the development
sets. Their per-field counts are in the frozen regression JSON files.

## Unsupported by this MVP Gold benchmark

Commercial Invoice `invoice_number`, `invoice_date`, `currency`, and
`total_amount`; Packing List `packing_list_number`, `date`, `package_count`,
`gross_weight`, `net_weight`, and `weight_unit`; and B/L `bl_number`, `vessel`,
`port_of_loading`, `port_of_discharge`, `shipment_date`, `on_board_date`,
`package_count`, `gross_weight`, `weight_unit`, and `goods_description` remain
`ambiguous_gt` where v4 has no reviewed available value. The production JSON
still exposes the canonical keys and evidence status for these fields, but no
accuracy claim is made for them from this benchmark.

## Manual acceptance

The product smoke uses one frozen development image/OCR fixture per document
type and checks that the service returns `fintra-document-contract.v1`, keeps
OCR regions, and emits all canonical document keys. It does not turn an
unsupported Gold field into an evaluated field.

Smoke outputs:

- `artifacts/fintra/product-smoke-dev/ci-canonical.json`
- `artifacts/fintra/product-smoke-dev/pl-canonical.json`
- `artifacts/fintra/product-smoke-dev/bl-canonical.json`

The acceptance is an interface/readiness check, not a claim that unsupported
fields are accurate.
