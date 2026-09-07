"""Clean-room extraction engine.

One path is used for every field: normalized layout, semantic anchors,
typed candidates, ranking, and evidence-bearing canonical output.
"""

from __future__ import annotations

from fintra.domain.schema import BillOfLading, CommercialInvoice, DocumentMetadata, EvidenceField, PackingList, evidence, missing
from fintra.ocr.adapter import OCRResult

from .layout import Layout
from .party import resolve as resolve_party
from .scalar import resolve as resolve_scalar
from .table import resolve as resolve_table, resolve_goods_description


def _metadata(result: OCRResult, kind: str) -> DocumentMetadata:
    return DocumentMetadata(result.document_id, kind, source_file=result.source_file, extraction_status="extracted")


def _party(layout: Layout, field: str) -> EvidenceField:
    return resolve_party(layout, field)


def _scalar(layout: Layout, field: str) -> EvidenceField:
    return resolve_scalar(layout, field)


def _items(layout: Layout):
    return resolve_table(layout)


def extract_commercial_invoice(result: OCRResult) -> CommercialInvoice:
    layout = Layout(result)
    return CommercialInvoice(
        metadata=_metadata(result, "Commercial Invoice"),
        invoice_number=_scalar(layout, "invoice_number"),
        invoice_date=_scalar(layout, "invoice_date"),
        seller=_party(layout, "seller"),
        buyer=_party(layout, "buyer"),
        currency=_scalar(layout, "currency"),
        total_amount=_scalar(layout, "total_amount"),
        items=_items(layout),
    )


def extract_packing_list(result: OCRResult) -> PackingList:
    layout = Layout(result)
    return PackingList(
        metadata=_metadata(result, "Packing List"),
        packing_list_number=_scalar(layout, "packing_list_number"),
        date=_scalar(layout, "date"),
        exporter=_party(layout, "exporter"),
        consignee=_party(layout, "consignee"),
        items=_items(layout),
        package_count=_scalar(layout, "package_count"),
        gross_weight=_scalar(layout, "gross_weight"),
        net_weight=_scalar(layout, "net_weight"),
        weight_unit=_scalar(layout, "weight_unit"),
    )


def extract_bill_of_lading(result: OCRResult) -> BillOfLading:
    layout = Layout(result)
    goods = _scalar(layout, "goods_description")
    inferred_goods = resolve_goods_description(layout)
    if inferred_goods.status.value == "extracted":
        goods = inferred_goods
    return BillOfLading(
        metadata=_metadata(result, "B/L"),
        bl_number=_scalar(layout, "bl_number"),
        shipper=_party(layout, "shipper"),
        consignee=_party(layout, "consignee"),
        notify_party=_party(layout, "notify_party"),
        vessel=_scalar(layout, "vessel"),
        port_of_loading=_scalar(layout, "port_of_loading"),
        port_of_discharge=_scalar(layout, "port_of_discharge"),
        shipment_date=_scalar(layout, "shipment_date"),
        package_count=_scalar(layout, "package_count"),
        gross_weight=_scalar(layout, "gross_weight"),
        weight_unit=_scalar(layout, "weight_unit"),
        goods_description=goods,
    )


EXTRACTORS = {
    "Commercial Invoice": extract_commercial_invoice,
    "Packing List": extract_packing_list,
    "B/L": extract_bill_of_lading,
}

__all__ = ["EXTRACTORS", "extract_commercial_invoice", "extract_packing_list", "extract_bill_of_lading"]
