from fintra_ocr.field_extraction import extract_fields, find_label_spans
from fintra_ocr.gt_recall import evaluate_gt_recall
from fintra_ocr.label_bbox import OCRBoundingBox
from fintra_ocr.ocr_backends import _deduplicate_predictions, _focus_regions, _tile_starts
from fintra_ocr.prediction_parser import OCRPrediction
from fintra_ocr.target_scope import FINTRA_FORM_TYPES


def p(text, left, top, right, bottom=None, score=.9):
    if bottom is None:
        bottom = top + 20
    return OCRPrediction(text, (left, right, right, left), (top, top, bottom, bottom), score)


def g(text, left, top, right, bottom):
    return OCRBoundingBox('g', text, (left, right, right, left), (top, top, bottom, bottom))


def test_fuzzy_label_does_not_turn_bill_of_into_bill_to_buyer():
    predictions = [
        p('Bill', 10, 10, 40), p('of', 45, 10, 60), p('Lading', 65, 10, 120),
        p('Buyer', 10, 50, 60), p('ACME', 100, 50, 150), p('CORP', 155, 50, 210),
    ]
    fields = extract_fields('상업송장', predictions)
    assert fields['buyer'].value == 'ACME CORP'


def test_buyer_reference_header_is_skipped_and_company_line_is_expanded():
    predictions = [
        p('Buyer', 500, 10, 550), p('Reference', 560, 10, 640), p('ABC123', 650, 10, 720),
        p('Buyer', 500, 60, 550), p('(If', 560, 60, 590), p('not', 595, 60, 625), p('Consignee)', 630, 60, 710),
        p('Dentauri', 500, 90, 570), p('Health', 580, 90, 640), p('Solutions', 650, 90, 730),
    ]
    fields = extract_fields('상업송장', predictions)
    assert fields['buyer'].value == 'Dentauri Health Solutions'


def test_departure_date_is_not_used_as_invoice_date():
    fields = extract_fields('상업송장', [
        p('Invoice Number', 10, 10, 120), p('ABC123', 140, 10, 210),
        p('Date', 400, 400, 450), p('of', 455, 400, 475), p('Departure', 480, 400, 560),
        p('25-Jan-2004', 400, 430, 520),
    ])
    assert fields['date'].status == 'missing'


def test_invoice_total_wins_over_line_item_amount_header():
    fields = extract_fields('상업송장', [
        p('Description of Goods', 10, 100, 180), p('Amount', 400, 100, 470),
        p('Widget', 10, 140, 100), p('$100.00', 400, 140, 470),
        p('TOTAL', 300, 500, 360), p('$1,216.98', 400, 500, 500),
    ])
    assert fields['amount'].value == '$1,216.98'


def test_tall_table_header_does_not_merge_with_row_above():
    predictions = [
        p('ITALY', 10, 865, 60, 883),
        p('Description', 100, 879, 190, 955), p('of', 195, 879, 215, 955), p('Goods', 220, 879, 270, 955),
        p('LENS', 100, 999, 160, 1020),
    ]
    spans = find_label_spans(predictions, 'goods_description')
    assert any('Description' in span.text and 'Goods' in span.text for span in spans)
    fields = extract_fields('상업송장', predictions)
    assert fields['goods_description'].value == 'LENS'


def test_tile_starts_cover_last_edge_and_deduplicate_overlap():
    assert _tile_starts(1654, 1280, 160) == [0, 374]
    first = p('Invoice', 10, 10, 100, 40, .8)
    duplicate = p('Invoice', 12, 11, 102, 41, .95)
    other = p('Number', 110, 10, 190, 40, .9)
    merged = _deduplicate_predictions([first, duplicate, other])
    assert len(merged) == 2
    assert any(item.score == .95 and item.text == 'Invoice' for item in merged)


def test_segmentation_aware_recall_accepts_gt_inside_nearby_group():
    report = evaluate_gt_recall(
        [g('ABC123', 10, 10, 80, 30)],
        [p('REF', 5, 10, 25, 30), p('ABC123', 30, 10, 80, 30)],
    )
    assert report.segmentation_aware_recall == 1.0


def test_focus_regions_are_generic_unique_and_inside_page():
    width, height = 1654, 2340
    regions = _focus_regions(width, height)
    assert len(regions) == 3
    assert len(regions) == len(set(regions))
    for left, top, right, bottom in regions:
        assert 0 <= left < right <= width
        assert 0 <= top < bottom <= height
        assert right - left >= 256
        assert bottom - top >= 192


def test_focus_regions_skip_tiny_images():
    assert _focus_regions(500, 700) == []


def test_rescale_predictions_maps_upscaled_crop_back_to_page_coordinates():
    from fintra_ocr.ocr_backends import _rescale_predictions
    p = OCRPrediction("53 KG", (100, 200, 200, 100), (40, 40, 80, 80), 0.99)
    [mapped] = _rescale_predictions([p], 2.0, left=300, top=500)
    assert mapped.x == (350, 400, 400, 350)
    assert mapped.y == (520, 520, 540, 540)


def test_invoice_total_amount_column_fails_closed_instead_of_taking_unit_price():
    predictions = [
        OCRPrediction("Q-TY OF", (340, 420, 420, 340), (400, 400, 430, 430), 0.99),
        OCRPrediction("PRICE PER", (430, 500, 500, 430), (400, 400, 430, 430), 0.99),
        OCRPrediction("TOTAL AMOUNT", (520, 650, 650, 520), (400, 400, 430, 430), 0.99),
        OCRPrediction("30", (360, 395, 395, 360), (500, 500, 525, 525), 0.99),
        OCRPrediction("220", (440, 480, 480, 440), (500, 500, 525, 525), 0.99),
        OCRPrediction("TOTAL", (140, 240, 240, 140), (640, 640, 665, 665), 0.99),
    ]
    fields = extract_fields("상업송장", predictions)
    assert fields["amount"].status == "missing"


def test_party_caption_guard_rejects_address_label_as_buyer():
    predictions = [
        OCRPrediction("Buyer", (10, 100, 100, 10), (100, 100, 125, 125), 0.99),
        OCRPrediction("Address/Adpec:", (120, 280, 280, 120), (100, 100, 125, 125), 0.99),
    ]
    fields = extract_fields("상업송장", predictions)
    assert fields["buyer"].status == "missing"


def test_party_caption_guard_rejects_distorted_aihub_empty_party_instruction():
    predictions = [
        OCRPrediction("CONSIGNEE", (10, 100, 100, 10), (100, 100, 125, 125), 0.99),
        OCRPrediction("Tlease proydde compleee name", (120, 360, 360, 120), (100, 100, 125, 125), 0.64),
    ]
    fields = extract_fields(next(item for item in FINTRA_FORM_TYPES if "증권" in item), predictions)
    assert fields["consignee"].status == "missing"


def test_generic_total_does_not_promote_small_fragment_over_explicit_money_token():
    predictions = [
        p("Total", 10, 100, 70),
        p("4", 90, 100, 110),
        p("$655777", 300, 300, 380),
    ]
    fields = extract_fields(next(item for item in FINTRA_FORM_TYPES if "상업" in item), predictions)
    assert fields["amount"].status == "missing"
