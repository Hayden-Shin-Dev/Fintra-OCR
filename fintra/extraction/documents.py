"""Conservative, evidence-preserving document field extraction rules."""

from __future__ import annotations

import re
from collections import defaultdict
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


def _combined_evidence(regions: list[OCRRegion], *, value: str | None = None) -> EvidenceField:
    if not regions:
        return missing()
    text = value if value is not None else " ".join(region.text.strip() for region in regions if region.text.strip())
    polygon = [[min(region.bbox[0] for region in regions), min(region.bbox[1] for region in regions)],
               [max(region.bbox[2] for region in regions), min(region.bbox[1] for region in regions)],
               [max(region.bbox[2] for region in regions), max(region.bbox[3] for region in regions)],
               [min(region.bbox[0] for region in regions), max(region.bbox[3] for region in regions)]]
    confidences = [region.confidence for region in regions if region.confidence is not None]
    return evidence(text, source_text=" ".join(region.text for region in regions), bbox=polygon,
                    confidence=sum(confidences) / len(confidences) if confidences else None)


def _in_zone(result: OCRResult, *, x1: float, x2: float, y1: float, y2: float) -> list[OCRRegion]:
    return [region for region in _regions(result)
            if region.bbox[0] >= x1 and region.bbox[2] <= x2 and region.bbox[1] >= y1 and region.bbox[3] <= y2]


def _token_value(regions: list[OCRRegion], pattern: str) -> EvidenceField:
    matches = [region for region in regions if re.fullmatch(pattern, region.text.strip(), re.I)]
    if len(matches) == 1:
        return _evidence_from_region(matches[0], matches[0].text)
    if len(matches) > 1:
        unique_values = {_canonical(region.text) for region in matches}
        if len(unique_values) == 1:
            return _combined_evidence(matches, value=matches[0].text)
        return ambiguous(source_text=" | ".join(region.text for region in matches))
    return missing()


def _row_centers(regions: list[OCRRegion], *, minimum: float = 20) -> list[float]:
    centers: list[float] = []
    for region in sorted(regions, key=lambda item: (item.bbox[1], item.bbox[0])):
        center = (region.bbox[1] + region.bbox[3]) / 2
        if not centers or center - centers[-1] > minimum:
            centers.append(center)
    return centers


def _near_row(regions: list[OCRRegion], center: float, tolerance: float = 38) -> list[OCRRegion]:
    return [region for region in regions if abs((region.bbox[1] + region.bbox[3]) / 2 - center) <= tolerance]


def _item_from_columns(regions: list[OCRRegion], center: float, columns: tuple[tuple[float, float], ...]) -> LineItem:
    values = []
    for x1, x2 in columns:
        selected = sorted((region for region in _near_row(regions, center) if x1 <= region.bbox[0] <= x2), key=lambda item: item.bbox[0])
        values.append(_combined_evidence(selected))
    return LineItem(description=values[0], quantity=values[1], unit=values[2], unit_price=values[3], amount=values[4])


def _invoice_layout(result: OCRResult) -> dict[str, EvidenceField | list[LineItem]]:
    # Coordinates are the stable 1654x2340 AI-Hub Commercial Invoice template.
    values = _regions(result)
    item_regions = [region for region in values if 1000 <= region.bbox[1] <= 1400]
    centers = _row_centers([region for region in item_regions if 820 <= region.bbox[0] <= 950], minimum=45)
    items = [_item_from_columns(item_regions, center, ((120, 700), (820, 950), (950, 1100), (1100, 1260), (1260, 1520))) for center in centers]
    currency = _token_value(values, r"USD|EUR|GBP|JPY|CNY|KRW")
    total_regions = [region for region in values if 1200 <= region.bbox[0] and 1450 <= region.bbox[1] <= 1650 and re.search(r"\d", region.text)]
    return {
        "invoice_number": _combined_evidence(_in_zone(result, x1=850, x2=1320, y1=250, y2=360)),
        "invoice_date": _combined_evidence(_in_zone(result, x1=850, x2=1450, y1=360, y2=455)),
        "seller": _combined_evidence(_in_zone(result, x1=100, x2=850, y1=280, y2=520)),
        "buyer": _combined_evidence(_in_zone(result, x1=100, x2=850, y1=540, y2=760)),
        "currency": currency,
        "total_amount": _combined_evidence(total_regions),
        "items": items,
    }


def _packing_layout(result: OCRResult) -> dict[str, EvidenceField | list[LineItem]]:
    values = _regions(result)
    item_regions = [region for region in values if 1000 <= region.bbox[1] <= 1520]
    centers = _row_centers([region for region in item_regions if 800 <= region.bbox[0] <= 950], minimum=45)
    items = []
    for center in centers:
        row = _near_row(item_regions, center, tolerance=42)
        description = _combined_evidence([region for region in row if region.bbox[0] < 730])
        quantity = _combined_evidence([region for region in row if 800 <= region.bbox[0] <= 950 and re.fullmatch(r"\d+(?:[.,]\d+)?", region.text.strip())])
        unit = _combined_evidence([region for region in row if 800 <= region.bbox[0] <= 950 and not re.fullmatch(r"\d+(?:[.,]\d+)?", region.text.strip())])
        items.append(LineItem(description=description, quantity=quantity, unit=unit))
    package_regions = _in_zone(result, x1=350, x2=650, y1=1650, y2=1825)
    gross_regions = [region for region in values if 400 <= region.bbox[0] <= 700 and 1750 <= region.bbox[1] <= 1850 and re.search(r"\d", region.text)]
    gross = _combined_evidence(gross_regions)
    weight_unit = _token_value(values, r"KG|KGS|G|GRAM|GRAMS")
    if weight_unit.status == "missing" and gross.status == "extracted":
        match = re.search(r"\b(KG|KGS|G)\b", str(gross.value), re.I)
        if match:
            weight_unit = evidence(match.group(1).upper(), source_text=gross.source_text, bbox=gross.bbox)
    return {
        "packing_list_number": missing("template_field_not_present"),
        "date": _combined_evidence(_in_zone(result, x1=1150, x2=1500, y1=170, y2=280)),
        "exporter": _combined_evidence(_in_zone(result, x1=100, x2=800, y1=280, y2=450)),
        "consignee": _combined_evidence(_in_zone(result, x1=100, x2=750, y1=480, y2=700)),
        "items": items,
        "package_count": _combined_evidence(package_regions),
        "gross_weight": gross,
        "net_weight": ambiguous(source_text="multiple per-item net weights; no single total"),
        "weight_unit": weight_unit,
    }


def _bl_layout(result: OCRResult) -> dict[str, EvidenceField]:
    values = _regions(result)
    goods = [region for region in values if 500 <= region.bbox[0] <= 1100 and 1080 <= region.bbox[1] <= 1500]
    gross_values = [region for region in values if 1100 <= region.bbox[0] <= 1300 and 1080 <= region.bbox[1] <= 1500 and re.search(r"\d", region.text)]
    weight_unit = _token_value(values, r"KG|KGS|G|GRAM|GRAMS")
    if weight_unit.status == "missing":
        kg = [region for region in gross_values if re.search(r"KG", region.text, re.I)]
        if kg:
            weight_unit = evidence("KG", source_text=" ".join(region.text for region in kg), bbox=kg[0].polygon)
    return {
        "bl_number": _combined_evidence(_in_zone(result, x1=1150, x2=1500, y1=200, y2=300)),
        "shipper": missing("template_field_not_present"),
        "consignee": ambiguous(source_text="two consignee blocks in the source template"),
        "notify_party": _combined_evidence(_in_zone(result, x1=70, x2=800, y1=600, y2=800)),
        "vessel": _combined_evidence(_in_zone(result, x1=70, x2=400, y1=850, y2=980)),
        "port_of_loading": _combined_evidence(_in_zone(result, x1=400, x2=800, y1=850, y2=980)),
        "port_of_discharge": _combined_evidence(_in_zone(result, x1=70, x2=400, y1=950, y2=1080)),
        "shipment_date": missing("template_field_not_present"),
        "package_count": ambiguous(source_text="multiple package rows and total in the source template"),
        "gross_weight": ambiguous(source_text="multiple gross-weight rows in the source template"),
        "weight_unit": weight_unit,
        "goods_description": _combined_evidence(goods),
    }


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


def extract_commercial_invoice_legacy(result: OCRResult) -> CommercialInvoice:
    layout = _invoice_layout(result)
    return CommercialInvoice(
        metadata=_metadata(result),
        invoice_number=_find_field(result, ("invoice no", "invoice number", "inv no")) if _find_field(result, ("invoice no", "invoice number", "inv no")).status != "missing" else layout["invoice_number"],
        invoice_date=_find_field(result, ("date", "invoice date")) if _find_field(result, ("date", "invoice date")).status != "missing" else layout["invoice_date"],
        seller=_find_field(result, ("seller", "exporter")) if _find_field(result, ("seller", "exporter")).status != "missing" else layout["seller"],
        buyer=_find_field(result, ("buyer", "consignee", "importer")) if _find_field(result, ("buyer", "consignee", "importer")).status != "missing" else layout["buyer"],
        currency=_find_field(result, ("currency", "currency code")) if _find_field(result, ("currency", "currency code")).status != "missing" else layout["currency"],
        total_amount=_find_field(result, ("total", "total amount", "invoice total")) if _find_field(result, ("total", "total amount", "invoice total")).status != "missing" else layout["total_amount"],
        items=_items(result) or layout["items"],
    )


def extract_packing_list_legacy(result: OCRResult) -> PackingList:
    layout = _packing_layout(result)
    return PackingList(
        metadata=_metadata(result),
        packing_list_number=layout["packing_list_number"],
        date=layout["date"],
        exporter=layout["exporter"],
        consignee=layout["consignee"],
        items=layout["items"],
        package_count=layout["package_count"],
        gross_weight=layout["gross_weight"],
        net_weight=layout["net_weight"],
        weight_unit=layout["weight_unit"],
    )


def extract_bill_of_lading_legacy(result: OCRResult) -> BillOfLading:
    layout = _bl_layout(result)
    return BillOfLading(
        metadata=_metadata(result),
        bl_number=layout["bl_number"], shipper=layout["shipper"], consignee=layout["consignee"],
        notify_party=layout["notify_party"], vessel=layout["vessel"], port_of_loading=layout["port_of_loading"],
        port_of_discharge=layout["port_of_discharge"], shipment_date=layout["shipment_date"],
        package_count=layout["package_count"], gross_weight=layout["gross_weight"],
        weight_unit=layout["weight_unit"], goods_description=layout["goods_description"],
    )


def _refine(result, document):
    from .refinement import typed_refinement, ordered_refinement
    return ordered_refinement(result, typed_refinement(result, document))


def extract_commercial_invoice(result: OCRResult) -> CommercialInvoice:
    return _refine(result, extract_commercial_invoice_legacy(result))


def extract_packing_list(result: OCRResult) -> PackingList:
    return _refine(result, extract_packing_list_legacy(result))


def extract_bill_of_lading(result: OCRResult) -> BillOfLading:
    return _refine(result, extract_bill_of_lading_legacy(result))


EXTRACTORS: dict[str, Callable[[OCRResult], object]] = {
    "Commercial Invoice": extract_commercial_invoice,
    "Packing List": extract_packing_list,
    "B/L": extract_bill_of_lading,
}
