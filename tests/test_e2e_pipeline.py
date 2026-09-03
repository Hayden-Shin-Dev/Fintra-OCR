from fintra_ocr.e2e_pipeline import build_document_from_predictions
from fintra_ocr.prediction_parser import OCRPrediction


def p(text, left, top, right, bottom):
    return OCRPrediction(text, (left, right, right, left), (top, top, bottom, bottom), 0.99)


def test_build_common_json_from_invoice_predictions():
    predictions = [
        p("Invoice No", 10, 10, 100, 30),
        p("ABC123", 10, 35, 100, 55),
        p("TOTAL", 10, 70, 80, 90),
        p("USD 5000", 10, 95, 100, 115),
    ]
    result = build_document_from_predictions("상업송장", "doc1", predictions)
    assert result.document["schema_version"] == "1.0"
    assert result.document["fields"]["invoice_no"]["value"] == "ABC123"
    assert result.document["fields"]["amount"]["normalized"]["value"] == 5000.0
