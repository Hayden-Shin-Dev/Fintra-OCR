"""Audit Field Schema v2 field specifications.

The aliases are semantic labels, not document-instance values.  They are
shared by candidate generation for all document layouts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    aliases: tuple[str, ...]
    kind: str


def _spec(aliases: tuple[str, ...], kind: str) -> FieldSpec:
    return FieldSpec(aliases, kind)


SPECS = {
    "invoice_number": _spec(("INVOICE NO", "INVOICE NUMBER", "INV NO", "INV NUMBER", "INVOICE #"), "identifier"),
    "invoice_date": _spec(("INVOICE DATE", "DATE OF INVOICE", "INVOICE NO AND DATE"), "date"),
    "seller": _spec(("SELLER", "SELLER NAME", "SOLD BY", "FROM"), "party"),
    "buyer": _spec(("BUYER", "SOLD TO", "BILL TO", "BUYER IF OTHER THAN CONSIGNEE"), "party"),
    "consignee": _spec(("CONSIGNEE", "CONSIGNED TO", "SHIP TO"), "party"),
    "exporter": _spec(("EXPORTER", "SHIPPER/EXPORTER", "EXPORTED BY"), "party"),
    "shipper": _spec(("SHIPPER", "CONSIGNOR", "CONSIGNOR/SHIPPER"), "party"),
    "notify_party": _spec(("NOTIFY PARTY", "ALSO NOTIFY", "NOTIFY"), "party"),
    "lc_number": _spec(("L/C NO", "LC NO", "LETTER OF CREDIT NO", "L/C NUMBER"), "identifier"),
    "lc_date": _spec(("L/C DATE", "LC DATE", "LETTER OF CREDIT DATE"), "date"),
    "bl_number": _spec(("BILL OF LADING NO", "BILL OF LADING NUMBER", "B/L NO", "B/L NUMBER", "BL NO"), "identifier"),
    "purchase_order_number": _spec(("PURCHASE ORDER", "PURCHASE ORDER NO", "P/O NO", "PO NO"), "identifier"),
    "po_number": _spec(("PO NUMBER", "P/O NUMBER", "PURCHASE ORDER NO", "PO NO"), "identifier"),
    "invoice_reference": _spec(("INVOICE REF", "INVOICE REFERENCE", "RELATED INVOICE", "INVOICE NO"), "identifier"),
    "document_number": _spec(("DOCUMENT NO", "DOCUMENT NUMBER", "DOC NO", "PACKING LIST NO", "PACKING LIST NUMBER"), "identifier"),
    "flight_number": _spec(("FLIGHT NO", "FLIGHT NUMBER"), "identifier"),
    "contract_number": _spec(("CONTRACT NO", "CONTRACT NUMBER"), "identifier"),
    "reference_number": _spec(("REFERENCE NO", "REFERENCE NUMBER", "OTHER REFERENCE", "REF NO"), "identifier"),
    "booking_number": _spec(("BOOKING NO", "BOOKING NUMBER"), "identifier"),
    "part_number": _spec(("PART NUMBER", "PART NO", "PART#"), "identifier"),
    "sku": _spec(("SKU",), "identifier"),
    "document_date": _spec(("DOCUMENT DATE", "DATE OF DOCUMENT", "PACKING LIST DATE"), "date"),
    "currency": _spec(("CURRENCY", "CURRENCY CODE", "AMOUNT IN"), "currency"),
    "total_amount": _spec(("TOTAL AMOUNT", "INVOICE TOTAL", "GRAND TOTAL", "TOTAL"), "amount"),
    "payment_terms": _spec(("PAYMENT TERMS", "TERMS OF PAYMENT"), "text"),
    "incoterm": _spec(("INCOTERM", "TERMS OF DELIVERY", "DELIVERY TERMS"), "code"),
    "vessel": _spec(("VESSEL", "VESSEL/VOY", "VESSEL / VOY", "EXPORT CARRIER"), "vessel"),
    "voyage_number": _spec(("VOYAGE", "VOY", "VOY NO", "VOYAGE NO", "VESSEL/VOY"), "identifier"),
    "departure_date": _spec(("DATE OF DEPARTURE", "DEPARTURE DATE", "ETD"), "date"),
    "shipment_date": _spec(("SHIPMENT DATE", "ON BOARD DATE", "SHIPPED ON BOARD", "DATE OF SHIPMENT"), "date"),
    "arrival_date": _spec(("DATE OF ARRIVAL", "ARRIVAL DATE", "ETA"), "date"),
    "port_of_loading": _spec(("PORT OF LOADING", "PLACE OF LOADING", "LOADING PORT"), "location"),
    "port_of_discharge": _spec(("PORT OF DISCHARGE", "PLACE OF DISCHARGE", "DISCHARGE PORT"), "location"),
    "place_of_receipt": _spec(("PLACE OF RECEIPT", "RECEIPT PLACE"), "location"),
    "place_of_delivery": _spec(("PLACE OF DELIVERY", "DELIVERY PLACE"), "location"),
    "final_destination": _spec(("FINAL DESTINATION", "DESTINATION"), "location"),
    "container_number": _spec(("CONTAINER NO", "CONTAINER NUMBER", "CONTAINER"), "identifier"),
    "seal_number": _spec(("SEAL NO", "SEAL NUMBER", "SEAL"), "identifier"),
    "package_count": _spec(("PACKAGE COUNT", "NO OF PACKAGES", "NUMBER OF PACKAGES", "PACKAGES", "PACKAGE"), "quantity"),
    "package_type": _spec(("PACKAGE TYPE", "KIND OF PACKAGES", "PACKING TYPE"), "text"),
    "carton_count": _spec(("CARTON COUNT", "NO OF CARTONS", "CARTONS", "CARTON"), "quantity"),
    "pallet_count": _spec(("PALLET COUNT", "NO OF PALLETS", "PALLETS", "PALLET"), "quantity"),
    "gross_weight": _spec(("GROSS WEIGHT", "GROSS WT", "G.W.", "G/W"), "weight"),
    "net_weight": _spec(("NET WEIGHT", "NET WT", "N.W.", "N/W"), "weight"),
    "weight_unit": _spec(("WEIGHT UNIT", "UNIT OF WEIGHT"), "unit"),
    "measurement": _spec(("MEASUREMENT", "MEASUREMENTS", "CUBIC METER", "CUBIC METERS"), "measurement"),
    "cbm": _spec(("CBM", "CUBIC METER", "CUBIC METERS"), "measurement"),
    "shipment_type": _spec(("SHIPMENT TYPE", "TYPE OF SHIPMENT"), "text"),
    "goods_description": _spec(("GOODS DESCRIPTION", "DESCRIPTION OF GOODS", "DESCRIPTION"), "text"),
    "description": _spec(("DESCRIPTION", "DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "ITEM DESCRIPTION", "COMMODITY", "PARTICULARS"), "text"),
    "hs_code": _spec(("HS CODE", "H.S. CODE", "HARMONIZED CODE", "HS NO"), "identifier"),
    "quantity": _spec(("QUANTITY", "QTY", "QUANTITIES"), "quantity"),
    "unit": _spec(("UNIT", "UOM", "UNITS"), "unit"),
    "unit_price": _spec(("UNIT PRICE", "UNIT COST", "PRICE/UNIT", "RATE"), "amount"),
    "amount": _spec(("LINE AMOUNT", "EXTENDED AMOUNT", "TOTAL PRICE", "AMOUNT", "VALUE"), "amount"),
    "line_number": _spec(("LINE NO", "LINE NUMBER", "ITEM NO", "NO", "NO."), "quantity"),
    "product_code": _spec(("PRODUCT CODE", "ITEM CODE", "PRODUCT NO"), "identifier"),
    "shipping_mark": _spec(("SHIPPING MARK", "SHIPPING MARKS", "MARKS & NOS", "MARKS AND NUMBERS"), "text"),
    "country_of_origin": _spec(("COUNTRY OF ORIGIN", "ORIGIN COUNTRY"), "location"),
    "country_of_destination": _spec(("COUNTRY OF DESTINATION", "DESTINATION COUNTRY"), "location"),
    "carrier": _spec(("CARRIER", "EXPORT CARRIER", "FORWARDER"), "party"),
    "bank": _spec(("BANK", "ISSUING BANK", "ADVISING BANK"), "party"),
    "manufacturer": _spec(("MANUFACTURER", "MADE BY"), "party"),
    "signatory_company": _spec(("AUTHORIZED SIGNATURE", "SIGNATURE", "SIGNED BY"), "party"),
    "delivery_terms": _spec(("DELIVERY TERMS", "TERMS OF DELIVERY"), "text"),
    "method_of_dispatch": _spec(("METHOD OF DISPATCH", "MODE OF TRANSPORT", "TRANSPORT MODE"), "text"),
    "freight": _spec(("FREIGHT", "FREIGHT CHARGE"), "amount"),
    "insurance": _spec(("INSURANCE", "INSURANCE CHARGE"), "amount"),
    "tax": _spec(("TAX", "VAT", "TAX AMOUNT"), "amount"),
    "discount": _spec(("DISCOUNT", "DISCOUNT AMOUNT"), "amount"),
    "subtotal": _spec(("SUBTOTAL", "SUB TOTAL"), "amount"),
    "other_charges": _spec(("OTHER CHARGES", "ADDITIONAL CHARGES"), "amount"),
}


# These are derived from the checked-in ``field_schema_v2.json`` artifact.
# The artifact is the source of truth for the 72-field inventory.  Fields
# marked NOT_APPLICABLE in that artifact are intentionally not emitted for
# that document type; nullable applicable slots are always emitted.
DOCUMENT_FIELDS = {
    "Commercial Invoice": (
        "arrival_date", "bank", "buyer", "carrier", "consignee",
        "contract_number", "country_of_destination", "country_of_origin",
        "currency", "delivery_terms", "departure_date", "discount",
        "document_date", "document_number", "final_destination",
        "flight_number", "freight", "gross_weight", "incoterm",
        "insurance", "invoice_date", "invoice_number", "lc_date", "lc_number",
        "manufacturer", "method_of_dispatch", "other_charges", "package_count",
        "payment_terms", "port_of_discharge", "port_of_loading",
        "purchase_order_number", "reference_number", "seller",
        "signatory_company", "subtotal", "tax", "total_amount", "vessel",
        "voyage_number",
    ),
    "Packing List": (
        "arrival_date", "buyer", "carrier", "carton_count", "cbm", "consignee",
        "container_number", "contract_number", "country_of_destination",
        "country_of_origin", "departure_date", "document_date", "document_number",
        "exporter", "final_destination", "flight_number", "gross_weight",
        "incoterm", "invoice_reference", "manufacturer", "measurement",
        "method_of_dispatch", "net_weight", "package_count", "package_type",
        "pallet_count", "port_of_discharge", "port_of_loading",
        "purchase_order_number", "reference_number", "seal_number",
        "shipment_type", "signatory_company", "vessel", "voyage_number",
        "weight_unit",
    ),
    "B/L": (
        "arrival_date", "bl_number", "booking_number", "carrier", "carton_count",
        "cbm", "consignee", "container_number", "contract_number",
        "country_of_destination", "country_of_origin", "departure_date",
        "document_date", "document_number", "final_destination", "flight_number",
        "gross_weight", "incoterm", "invoice_reference", "measurement",
        "method_of_dispatch", "net_weight", "notify_party", "package_count",
        "package_type", "pallet_count", "place_of_delivery", "place_of_receipt",
        "port_of_discharge", "port_of_loading", "reference_number", "seal_number",
        "shipment_date", "shipment_type", "shipper", "signatory_company", "vessel",
        "voyage_number", "weight_unit",
    ),
}

ITEM_FIELDS = {
    "Commercial Invoice": (
        "amount", "description", "hs_code", "line_number", "part_number",
        "po_number", "product_code", "quantity", "shipping_mark", "sku", "unit",
        "unit_price",
    ),
    "Packing List": (
        "description", "hs_code", "line_number", "part_number", "po_number",
        "product_code", "quantity", "shipping_mark", "sku", "unit",
    ),
    "B/L": ("goods_description", "shipping_mark"),
}

# The two names below were present in the earlier v2 compatibility payload
# but are not part of the 72-field artifact.  Keep their nullable slots so
# callers of the initial v2 preview do not break while the audited inventory
# remains exact and separately countable.
COMPATIBILITY_DOCUMENT_FIELDS = {
    "Packing List": ("packing_list_number", "date"),
}

# Every field in the audited contract is routed through a resolver.  This is
# intentionally derived from the contract inventory rather than a hand-held
# benchmark allowlist: adding a schema field must not silently leave it
# permanently nullable.  The old name remains as a compatibility alias for
# callers written against the first v2 preview.
RESOLUTION_DOCUMENT_FIELDS = DOCUMENT_FIELDS

PARTY_FIELDS = {"seller", "buyer", "consignee", "exporter", "shipper", "notify_party", "carrier", "bank", "manufacturer", "signatory_company"}

PARTY_FIELDS_BY_DOCUMENT = {
    "Commercial Invoice": ("seller", "buyer", "consignee"),
    "Packing List": ("exporter", "shipper", "buyer", "consignee"),
    "B/L": ("shipper", "consignee", "notify_party"),
}

TABLE_FIELDS_BY_DOCUMENT = ITEM_FIELDS
FIELD_FAMILY = {
    name: ("party" if name in PARTY_FIELDS else "table" if name in {
        item for fields in ITEM_FIELDS.values() for item in fields
    } else "scalar")
    for name in SPECS
}


__all__ = [
    "COMPATIBILITY_DOCUMENT_FIELDS",
    "DOCUMENT_FIELDS",
    "FIELD_SPEC",
    "FIELD_FAMILY",
    "ITEM_FIELDS",
    "PARTY_FIELDS",
    "PARTY_FIELDS_BY_DOCUMENT",
    "RESOLUTION_DOCUMENT_FIELDS",
    "SPECS",
    "TABLE_FIELDS_BY_DOCUMENT",
    "FieldSpec",
]

# Compatibility alias for callers that prefer the singular spelling.
FIELD_SPEC = SPECS
