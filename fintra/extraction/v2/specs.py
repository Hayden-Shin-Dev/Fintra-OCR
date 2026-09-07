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
    "packing_list_number": _spec(("PACKING LIST NO", "PACKING LIST NUMBER", "PACKING NO", "DOCUMENT NO"), "identifier"),
    "document_date": _spec(("DOCUMENT DATE", "DATE OF DOCUMENT", "PACKING LIST DATE"), "date"),
    "date": _spec(("DATE", "DATE OF PACKING", "PACKING LIST DATE"), "date"),
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
    "gross_weight": _spec(("GROSS WEIGHT", "GROSS WT", "G.W.", "G/W"), "weight"),
    "net_weight": _spec(("NET WEIGHT", "NET WT", "N.W.", "N/W"), "weight"),
    "weight_unit": _spec(("WEIGHT UNIT", "UNIT OF WEIGHT"), "unit"),
    "measurement": _spec(("MEASUREMENT", "MEASUREMENTS", "CUBIC METER", "CUBIC METERS"), "measurement"),
    "goods_description": _spec(("GOODS DESCRIPTION", "DESCRIPTION OF GOODS", "DESCRIPTION"), "text"),
    "description": _spec(("DESCRIPTION", "DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "ITEM DESCRIPTION", "COMMODITY", "PARTICULARS"), "text"),
    "hs_code": _spec(("HS CODE", "H.S. CODE", "HARMONIZED CODE", "HS NO"), "identifier"),
    "quantity": _spec(("QUANTITY", "QTY", "QUANTITIES"), "quantity"),
    "unit": _spec(("UNIT", "UOM", "UNITS"), "unit"),
    "unit_price": _spec(("UNIT PRICE", "UNIT COST", "PRICE/UNIT", "RATE"), "amount"),
    "amount": _spec(("LINE AMOUNT", "EXTENDED AMOUNT", "TOTAL PRICE", "AMOUNT", "VALUE"), "amount"),
    "product_code": _spec(("PRODUCT CODE", "ITEM CODE", "PRODUCT NO"), "identifier"),
    "shipping_mark": _spec(("SHIPPING MARK", "SHIPPING MARKS", "MARKS & NOS", "MARKS AND NUMBERS"), "text"),
    "country_of_origin": _spec(("COUNTRY OF ORIGIN", "ORIGIN COUNTRY"), "location"),
    "country_of_destination": _spec(("COUNTRY OF DESTINATION", "DESTINATION COUNTRY"), "location"),
    "carrier": _spec(("CARRIER", "EXPORT CARRIER", "FORWARDER"), "party"),
    "bank": _spec(("BANK", "ISSUING BANK", "ADVISING BANK"), "party"),
    "reference_number": _spec(("REFERENCE NO", "REFERENCE NUMBER", "OTHER REFERENCE", "REF NO"), "identifier"),
    "booking_number": _spec(("BOOKING NO", "BOOKING NUMBER"), "identifier"),
    "contract_number": _spec(("CONTRACT NO", "CONTRACT NUMBER"), "identifier"),
    "part_number": _spec(("PART NUMBER", "PART NO", "PART#"), "identifier"),
    "sku": _spec(("SKU",), "identifier"),
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
    "cbm": _spec(("CBM", "CUBIC METER", "CUBIC METERS"), "measurement"),
}


DOCUMENT_FIELDS = {
    "Commercial Invoice": ("invoice_number", "invoice_date", "seller", "buyer", "consignee", "lc_number", "lc_date", "bl_number", "purchase_order_number", "currency", "total_amount", "payment_terms", "incoterm", "vessel", "voyage_number", "departure_date", "port_of_loading", "port_of_discharge", "final_destination"),
    "Packing List": ("document_number", "packing_list_number", "document_date", "date", "invoice_reference", "exporter", "shipper", "consignee", "buyer", "package_count", "package_type", "gross_weight", "net_weight", "weight_unit", "measurement", "vessel", "voyage_number", "port_of_loading", "port_of_discharge", "final_destination"),
    "B/L": ("bl_number", "document_date", "shipper", "consignee", "notify_party", "vessel", "voyage_number", "invoice_reference", "port_of_loading", "port_of_discharge", "place_of_receipt", "place_of_delivery", "final_destination", "container_number", "seal_number", "package_count", "gross_weight", "measurement", "weight_unit", "goods_description"),
}

ITEM_FIELDS = {
    "Commercial Invoice": ("description", "hs_code", "quantity", "unit", "unit_price", "amount", "po_number", "product_code", "shipping_mark"),
    "Packing List": ("description", "quantity", "unit", "package_count", "package_type", "gross_weight", "net_weight", "weight_unit", "measurement", "shipping_mark"),
}

PARTY_FIELDS = {"seller", "buyer", "consignee", "exporter", "shipper", "notify_party", "carrier", "bank", "manufacturer", "signatory_company"}


__all__ = ["DOCUMENT_FIELDS", "FIELD_SPEC", "ITEM_FIELDS", "PARTY_FIELDS", "SPECS", "FieldSpec"]

# Compatibility alias for callers that prefer the singular spelling.
FIELD_SPEC = SPECS
