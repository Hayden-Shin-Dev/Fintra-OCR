"""Conservative, evidence-preserving document field extraction rules."""

from __future__ import annotations

import re
from typing import Callable, Iterable

from fintra.domain.schema import (
    BillOfLading,
    CommercialInvoice,
    DocumentMetadata,
    EvidenceField,
    LineItem,
    PackingList,
    ambiguous,
    evidence,
    missing,
)
from fintra.ocr.adapter import OCRRegion, OCRResult


def _canonical(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def _regions(result: OCRResult) -> list[OCRRegion]:
    return sorted(result.regions, key=lambda item: (item.page, item.bbox[1], item.bbox[0], item.index))


def _evidence_from_region(region: OCRRegion, value: str) -> EvidenceField:
    return evidence(
        value.strip(),
        source_text=region.text,
        bbox=region.polygon,
        confidence=region.confidence,
    )


def _candidate_after_label(region: OCRRegion, aliases: Iterable[str]) -> str | None:
    text = region.text.strip()
    canonical = _canonical(text)
    for alias in aliases:
        alias_canonical = _canonical(alias)
        if canonical == alias_canonical:
            return None
        match = re.search(rf"\b{re.escape(alias_canonical)}\b\s*[:#-]?\s*(.+)$", canonical)
        if match:
            raw_match = re.search(r"[:#-]\s*(.+)$", text)
            return (raw_match.group(1) if raw_match else text[len(alias):]).strip()
    if ":" in text:
        left, right = text.split(":", 1)
        if _canonical(left) in {_canonical(alias) for alias in aliases} and right.strip():
            return right.strip()
    return None


def _find_field(result: OCRResult, aliases: tuple[str, ...]) -> EvidenceField:
    ordered = _regions(result)
    exact_regions = []
    for region in ordered:
        inline = _candidate_after_label(region, aliases)
        if inline:
            return _evidence_from_region(region, inline)
        if _canonical(region.text) in {_canonical(alias) for alias in aliases}:
            exact_regions.append(region)
    if len(exact_regions) > 1:
        return ambiguous(source_text=" | ".join(region.text for region in exact_regions))
    if not exact_regions:
        return missing()
    label = exact_regions[0]
    lx1, ly1, lx2, ly2 = label.bbox
    candidates = [
        region for region in ordered
        if region.index != label.index and region.page == label.page and region.text.strip()
    ]
    right = [region for region in candidates if region.bbox[0] >= lx2 - 2 and abs(region.bbox[1] - ly1) <= max(40, ly2 - ly1)]
    below = [region for region in candidates if region.bbox[1] >= ly2 - 2 and abs(region.bbox[0] - lx1) <= max(100, lx2 - lx1)]
    nearest = sorted(right or below, key=lambda region: (abs(region.bbox[1] - ly1), abs(region.bbox[0] - lx2)))
    return _evidence_from_region(nearest[0], nearest[0].text) if nearest else missing()


def _metadata(result: OCRResult) -> DocumentMetadata:
    return DocumentMetadata(
        document_id=result.document_id,
        document_type=result.document_type,
        source_file=result.source_file,
        extraction_status="extracted",
    )


def _items(result: OCRResult) -> list[LineItem]:
    items = []
    for region in _regions(result):
        match = re.match(r"ITEM\s*[:#-]?\s*(.+?)\s*[|;]\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)?(?:\s*[|;]\s*(.+?))?(?:\s*[|;]\s*(.+))?$", region.text, re.I)
        if not match:
            continue
        description, quantity, unit, unit_price, amount = match.groups()
        common = {"source_text": region.text, "bbox": region.polygon, "confidence": region.confidence}
        items.append(LineItem(
            description=evidence(description, **common),
            quantity=evidence(quantity, **common),
            unit=evidence(unit, **common),
            unit_price=evidence(unit_price, **common),
            amount=evidence(amount, **common),
        ))
    return items


def extract_commercial_invoice(result: OCRResult) -> CommercialInvoice:
    return CommercialInvoice(
        metadata=_metadata(result),
        invoice_number=_find_field(result, ("invoice no", "invoice number", "inv no")),
        invoice_date=_find_field(result, ("date", "invoice date")),
        seller=_find_field(result, ("seller", "exporter")),
        buyer=_find_field(result, ("buyer", "consignee", "importer")),
        currency=_find_field(result, ("currency", "currency code")),
        total_amount=_find_field(result, ("total", "total amount", "invoice total")),
        items=_items(result),
    )


def extract_packing_list(result: OCRResult) -> PackingList:
    return PackingList(
        metadata=_metadata(result),
        packing_list_number=_find_field(result, ("packing list no", "packing list number", "pl no")),
        date=_find_field(result, ("date", "packing date")),
        exporter=_find_field(result, ("exporter", "seller")),
        consignee=_find_field(result, ("consignee", "buyer")),
        items=_items(result),
        package_count=_find_field(result, ("package count", "packages", "total packages")),
        gross_weight=_find_field(result, ("gross weight",)),
        net_weight=_find_field(result, ("net weight",)),
        weight_unit=_find_field(result, ("weight unit",)),
    )


def extract_bill_of_lading(result: OCRResult) -> BillOfLading:
    return BillOfLading(
        metadata=_metadata(result),
        bl_number=_find_field(result, ("bl no", "b l no", "bill of lading no", "bl number")),
        shipper=_find_field(result, ("shipper",)),
        consignee=_find_field(result, ("consignee",)),
        notify_party=_find_field(result, ("notify party", "notify")),
        vessel=_find_field(result, ("vessel", "ship name")),
        port_of_loading=_find_field(result, ("port of loading", "pol")),
        port_of_discharge=_find_field(result, ("port of discharge", "pod")),
        shipment_date=_find_field(result, ("shipment date", "on board date", "shipped on board")),
        package_count=_find_field(result, ("package count", "packages")),
        gross_weight=_find_field(result, ("gross weight",)),
        weight_unit=_find_field(result, ("weight unit",)),
        goods_description=_find_field(result, ("goods description", "description of goods")),
    )


EXTRACTORS: dict[str, Callable[[OCRResult], object]] = {
    "Commercial Invoice": extract_commercial_invoice,
    "Packing List": extract_packing_list,
    "B/L": extract_bill_of_lading,
}
