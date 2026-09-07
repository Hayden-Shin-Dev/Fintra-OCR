from fintra.extraction.v2 import extract_document
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
    assert payload["invoice_number"]["value"] == "ABC-123"
    assert payload["seller"]["value"] == "ACME TRADING CO LTD"
    assert payload["items"][0]["description"]["value"] == "WIDGET"
    assert payload["items"][0]["quantity"]["value"] == "2"
    assert payload["items"][0]["amount"]["value"] == "20.00"
    assert payload["items"][0]["description"]["bbox"]
    assert payload["items"][0]["description"]["source_text"] == "WIDGET"


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
