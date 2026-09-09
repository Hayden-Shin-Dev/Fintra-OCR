from dataclasses import dataclass, asdict
@dataclass(frozen=True)
class FieldSpec:
    kind: str
    description: str

def f(description, kind="text"):
    return FieldSpec(kind, description)
PARTIES = {
    "shipper": f("Name of the party shipping/exporting goods; preserve legal name", "party"),
    "consignee": f("Name of the party receiving the shipment, not notify party", "party"),
}
CARGO = {
    "total_packages": f("Explicit total count of packages, not item quantity", "number"),
    "gross_weight": f("Explicit total gross weight numeric value", "number"),
    "net_weight": f("Explicit total net weight numeric value", "number"),
    "weight_unit": f("Unit explicitly attached to the total weight", "unit"),
    "volume": f("Explicit total cargo volume numeric value", "number"),
    "volume_unit": f("Unit explicitly attached to volume", "unit"),
}
SCHEMAS = {
    "commercial_invoice": {
        "invoice_number": f("Commercial invoice identifier, not purchase order or shipment identifier"),
        "invoice_date": f("Date of issue of the invoice", "date"),
        "seller": f("Seller legal name; do not include address", "party"),
        "buyer": f("Buyer legal name; may differ from consignee", "party"),
        "purchase_order_number": f("Buyer's purchase order identifier"),
        "currency": f("Explicit currency code or unambiguous currency name", "currency"),
        "subtotal": f("Explicit subtotal before tax and charges", "number"),
        "tax": f("Explicit tax amount", "number"),
        "total_amount": f("Final invoice payable amount, not an individual line amount", "number"),
        "incoterms": f("Explicit trade delivery rule and named place; not payment text", "incoterms"),
        "payment_terms": f("Explicit payment terms"),
    },
    "packing_list": {
        "packing_list_number": f("Packing list's own identifier"),
        "packing_date": f("Packing list issue date", "date"),
        "invoice_number": f("Referenced commercial invoice identifier"),
        **PARTIES, **CARGO,
    },
    "bill_of_lading": {
        "bill_of_lading_number": f("Bill of lading identifier, not booking number"),
        "issue_date": f("Bill of lading issue date", "date"),
        "on_board_date": f("Shipped on board date, distinguish from issue date", "date"),
        **PARTIES,
        "notify_party": f("Notify party legal name", "party"),
        "carrier": f("Carrier legal name", "party"),
        "vessel": f("Vessel name"), "voyage": f("Voyage identifier"),
        "port_of_loading": f("Port where cargo is loaded"),
        "port_of_discharge": f("Port where cargo is discharged"),
        "place_of_receipt": f("Place of receipt"),
        "place_of_delivery": f("Final place of delivery"),
        "freight_terms": f("Freight prepaid or collect terms", "freight_terms"), **CARGO,
    },
}
COMMON_ITEM = {
    "material": f("Material or composition explicitly printed for this goods row; not product code", "material"),
    "color": f("Color explicitly printed for this goods row"),
    "description": f("Goods description for this row only"),
    "quantity": f("Goods quantity for this row, not package count", "number"),
    "unit": f("Explicit quantity unit for this row", "unit"),
}
ITEM_CARGO = {
    "package_count": f("Package count for this cargo row only", "number"),
    "gross_weight": f("Gross weight numeric value for this row only", "number"),
    "net_weight": f("Net weight numeric value for this row only", "number"),
    "weight_unit": f("Explicit weight unit applying to this row", "unit"),
    "volume": f("Volume numeric value for this row only", "number"),
    "volume_unit": f("Explicit volume unit applying to this row", "unit"),
}
ITEM_SCHEMAS = {
    "commercial_invoice": {**COMMON_ITEM, "product_code": f("Product code"),
        "unit_price": f("Price per unit for this row", "number"),
        "amount": f("Extended amount for this row", "number")},
    "packing_list": {**COMMON_ITEM, "marks": f("Shipping marks"), **ITEM_CARGO},
    "bill_of_lading": {**COMMON_ITEM, "marks": f("Shipping marks"),
        "container_number": f("Container identifier"), "seal_number": f("Seal identifier"), **ITEM_CARGO},
}
# Additive v2 contract: references remain available regardless of document type.
REFERENCES = {
    "proforma_invoice_number": f("Explicit proforma invoice reference; not a commercial invoice identifier"),
    "invoice_number": f("Commercial invoice identifier, including a reference on another document"),
    "bill_of_lading_number": f("Bill of lading identifier, including an explicit reference"),
    "packing_list_number": f("Packing list identifier, including an explicit reference"),
    "purchase_order_number": f("Explicit purchase order identifier; buyer reference alone is not a purchase order"),
    "booking_number": f("Carrier booking identifier; not the bill of lading identifier"),
    "buyer_reference": f("Buyer's reference as printed, without assuming it is a purchase order"),
    "document_reference": f("Other explicitly labelled document reference"),
    "letter_of_credit_number": f("Explicit letter of credit identifier"),
    "insurance_policy_number": f("Explicit insurance or marine cover policy identifier"),
    "letter_of_credit_issuing_bank": f("Explicit bank issuing the letter of credit; not carrier or beneficiary", "party"),
}
TRANSPORT = {
    "shipping_origin": f("Explicit ship-from location; not necessarily port of loading or country where goods were manufactured"),
    "carrier": f("Explicitly named carrier; do not infer it from vessel or shipper", "party"),
    "mode_of_transport": f("Explicit initial carriage or transport mode, not vessel name"),
    "routing_instructions": f("Explicit domestic routing/export instructions, not voyage"),
    "movement_type": f("Explicit type of movement, not voyage"),
    "freight_payable_at": f("Place at which freight is payable, not prepaid/collect terms"),
    "vessel": f("Explicit vessel or vessel/aircraft name"),
    "voyage": f("Voyage identifier"),
    "port_of_loading": f("Port of loading"),
    "port_of_discharge": f("Port of discharge"),
    "place_of_delivery": f("Final delivery destination"),
    "departure_date": f("Explicit departure date, not issue or on-board date", "date"),
    "country_of_origin": f("Explicit country of origin of goods, ISO alpha-2 normalization", "country"),
    "country_of_destination": f("Explicit country of destination, not a port or city, ISO alpha-2 normalization", "country"),
}
for dtype, fields in SCHEMAS.items():
    for name,spec in CARGO.items():fields.setdefault(name,spec)
    for name,spec in ITEM_CARGO.items():ITEM_SCHEMAS[dtype].setdefault(name,spec)
    for name, spec in REFERENCES.items(): fields.setdefault(name, spec)
    for name, spec in TRANSPORT.items(): fields.setdefault(name, spec)
    for name in ("seller", "buyer", "exporter", "shipper", "consignee", "notify_party"):
        fields.setdefault(name, f("Explicit " + name.replace("_", " ") + " legal name; preserve distinct party roles", "party"))
    fields.setdefault("issue_date", f("Issue date of THIS document; not a referenced invoice date or departure date", "date"))
    fields.setdefault('forwarding_agent',f('Explicit forwarding agent legal name, not shipper or carrier','party'))
    fields.setdefault('forwarding_agent_number',f('Explicit forwarding agent registration/FMC identifier; not the agent legal name'))
    fields.setdefault('delivery_party',f('Explicit party labelled for delivery to; distinct from consignee','party'))
    fields.setdefault('bill_to_party',f('Explicit billing or third-party billing legal name; not automatically buyer','party'))
    fields.setdefault('quotation_number',f('Explicit quotation reference; not invoice or purchase order number'))
    fields.setdefault('letter_of_credit_date',f('Explicit issue date of referenced letter of credit, not this document date','date'))
    fields.setdefault('issue_place',f('Explicit place where this document was issued, distinct from cargo ports'))
    fields.setdefault('shipment_date',f('Explicit shipment date; not automatically departure, on-board or issue date','date'))
    fields.setdefault('declared_value',f('Explicit declared cargo value, not invoice amount or reference','number'))
    if dtype != "commercial_invoice":
        fields.setdefault("invoice_date", f("Issue date of the referenced invoice, not this document", "date"))
    ITEM_SCHEMAS[dtype].setdefault("package_count", f("Explicit number of packages for this row, not goods quantity", "number"))
    ITEM_SCHEMAS[dtype].setdefault("purchase_order_number", f("Explicit purchase order reference for this item row; not a document-wide order or product code"))
    ITEM_SCHEMAS[dtype].setdefault("product_size", f("Explicit product size or size designation, not a quantity unit"))
    ITEM_SCHEMAS[dtype].setdefault("marks", f("Shipping marks for this row; not product description"))
    ITEM_SCHEMAS[dtype].setdefault("product_code", f("Explicit product identifier for this row"))
    ITEM_SCHEMAS[dtype].setdefault("hs_code", f("Explicit customs HS code; keep punctuation and leading zeros"))
    ITEM_SCHEMAS[dtype].setdefault("package_type", f("Explicit package type for this row", "unit"))
    for weight in ('gross','net'):
        fields[weight+'_weight_unit']=f('Explicit '+weight+' weight unit; may differ from the other weight', 'unit')
        ITEM_SCHEMAS[dtype][weight+'_weight_unit']=f('Explicit '+weight+' weight unit applying to this row', 'unit')

# Legacy field names remain present but are derived from the same canonical field.
ALIASES = {"commercial_invoice": {"invoice_date": "issue_date"},
           "packing_list": {"packing_date": "issue_date"}, "bill_of_lading": {}}

def catalog():
    return {k: {"fields": {n: asdict(s) for n,s in v.items()},
                "items": {n: asdict(s) for n,s in ITEM_SCHEMAS[k].items()}}
            for k,v in SCHEMAS.items()}
