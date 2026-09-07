from fintra.extraction.v2 import extract_document
from fintra.extraction.v2.baseline import extract_baseline
from fintra.extraction.v2.party import resolve as resolve_party
from fintra.extraction.v2.table import _inferred_items
from fintra.extraction.v2.layout import Layout
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
    assert payload["seller"] == baseline["seller"]
    assert payload["items"][0]["description"] == baseline["items"][0]["description"]
    assert payload["items"][0]["quantity"] == baseline["items"][0]["quantity"]
    assert payload["items"][0]["amount"] == baseline["items"][0]["amount"]
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
