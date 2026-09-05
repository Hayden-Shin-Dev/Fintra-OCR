import json
from pathlib import Path

from fintra_ocr.field_extraction import extract_fields
from fintra_ocr.normalization import normalize_fields
from fintra_ocr.prediction_parser import OCRPrediction

FIXTURE = Path(__file__).parent / "fixtures" / "v2_real_ocr_problem_cases.json"


def _docs():
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    output = {}
    for row in rows:
        predictions = [
            OCRPrediction(
                item["text"],
                tuple(point[0] for point in item["bbox"]),
                tuple(point[1] for point in item["bbox"]),
                item["confidence"],
            )
            for item in row["ocr_predictions"]
        ]
        output[row["document_id"]] = normalize_fields(extract_fields(row["form_type"], predictions))
    return output


def test_real_invoice_failures_are_fixed():
    d = _docs()
    first = d["IMG_OCR_6_T_NV_000322"]
    assert first["invoice_no"].value == "670837"
    assert first["amount"].normalized["value"] == 39583.47
    assert first["buyer"].value == "Dentauri Health Solutions"
    assert first["date"].status == "missing"  # this template has no invoice-date field

    compound = d["IMG_OCR_6_T_NV_002734"]
    assert compound["invoice_no"].value == "236622"
    assert compound["date"].normalized == "2011-01-22"
    assert compound["amount"].normalized["value"] == 1761.70
    assert compound["buyer"].value == "U&E Dominion Strategies Co., Ltd."

    issue_date = d["IMG_OCR_6_T_NV_003157"]
    assert issue_date["date"].normalized == "2007-10-22"  # OCR 0ct -> Oct repair
    assert issue_date["buyer"].status == "ambiguous"
    assert issue_date["buyer"].value == "Nobile Advance Co., Ltd."
    assert issue_date["amount"].normalized["value"] == 2406.33

    dedup = d["IMG_OCR_6_T_NV_004574"]
    assert dedup["date"].normalized == "2016-07-16"
    assert dedup["buyer"].value == "Chugai Pharmaceutical Co., Ltd."
    assert dedup["amount"].normalized["value"] == 5107.56


def test_real_packing_totals_and_ocr_confusion_are_fixed():
    d = _docs()
    first = d["IMG_OCR_6_T_PL_001573"]
    assert first["invoice_no"].value == "25810-8046-2344"
    assert first["number_of_packages"].normalized == {"value": 19, "unit": "CTN"}
    assert first["gross_weight"].normalized == {"value": 18, "unit": "KG"}
    assert [item["value"] for item in first["quantity"].normalized["items"]] == [4, 5, 4]

    confused = d["IMG_OCR_6_T_PL_001943"]
    assert confused["number_of_packages"].normalized == {"value": 59, "unit": "CTN"}
    assert confused["gross_weight"].normalized == {"value": 80, "unit": "KG"}


def test_real_bill_of_lading_layouts_are_fixed_without_fabricating_shipper():
    d = _docs()
    standard = d["IMG_OCR_6_T_BL_001677"]
    assert standard["shipper"].status == "missing"  # no reliable shipper label in this OCR layout
    assert standard["consignee"].value == "D&P GUYS MANUFACTURING CO., LTD."
    assert standard["number_of_packages"].normalized == {"value": 22, "unit": "PKG"}
    assert standard["gross_weight"].status == "ambiguous"  # multiple item weights, no total
    assert "GEAR SET, FAN DRIVE" in standard["goods_description"].value

    multi = d["IMG_OCR_6_T_BL_002596"]
    assert multi["shipper"].value == "HRAVY ANALYTICS"
    assert multi["consignee"].value == "DITCOIN OF AMERICA"
    assert multi["gross_weight"].normalized == {"value": 55, "unit": "KG"}
    assert multi["on_board_date"].normalized == "2021-12-10"
    assert "ELBOW, HOSE" in multi["goods_description"].value

    laden = d["IMG_OCR_6_T_BL_003578"]
    assert laden["number_of_packages"].normalized == {"value": 56, "unit": "BUNDLES"}
    assert laden["gross_weight"].normalized == {"value": 690, "unit": "KG"}
    assert laden["on_board_date"].normalized == "2017-04-10"

    multi2 = d["IMG_OCR_6_T_BL_004826"]
    assert multi2["shipper"].value == "NIFESCAPE ASSOCIATES"
    assert multi2["consignee"].value == "KAMADAI YAKKYOKU"
    assert multi2["gross_weight"].normalized == {"value": 38, "unit": "KG"}
    assert multi2["on_board_date"].normalized == "2009-07-17"


def test_real_fail_closed_and_total_column_regressions():
    d = _docs()
    occluded = d["IMG_OCR_6_T_NV_003382"]
    assert occluded["amount"].status == "missing"  # TOTAL AMOUNT cell is blank; 220 is unit price
    assert occluded["buyer"].status == "missing"   # Address/Adpec: is a caption, not a company

    assert d["IMG_OCR_6_T_PL_000554"]["gross_weight"].normalized == {"value": 747, "unit": "KG"}
    assert d["IMG_OCR_6_T_PL_001587"]["gross_weight"].normalized == {"value": 702, "unit": "KG"}
    assert d["IMG_OCR_6_T_PL_002061"]["gross_weight"].normalized == {"value": 578, "unit": "KG"}
    assert d["IMG_OCR_6_T_PL_004423"]["gross_weight"].normalized == {"value": 380, "unit": "KG"}
