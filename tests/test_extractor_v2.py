from fintra.extraction.v2 import extract_document
from fintra.extraction.v2.baseline import extract_baseline
from fintra.extraction.v2.party import resolve as resolve_party
from fintra.extraction.v2.table import _inferred_items
from fintra.extraction.v2.layout import Layout
from fintra.extraction.v2.overlay import apply as apply_overlay
from fintra.extraction.v2.specs import DOCUMENT_FIELDS, PARTY_FIELDS_BY_DOCUMENT, SPECS
from fintra.ocr.adapter import OCRRegion, OCRResult


def region(index, x1, y1, x2, y2, text):
    return OCRRegion([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], text, index=index)


def invoice_result():
    regions = [
        region(0, 0, 0, 80, 20, "INVOICE NO"),
        region(1, 100, 0, 220, 20, "ABC-123"),
        region(2, 0, 40, 60, 60, "SELLER"),
        region(3, 80, 40, 240, 60, "ACME TRADING CO LTD"),
        region(4, 0, 100, 80, 120, "DESCRIPTION"),
        region(5, 100, 100, 145, 120, "QTY"),
        region(6, 170, 100, 240, 120, "UNIT PRICE"),
        region(7, 270, 100, 330, 120, "AMOUNT"),
        region(8, 0, 130, 80, 150, "WIDGET"),
        region(9, 100, 130, 145, 150, "2"),
        region(10, 170, 130, 240, 150, "10.00"),
        region(11, 270, 130, 330, 150, "20.00"),
    ]
    return OCRResult("invoice-1", "Commercial Invoice", "invoice.png", regions, metadata={"page_width": 330, "page_height": 180})


def test_v2_uses_inline_and_typed_table_evidence():
    payload = extract_document(invoice_result()).to_dict()
    baseline = extract_baseline(invoice_result())
    assert payload["invoice_number"]["value"] == "ABC-123"
    assert baseline["seller"]["value"] is None
    assert payload["seller"]["value"] == "ACME TRADING CO LTD"
    assert payload["items"][0]["description"]["value"] == baseline["items"][0]["description"]["value"]
    assert payload["items"][0]["quantity"]["value"] == baseline["items"][0]["quantity"]["value"]
    assert payload["items"][0]["amount"]["value"] == baseline["items"][0]["amount"]["value"]
    assert payload["items"][0]["description"]["bbox"]
    assert payload["items"][0]["description"]["source_text"] == "WIDGET"


def test_v2_headerless_three_number_row_keeps_quantity():
    regions = [
        region(0, 0, 0, 100, 20, "WIDGET"),
        region(1, 120, 0, 150, 20, "10"),
        region(2, 180, 0, 230, 20, "5.00"),
        region(3, 260, 0, 320, 20, "50.00"),
    ]
    result = OCRResult("table-1", "Commercial Invoice", "table.png", regions, metadata={"page_width": 320, "page_height": 40})
    items = _inferred_items(Layout(result), "Commercial Invoice")
    assert items[0]["quantity"]["value"] == "10"
    assert items[0]["unit_price"]["value"] == "5.00"
    assert items[0]["amount"]["value"] == "50.00"


def test_v2_contract_keeps_nullable_fields_and_document_type():
    payload = extract_document(invoice_result()).to_dict()
    assert payload["schema_version"] == "fintra-audit-field-schema-v2"
    assert payload["document_type"] == "Commercial Invoice"
    assert "buyer" in payload
    assert payload["buyer"]["status"] in {"missing", "ambiguous", "extracted"}
    assert "items" in payload


def test_v2_does_not_guess_missing_party():
    payload = extract_document(invoice_result()).to_dict()
    assert payload["buyer"]["value"] is None
    assert payload["buyer"]["status"] == "missing"


def test_v2_same_as_role_is_not_cross_assigned():
    regions = [
        region(0, 0, 0, 90, 20, "SHIPPER"),
        region(1, 100, 0, 260, 20, "SAME AS CONSIGNEE"),
        region(2, 0, 40, 100, 60, "CONSIGNEE"),
        region(3, 110, 40, 260, 60, "ACME LOGISTICS LTD"),
    ]
    result = OCRResult("party-1", "B/L", "party.png", regions, metadata={"page_width": 300, "page_height": 100})
    layout = Layout(result)
    shipper = resolve_party(layout, "shipper")
    consignee = resolve_party(layout, "consignee")
    assert shipper["value"] != "SAME AS CONSIGNEE"
    assert consignee["value"] == "ACME LOGISTICS LTD"


def test_v2_overlay_does_not_replace_existing_baseline_value():
    result = invoice_result()
    baseline = extract_baseline(result)
    updated, diagnostics = apply_overlay(result, baseline)
    assert updated["invoice_number"]["value"] == baseline["invoice_number"]["value"]
    assert updated["invoice_number"]["candidate"]["semantic_anchor"] == "INVOICE NO"
    assert diagnostics["mode"] == "semantic_overlay"


def test_v2_layout_keeps_value_cell_even_if_it_matches_another_alias():
    result = OCRResult(
        "anchor-1",
        "Commercial Invoice",
        "anchor.png",
        [
            region(0, 0, 0, 80, 20, "BUYER"),
            region(1, 100, 0, 180, 20, "TOTAL"),
        ],
        metadata={"page_width": 200, "page_height": 40},
    )
    layout = Layout(result)
    anchors = layout.all_anchors({"buyer": SPECS["buyer"].aliases, "total_amount": SPECS["total_amount"].aliases})
    buyer = next(anchor for anchor in anchors if anchor.field == "buyer")
    adjacent = layout.adjacent(buyer, anchors)
    assert any(cell.text == "TOTAL" for cells, _relation, _distance in adjacent for cell in cells)


def test_v2_document_contract_scopes_party_roles_and_keeps_shipment_date():
    assert {"shipper", "consignee", "notify_party"}.issubset(set(PARTY_FIELDS_BY_DOCUMENT["B/L"]))
    assert "shipment_date" in DOCUMENT_FIELDS["B/L"]


def test_v2_party_rejects_consignee_as_fuzzy_shipper_heading():
    regions = [
        region(0, 0, 0, 90, 20, "CONSIGNEE"),
        region(1, 100, 0, 260, 20, "ACME CONSIGNEE LTD"),
    ]
    result = OCRResult("party-2", "B/L", "party2.png", regions, metadata={"page_width": 300, "page_height": 60})
    value = resolve_party(Layout(result), "shipper")
    assert value["value"] is None


def test_v2_party_block_uses_anchor_relative_right_column():
    result = OCRResult(
        "party-3",
        "B/L",
        "party3.png",
        [
            region(0, 700, 0, 800, 20, "SHIPPER"),
            region(1, 710, 40, 980, 60, "RIGHT COLUMN LOGISTICS LTD"),
        ],
        metadata={"page_width": 1000, "page_height": 100},
    )
    value = resolve_party(Layout(result), "shipper")
    assert value["value"] == "RIGHT COLUMN LOGISTICS LTD"
