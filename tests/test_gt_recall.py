from fintra_ocr.gt_recall import evaluate_gt_recall
from fintra_ocr.label_bbox import OCRBoundingBox
from fintra_ocr.prediction_parser import OCRPrediction


def gt(text, left, top, right, bottom):
    return OCRBoundingBox("id", text, (left, right, right, left), (top, top, bottom, bottom))


def pred(text, left, top, right, bottom):
    return OCRPrediction(text, (left, right, right, left), (top, top, bottom, bottom), 0.9)


def test_gt_recall_recovers_split_prediction():
    report = evaluate_gt_recall(
        [gt("Quantity 100", 10, 10, 120, 30)],
        [pred("Quantity", 10, 10, 75, 30), pred("100", 80, 10, 120, 30), pred("STATIC LABEL", 200, 10, 300, 30)],
    )
    assert report.gt_boxes == 1
    assert report.exact_text_recall == 1.0
    assert report.similarity_90_recall == 1.0
    # Extra static labels are not counted as false positives.
    assert report.predicted_boxes == 3


def test_gt_recall_reports_missing_value():
    report = evaluate_gt_recall([gt("5000", 10, 10, 50, 30)], [])
    assert report.exact_text_recall == 0
    assert report.geometric_recall == 0
    assert report.mean_cer == 1
