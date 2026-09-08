"""Build the prediction-independent Audit Field Schema v2 inventory.

This script reads only frozen Paddle OCR JSON and case manifests.  It does not
call an extractor, read extractor predictions, modify Gold, or run OCR.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DOCUMENT_TYPES = ("Commercial Invoice", "Packing List", "B/L")


FIELD_DEFS: dict[str, dict[str, Any]] = {
    # Common / identifiers
    "document_number": {"category": "common", "types": list(DOCUMENT_TYPES), "aliases": ["DOCUMENT NO", "DOCUMENT NUMBER", "DOC NO"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "REQUIRED", "B/L": "OPTIONAL"}, "targets": []},
    "document_date": {"category": "common", "types": list(DOCUMENT_TYPES), "aliases": ["DOCUMENT DATE", "DATE OF DOCUMENT"], "data_type": "date", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "REQUIRED", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "invoice_number": {"category": "identifier", "types": ["Commercial Invoice"], "aliases": ["INVOICE NO", "INVOICE NUMBER", "INV NO", "INV NUMBER", "INVOICE #"], "data_type": "identifier", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": ["Packing List.invoice_reference", "B/L.invoice_reference"]},
    "invoice_date": {"category": "date", "types": ["Commercial Invoice"], "aliases": ["INVOICE DATE", "DATE OF INVOICE", "INVOICE NO AND DATE"], "data_type": "date", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": []},
    "invoice_reference": {"category": "identifier", "types": ["Packing List", "B/L"], "aliases": ["INVOICE REF", "INVOICE REFERENCE", "RELATED INVOICE", "INVOICE NO"], "data_type": "identifier", "requirement": {"Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": ["Commercial Invoice.invoice_number"]},
    "bl_number": {"category": "identifier", "types": ["B/L"], "aliases": ["BILL OF LADING NO", "BILL OF LADING NUMBER", "B/L NO", "B/L NUMBER", "BL NO"], "data_type": "identifier", "requirement": {"B/L": "REQUIRED"}, "targets": ["Commercial Invoice.bl_number"]},
    "lc_number": {"category": "identifier", "types": ["Commercial Invoice"], "aliases": ["L/C NO", "LC NO", "LETTER OF CREDIT NO", "L/C NUMBER"], "data_type": "identifier", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "lc_date": {"category": "date", "types": ["Commercial Invoice"], "aliases": ["L/C DATE", "LC DATE", "LETTER OF CREDIT DATE"], "data_type": "date", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "purchase_order_number": {"category": "identifier", "types": ["Commercial Invoice", "Packing List"], "aliases": ["PURCHASE ORDER", "PURCHASE ORDER NO", "P/O NO", "PO NO"], "data_type": "identifier", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL"}, "targets": []},
    "contract_number": {"category": "identifier", "types": ["Commercial Invoice", "Packing List", "B/L"], "aliases": ["CONTRACT NO", "CONTRACT NUMBER"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "reference_number": {"category": "identifier", "types": list(DOCUMENT_TYPES), "aliases": ["REFERENCE NO", "REFERENCE NUMBER", "OTHER REFERENCE", "REF NO"], "data_type": "identifier", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "OPTIONAL"}, "targets": []},
    "booking_number": {"category": "identifier", "types": ["B/L"], "aliases": ["BOOKING NO", "BOOKING NUMBER"], "data_type": "identifier", "requirement": {"B/L": "AUDIT_USEFUL"}, "targets": []},
    # Parties
    "seller": {"category": "party", "types": ["Commercial Invoice"], "aliases": ["SELLER", "SELLER NAME", "FROM", "SOLD BY"], "data_type": "party", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": ["Packing List.exporter", "B/L.shipper"]},
    "exporter": {"category": "party", "types": ["Packing List"], "aliases": ["EXPORTER", "SHIPPER/EXPORTER", "EXPORTED BY"], "data_type": "party", "requirement": {"Packing List": "REQUIRED"}, "targets": ["Commercial Invoice.seller", "B/L.shipper"]},
    "shipper": {"category": "party", "types": ["B/L"], "aliases": ["SHIPPER", "CONSIGNOR", "CONSIGNOR/SHIPPER"], "data_type": "party", "requirement": {"B/L": "REQUIRED"}, "targets": ["Commercial Invoice.seller", "Packing List.exporter"]},
    "buyer": {"category": "party", "types": ["Commercial Invoice", "Packing List"], "aliases": ["BUYER", "BUYER IF OTHER THAN CONSIGNEE", "SOLD TO", "BILL TO"], "data_type": "party", "requirement": {"Commercial Invoice": "REQUIRED", "Packing List": "AUDIT_USEFUL"}, "targets": ["Packing List.consignee", "B/L.consignee"]},
    "consignee": {"category": "party", "types": ["Commercial Invoice", "Packing List", "B/L"], "aliases": ["CONSIGNEE", "CONSIGNED TO", "SHIP TO"], "data_type": "party", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "REQUIRED", "B/L": "REQUIRED"}, "targets": ["Commercial Invoice.buyer", "Packing List.buyer", "B/L.consignee"]},
    "notify_party": {"category": "party", "types": ["B/L"], "aliases": ["NOTIFY PARTY", "NOTIFY", "ALSO NOTIFY"], "data_type": "party", "requirement": {"B/L": "REQUIRED"}, "targets": []},
    "manufacturer": {"category": "party", "types": ["Commercial Invoice", "Packing List"], "aliases": ["MANUFACTURER", "MADE BY"], "data_type": "party", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL"}, "targets": []},
    "carrier": {"category": "party", "types": ["B/L", "Commercial Invoice", "Packing List"], "aliases": ["CARRIER", "EXPORT CARRIER", "FORWARDER"], "data_type": "party", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "bank": {"category": "party", "types": ["Commercial Invoice"], "aliases": ["BANK", "ISSUING BANK", "ADVISING BANK"], "data_type": "party", "requirement": {"Commercial Invoice": "OPTIONAL"}, "targets": []},
    "signatory_company": {"category": "party", "types": list(DOCUMENT_TYPES), "aliases": ["AUTHORIZED SIGNATURE", "SIGNATURE", "SIGNED BY"], "data_type": "party", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    # Shipment / location
    "vessel": {"category": "shipment", "types": list(DOCUMENT_TYPES), "aliases": ["VESSEL", "VESSEL/VOY", "VESSEL / VOY", "EXPORT CARRIER"], "data_type": "text", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "REQUIRED"}, "targets": []},
    "voyage_number": {"category": "shipment", "types": ["B/L", "Commercial Invoice", "Packing List"], "aliases": ["VOYAGE", "VOY", "VOY NO", "VESSEL/VOY"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "flight_number": {"category": "shipment", "types": list(DOCUMENT_TYPES), "aliases": ["FLIGHT NO", "FLIGHT NUMBER"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "method_of_dispatch": {"category": "shipment", "types": list(DOCUMENT_TYPES), "aliases": ["METHOD OF DISPATCH", "MODE OF TRANSPORT", "TRANSPORT MODE"], "data_type": "text", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "shipment_type": {"category": "shipment", "types": ["B/L", "Packing List"], "aliases": ["SHIPMENT TYPE", "TYPE OF SHIPMENT"], "data_type": "text", "requirement": {"Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "departure_date": {"category": "shipment", "types": ["Commercial Invoice", "Packing List", "B/L"], "aliases": ["DATE OF DEPARTURE", "DEPARTURE DATE", "ETD"], "data_type": "date", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "OPTIONAL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "arrival_date": {"category": "shipment", "types": list(DOCUMENT_TYPES), "aliases": ["DATE OF ARRIVAL", "ARRIVAL DATE", "ETA"], "data_type": "date", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "shipment_date": {"category": "shipment", "types": ["B/L"], "aliases": ["SHIPMENT DATE", "ON BOARD DATE", "SHIPPED ON BOARD"], "data_type": "date", "requirement": {"B/L": "REQUIRED"}, "targets": []},
    "port_of_loading": {"category": "location", "types": ["B/L", "Commercial Invoice", "Packing List"], "aliases": ["PORT OF LOADING", "PLACE OF LOADING", "LOADING PORT"], "data_type": "location", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "REQUIRED"}, "targets": []},
    "port_of_discharge": {"category": "location", "types": ["B/L", "Commercial Invoice", "Packing List"], "aliases": ["PORT OF DISCHARGE", "PLACE OF DISCHARGE", "DISCHARGE PORT"], "data_type": "location", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "REQUIRED"}, "targets": []},
    "place_of_receipt": {"category": "location", "types": ["B/L"], "aliases": ["PLACE OF RECEIPT", "RECEIPT PLACE"], "data_type": "location", "requirement": {"B/L": "AUDIT_USEFUL"}, "targets": []},
    "place_of_delivery": {"category": "location", "types": ["B/L"], "aliases": ["PLACE OF DELIVERY", "DELIVERY PLACE"], "data_type": "location", "requirement": {"B/L": "AUDIT_USEFUL"}, "targets": []},
    "final_destination": {"category": "location", "types": list(DOCUMENT_TYPES), "aliases": ["FINAL DESTINATION", "DESTINATION"], "data_type": "location", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "country_of_origin": {"category": "location", "types": list(DOCUMENT_TYPES), "aliases": ["COUNTRY OF ORIGIN", "ORIGIN COUNTRY"], "data_type": "location", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "OPTIONAL"}, "targets": []},
    "country_of_destination": {"category": "location", "types": list(DOCUMENT_TYPES), "aliases": ["COUNTRY OF DESTINATION", "DESTINATION COUNTRY"], "data_type": "location", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    # Financial / terms
    "currency": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["CURRENCY", "CURRENCY CODE"], "data_type": "currency", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": []},
    "payment_terms": {"category": "terms", "types": ["Commercial Invoice"], "aliases": ["PAYMENT TERMS", "TERMS OF PAYMENT"], "data_type": "text", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "delivery_terms": {"category": "terms", "types": ["Commercial Invoice"], "aliases": ["DELIVERY TERMS", "TERMS OF DELIVERY"], "data_type": "text", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "incoterm": {"category": "terms", "types": list(DOCUMENT_TYPES), "aliases": ["INCOTERM", "TERMS OF DELIVERY"], "data_type": "code", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "subtotal": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["SUBTOTAL", "SUB TOTAL"], "data_type": "amount", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "freight": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["FREIGHT", "FREIGHT CHARGE"], "data_type": "amount", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "insurance": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["INSURANCE", "INSURANCE CHARGE"], "data_type": "amount", "requirement": {"Commercial Invoice": "OPTIONAL"}, "targets": []},
    "tax": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["TAX", "VAT", "TAX AMOUNT"], "data_type": "amount", "requirement": {"Commercial Invoice": "AUDIT_USEFUL"}, "targets": []},
    "discount": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["DISCOUNT", "DISCOUNT AMOUNT"], "data_type": "amount", "requirement": {"Commercial Invoice": "OPTIONAL"}, "targets": []},
    "other_charges": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["OTHER CHARGES", "ADDITIONAL CHARGES"], "data_type": "amount", "requirement": {"Commercial Invoice": "OPTIONAL"}, "targets": []},
    "total_amount": {"category": "financial", "types": ["Commercial Invoice"], "aliases": ["TOTAL", "TOTAL AMOUNT", "INVOICE TOTAL", "GRAND TOTAL"], "data_type": "amount", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": []},
    # Packing / weights
    "package_count": {"category": "packing", "types": list(DOCUMENT_TYPES), "aliases": ["PACKAGE", "PACKAGES", "PACKAGE COUNT", "NO OF PACKAGES", "NUMBER OF PACKAGES"], "data_type": "quantity", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "REQUIRED", "B/L": "REQUIRED"}, "targets": ["Packing List.package_count", "B/L.package_count"]},
    "package_type": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["PACKAGE TYPE", "KIND OF PACKAGES", "PACKING TYPE"], "data_type": "text", "requirement": {"Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "carton_count": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["CARTON", "CARTONS", "CARTON COUNT"], "data_type": "quantity", "requirement": {"Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "pallet_count": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["PALLET", "PALLETS", "PALLET COUNT"], "data_type": "quantity", "requirement": {"Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "container_number": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["CONTAINER NO", "CONTAINER NUMBER", "CONTAINER"], "data_type": "identifier", "requirement": {"Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "seal_number": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["SEAL NO", "SEAL NUMBER", "SEAL"], "data_type": "identifier", "requirement": {"Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    "gross_weight": {"category": "packing", "types": list(DOCUMENT_TYPES), "aliases": ["GROSS WEIGHT", "GROSS WT", "G.W.", "G/W"], "data_type": "weight", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "REQUIRED", "B/L": "REQUIRED"}, "targets": ["Packing List.gross_weight", "B/L.gross_weight"]},
    "net_weight": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["NET WEIGHT", "NET WT", "N.W.", "N/W"], "data_type": "weight", "requirement": {"Packing List": "REQUIRED", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "weight_unit": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["WEIGHT UNIT", "UNIT OF WEIGHT"], "data_type": "unit", "requirement": {"Packing List": "REQUIRED", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "measurement": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["MEASUREMENT", "MEASUREMENTS", "CBM", "M3"], "data_type": "measurement", "requirement": {"Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "cbm": {"category": "packing", "types": ["Packing List", "B/L"], "aliases": ["CUBIC METER", "CUBIC METERS"], "data_type": "measurement", "requirement": {"Packing List": "OPTIONAL", "B/L": "OPTIONAL"}, "targets": []},
    # Items
    "line_number": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["NO", "NO.", "ITEM NO", "LINE NO"], "data_type": "quantity", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL"}, "targets": []},
    "product_code": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["PRODUCT CODE", "ITEM CODE", "PRODUCT NO"], "data_type": "identifier", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL"}, "targets": []},
    "sku": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["SKU"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL"}, "targets": []},
    "part_number": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["PART NUMBER", "PART NO", "PART#"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL"}, "targets": []},
    "po_number": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["PO NUMBER", "P/O NUMBER", "PURCHASE ORDER NO"], "data_type": "identifier", "requirement": {"Commercial Invoice": "OPTIONAL", "Packing List": "OPTIONAL"}, "targets": []},
    "shipping_mark": {"category": "item", "types": ["Commercial Invoice", "Packing List", "B/L"], "aliases": ["SHIPPING MARK", "SHIPPING MARKS", "MARKS & NOS", "MARKS AND NUMBERS"], "data_type": "text", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL", "B/L": "AUDIT_USEFUL"}, "targets": []},
    "description": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["DESCRIPTION", "DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "ITEM DESCRIPTION"], "data_type": "text", "requirement": {"Commercial Invoice": "REQUIRED", "Packing List": "REQUIRED"}, "targets": ["B/L.goods_description"]},
    "goods_description": {"category": "item", "types": ["B/L"], "aliases": ["DESCRIPTION OF GOODS", "GOODS DESCRIPTION", "DESCRIPTION"], "data_type": "text", "requirement": {"B/L": "REQUIRED"}, "targets": ["Commercial Invoice.items.description", "Packing List.items.description"]},
    "hs_code": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["HS CODE", "H.S. CODE", "HARMONIZED CODE", "HS NO"], "data_type": "identifier", "requirement": {"Commercial Invoice": "AUDIT_USEFUL", "Packing List": "AUDIT_USEFUL"}, "targets": []},
    "quantity": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["QUANTITY", "QTY", "QUANTITIES"], "data_type": "quantity", "requirement": {"Commercial Invoice": "REQUIRED", "Packing List": "REQUIRED"}, "targets": ["Commercial Invoice.items.quantity", "Packing List.items.quantity"]},
    "unit": {"category": "item", "types": ["Commercial Invoice", "Packing List"], "aliases": ["UNIT", "UOM", "UNITS"], "data_type": "unit", "requirement": {"Commercial Invoice": "REQUIRED", "Packing List": "REQUIRED"}, "targets": []},
    "unit_price": {"category": "item", "types": ["Commercial Invoice"], "aliases": ["UNIT PRICE", "UNIT COST", "PRICE/UNIT"], "data_type": "amount", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": []},
    "amount": {"category": "item", "types": ["Commercial Invoice"], "aliases": ["AMOUNT", "LINE AMOUNT", "EXTENDED AMOUNT", "TOTAL PRICE"], "data_type": "amount", "requirement": {"Commercial Invoice": "REQUIRED"}, "targets": []},
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).upper().replace("#", " NUMBER ")
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def alias_hit(text: str, aliases: list[str]) -> str | None:
    value = normalize(text)
    for alias in sorted(aliases, key=len, reverse=True):
        target = normalize(alias)
        if value == target or re.search(rf"(?:^| ){re.escape(target)}(?:$| )", value):
            return alias
    return None


def box(region: dict[str, Any]) -> tuple[float, float, float, float]:
    points = region.get("polygon") or region.get("bbox") or []
    if points and isinstance(points[0], (int, float)):
        points = list(zip(points[::2], points[1::2]))
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def plausible(text: str, data_type: str) -> bool:
    value = normalize(text)
    if not value:
        return False
    if data_type == "date":
        return bool(re.search(r"\b\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\b", value) or re.search(r"\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)", value))
    if data_type in {"amount", "quantity", "weight", "measurement"}:
        return bool(re.search(r"\d", value))
    if data_type == "currency":
        return bool(re.fullmatch(r"(?:USD|EUR|JPY|KRW|RMB|CNY|GBP|\$|€|¥)", value))
    if data_type == "unit":
        return bool(re.search(r"\b(?:EA|PCS|PC|SET|BOX|CTN|KG|KGS|G|LB|LBS|M|M2|M3|UNIT|UNITS)\b", value))
    if data_type == "identifier":
        return bool(re.search(r"[A-Z0-9]", value)) and len(value) <= 80
    if data_type == "party":
        return bool(re.search(r"[A-Z]{2,}", value)) and len(value) >= 3
    if data_type == "location":
        return bool(re.search(r"[A-Z]{2,}", value)) and len(value) >= 3
    return bool(re.search(r"[A-Z]", value))


def nearby_value(label: dict[str, Any], regions: list[dict[str, Any]], data_type: str) -> dict[str, Any] | None:
    lx1, ly1, lx2, ly2 = box(label)
    lh = max(8.0, ly2 - ly1)
    candidates = []
    for region in regions:
        if region is label or not str(region.get("text", "")).strip():
            continue
        if box(region) == (lx1, ly1, lx2, ly2) and normalize(str(region.get("text", ""))) == normalize(str(label.get("text", ""))):
            continue
        rx1, ry1, rx2, ry2 = box(region)
        same_line = abs((ry1 + ry2) / 2 - (ly1 + ly2) / 2) <= lh * 1.2
        below = ry1 >= ly2 - lh * 0.3 and ry1 <= ly2 + lh * 4.0
        right = rx1 >= lx2 - lh * 0.5 and rx1 <= lx2 + lh * 12.0 and abs((ry1 + ry2) / 2 - (ly1 + ly2) / 2) <= lh * 2.0
        if (same_line and rx1 >= lx2 - lh * 0.5) or below or right:
            if plausible(str(region.get("text", "")), data_type):
                distance = abs((ry1 + ry2) / 2 - (ly1 + ly2) / 2) + abs(rx1 - lx2) * 0.15
                candidates.append((distance, region))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def load_cases(dataset: str, root: Path) -> list[dict[str, Any]]:
    cases = []
    for case_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        ocr_path = case_dir / "outputs/recognition/paddle.json"
        if not manifest_path.is_file() or not ocr_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = json.loads(ocr_path.read_text(encoding="utf-8"))
        cases.append({"dataset": dataset, "case_id": manifest["case_id"], "document_type": manifest["document_type"], "regions": payload.get("regions", [])})
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/schema-v2"))
    parser.add_argument("--accurate75", type=Path, default=Path("artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1"))
    parser.add_argument("--fast300", type=Path, default=Path(".tmp/mvp_fast300_cases_v1"))
    parser.add_argument("--v3", type=Path, default=Path("artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3/cases"))
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    datasets = [("accurate75", args.accurate75), ("fast300", args.fast300), ("v3_75", args.v3)]
    cases = [case for name, root in datasets for case in load_cases(name, root)]
    case_pools = {name: load_cases(name, root) for name, root in datasets}
    case_pools["combined_selected_sets"] = cases

    coverage_rows = []
    synonym_rows = []
    representatives: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for dataset_name, pool in case_pools.items():
        for field, spec in FIELD_DEFS.items():
            for document_type in DOCUMENT_TYPES:
                applicable = [case for case in pool if document_type in spec["types"] and case["document_type"] == document_type]
                label_cases = pair_cases = plausible_cases = 0
                observed = Counter()
                for case in applicable:
                    regions = case["regions"]
                    labels = []
                    for region in regions:
                        hit = alias_hit(str(region.get("text", "")), spec["aliases"])
                        if hit:
                            labels.append((region, hit))
                            observed[str(region.get("text", ""))] += 1
                            representatives[(dataset_name, field, document_type)].append({"dataset": case["dataset"], "case_id": case["case_id"], "label": region.get("text", ""), "bbox": region.get("polygon")})
                    if labels:
                        label_cases += 1
                    pair = False
                    for label, alias in labels:
                        value = nearby_value(label, regions, spec["data_type"])
                        if value:
                            pair = True
                            representatives[(dataset_name, field, document_type)].append({"dataset": case["dataset"], "case_id": case["case_id"], "label": label.get("text", ""), "value": value.get("text", ""), "bbox": value.get("polygon")})
                            break
                    if any(nearby_value(label, regions, spec["data_type"]) for label, _ in labels):
                        plausible_cases += 1
                    if pair:
                        pair_cases += 1
                for variant, count in observed.most_common():
                    synonym_rows.append({"dataset": dataset_name, "document_type": document_type, "canonical_field": field, "observed_ocr_text": variant, "normalized": normalize(variant), "count": count})
                rate = pair_cases / len(applicable) if applicable else 0.0
                requirement = spec["requirement"].get(document_type, "NOT_APPLICABLE")
                if requirement == "NOT_APPLICABLE":
                    decision = "NOT_APPLICABLE"
                elif requirement == "REQUIRED":
                    decision = "INCLUDE_REQUIRED" if rate >= 0.10 else "DEFER_LOW_EVIDENCE"
                elif rate >= 0.20:
                    decision = "INCLUDE_AUDIT_USEFUL"
                elif rate > 0:
                    decision = "INCLUDE_OPTIONAL"
                else:
                    decision = "DEFER_LOW_EVIDENCE"
                coverage_rows.append({
                    "dataset": dataset_name, "document_type": document_type, "field": field,
                    "category": spec["category"], "total_documents": len([case for case in pool if case["document_type"] == document_type]),
                    "documents_applicable": len(applicable), "explicit_label_found": label_cases,
                    "plausible_value_found": plausible_cases, "label_and_value_pair_found": pair_cases,
                    "estimated_recoverable": pair_cases, "recoverable_rate": f"{rate:.6f}",
                    "requirement_level": requirement, "inclusion_decision": decision,
                    "common_label_variants": " || ".join(v for v, _ in observed.most_common(5)),
                    "representative_examples": json.dumps(representatives[(dataset_name, field, document_type)][:3], ensure_ascii=False),
                })

    schema_fields = []
    by_key = {(row["document_type"], row["field"]): row for row in coverage_rows if row["dataset"] == "combined_selected_sets"}
    for name, spec in FIELD_DEFS.items():
        for document_type in DOCUMENT_TYPES:
            row = by_key[(document_type, name)]
            schema_fields.append({
                "canonical_name": name, "document_types": spec["types"], "category": spec["category"],
                "aliases": spec["aliases"], "data_type": spec["data_type"], "cardinality": "single",
                "requirement_level": spec["requirement"].get(document_type, "NOT_APPLICABLE"),
                "nullable": True, "audit_use": row["inclusion_decision"] != "NOT_APPLICABLE",
                "cross_document_targets": spec["targets"], "inclusion_decision": row["inclusion_decision"],
                "coverage": {"explicit_label_found": row["explicit_label_found"], "label_and_value_pair_found": row["label_and_value_pair_found"], "estimated_recoverable": row["estimated_recoverable"], "recoverable_rate": float(row["recoverable_rate"])},
            })
    schema = {"schema_name": "Fintra Audit Field Schema v2", "schema_version": "2.0", "contract": "Document-type-stable nullable fields; absent or unproven values are null, never guessed.", "datasets": {name: str(root) for name, root in datasets}, "fields": schema_fields}
    (out / "field_schema_v2.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "field_ocr_coverage.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(coverage_rows[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(coverage_rows)
    with (out / "label_synonyms.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["dataset", "document_type", "canonical_field", "observed_ocr_text", "normalized", "count"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(synonym_rows)

    cross = []
    seen = set()
    for name, spec in FIELD_DEFS.items():
        for target in spec["targets"]:
            key = (f"{name}", target)
            if key in seen: continue
            seen.add(key)
            target_doc, target_field = target.split(".", 1)
            source_doc = ", ".join(spec["types"])
            cross.append({"source_field": name, "source_document_types": source_doc, "target_field": target_field, "target_document": target_doc, "purpose": "audit_reconciliation", "comparison": "exact_or_normalized_by_data_type", "notes": "Role-specific semantic mapping; never merge fields with different document roles."})
    with (out / "cross_document_mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(cross[0].keys()) if cross else ["source_field"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(cross)

    current = {
        "Commercial Invoice": ["invoice_number", "invoice_date", "seller", "buyer", "currency", "total_amount", "items"],
        "Packing List": ["packing_list_number", "date", "exporter", "consignee", "items", "package_count", "gross_weight", "net_weight", "weight_unit"],
        "B/L": ["bl_number", "shipper", "consignee", "notify_party", "vessel", "port_of_loading", "port_of_discharge", "shipment_date", "package_count", "gross_weight", "weight_unit", "goods_description"],
    }
    v2_by_type = defaultdict(list)
    for item in schema_fields:
        if item["requirement_level"] != "NOT_APPLICABLE": v2_by_type[item["canonical_name"]].append(item)
    comparison = []
    for document_type, old_fields in current.items():
        new_fields = sorted({item["canonical_name"] for item in schema_fields if document_type in FIELD_DEFS[item["canonical_name"]]["types"]})
        for field in sorted(set(old_fields) | set(new_fields)):
            if field in old_fields and field in new_fields: change = "retained"
            elif field in new_fields: change = "added"
            else: change = "replaced_or_legacy_only"
            comparison.append({"document_type": document_type, "field": field, "v1_state": "present" if field in old_fields else "absent", "v2_state": "present" if field in new_fields else "absent", "change": change, "reason": "Separate semantic role and stable nullable contract."})
    with (out / "schema_v1_vs_v2.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(comparison[0].keys()); writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(comparison)

    collisions = [
        ("buyer", "consignee", "Buyer and Consignee are separate party roles", "same broad party blocks", "retain separate fields; use document label and section"),
        ("seller", "exporter / shipper", "seller/exporter/shipper may refer to related but not identical roles", "party role swap", "retain role-specific fields and cross-document mapping"),
        ("invoice_number", "bl_number / lc_number / reference_number", "identifier labels are not interchangeable", "wrong identifier assignment", "field-specific aliases and bounded label sections"),
        ("invoice_date", "lc_date / departure_date / shipment_date", "dates have different semantic events", "date event collision", "event-specific labels and typed date candidates"),
        ("port_of_loading", "port_of_discharge", "both are place-like values but opposite events", "loading/discharge swap", "anchor-relative section boundaries"),
        ("description", "hs_code / shipping_mark", "text columns can look like product descriptions", "item-table contamination", "table header/column relation and typed cells"),
        ("gross_weight", "net_weight", "both are numeric weights", "weight-role collision", "role-specific weight anchor and unit relation"),
        ("currency", "currency symbol in amount", "symbol alone does not prove document currency", "currency inference", "explicit currency evidence or null"),
    ]
    with (out / "semantic_collision_analysis.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["source_role", "conflicting_role", "example_labels", "risk", "recommended_schema_split"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows({"source_role": a, "conflicting_role": b, "example_labels": c, "risk": d, "recommended_schema_split": e} for a,b,c,d,e in collisions)

    report = {
        "datasets": {name: {"path": str(root), "documents": len(load_cases(name, root))} for name, root in datasets},
        "selected_case_rows": len(cases), "schema_fields": len(FIELD_DEFS),
        "coverage_rows": len(coverage_rows), "label_synonym_rows": len(synonym_rows),
        "note": "Coverage is an OCR-only label/value proximity estimate, not extractor accuracy and not Gold validity.",
    }
    (out / "schema_v2_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
