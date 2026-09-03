"""Field-level oracle diagnostics using the dataset's GT value boxes.

The sample labels contain variable-value transcriptions/bboxes but may omit
static form captions. We therefore keep the OCR engine's static-label
predictions, replace OCR predictions overlapping annotated GT value regions
with perfect GT text, then rerun the same extractor.

This creates an *oracle-value* pass:
- actual fails, oracle succeeds -> OCR value recognition/detection degraded E2E
- both fail -> extractor/static-label/layout issue (not fixed by perfect values)
- both agree -> field survived OCR + extraction on this sample

It is a diagnostic proxy, not a human semantic annotation.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Mapping, Sequence

from .common_schema import build_common_document_from_form_type
from .field_extraction import extract_fields
from .label_bbox import OCRBoundingBox
from .normalization import normalize_fields
from .prediction_parser import OCRPrediction


def _bounds(item: OCRBoundingBox | OCRPrediction) -> tuple[int, int, int, int]:
    return min(item.x), min(item.y), max(item.x), max(item.y)


def _intersection_ratio_of_prediction(pred: OCRPrediction, gt: OCRBoundingBox) -> float:
    px1, py1, px2, py2 = _bounds(pred)
    gx1, gy1, gx2, gy2 = _bounds(gt)
    iw = max(0, min(px2, gx2) - max(px1, gx1))
    ih = max(0, min(py2, gy2) - max(py1, gy1))
    inter = iw * ih
    area = max(1, (px2-px1) * (py2-py1))
    return inter / area


def inject_ground_truth_values(
    predictions: Sequence[OCRPrediction],
    ground_truth: Sequence[OCRBoundingBox],
) -> list[OCRPrediction]:
    """Keep static OCR boxes, replace boxes on annotated value regions with GT."""
    static_predictions: list[OCRPrediction] = []
    for prediction in predictions:
        if any(_intersection_ratio_of_prediction(prediction, gt) >= 0.20 for gt in ground_truth):
            continue
        static_predictions.append(prediction)
    gt_predictions = [
        OCRPrediction(item.text, item.x, item.y, 1.0)
        for item in ground_truth if item.text.strip()
    ]
    return static_predictions + gt_predictions


def _normalized_payload(field: Mapping[str, object]) -> object:
    normalized = field.get("normalized")
    return normalized if normalized is not None else field.get("value")



def _canonical_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _text_agreement(first: object, second: object) -> float:
    a = _canonical_text(first)
    b = _canonical_text(second)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _description_agreement(first: object, second: object) -> float:
    """Compare free-text item lists without requiring identical OCR segmentation."""
    def items(value: object) -> list[str]:
        if isinstance(value, str):
            return [part for part in (_canonical_text(piece) for piece in value.split("|")) if part]
        return [_canonical_text(value)] if _canonical_text(value) else []
    left = items(first)
    right = items(second)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    # Symmetric best-item matching.  This tolerates Paddle splitting one item
    # into two boxes while still penalizing genuinely different descriptions.
    left_scores = [max(SequenceMatcher(None, item, other).ratio() for other in right) for item in left]
    right_scores = [max(SequenceMatcher(None, item, other).ratio() for other in left) for item in right]
    return (sum(left_scores) / len(left_scores) + sum(right_scores) / len(right_scores)) / 2


def _amount_agreement(first: object, second: object) -> float:
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        return 1.0 if first == second else 0.0
    if first.get("value") != second.get("value"):
        return 0.0
    first_code = first.get("currency_code")
    second_code = second.get("currency_code")
    if first_code and second_code and first_code != second_code:
        return 0.0
    return 1.0


def _field_agreement(field_name: str, first: object, second: object) -> float:
    if field_name == "goods_description":
        return _description_agreement(first, second)
    if field_name in {"buyer", "shipper", "consignee"}:
        return _text_agreement(first, second)
    if field_name == "amount":
        return _amount_agreement(first, second)
    if first == second:
        return 1.0
    # String IDs are compared after punctuation/case normalization, but digits
    # and letters are not substituted for one another (O/0 remains a mismatch).
    if field_name in {"invoice_no", "bl_no", "currency"}:
        return 1.0 if _canonical_text(first) == _canonical_text(second) else 0.0
    return 0.0


def _agreement_threshold(field_name: str) -> float:
    if field_name == "goods_description":
        return 0.72
    if field_name in {"buyer", "shipper", "consignee"}:
        return 0.82
    return 1.0


def _semantic_value_valid(field_name: str, value: object) -> bool:
    """Reject values that are structurally impossible for a Fintra field.

    This is intentionally conservative.  It does not claim a value is the true
    human answer; it only prevents the oracle from congratulating the extractor
    for obvious captions such as ``BILL`` or ``DESCRIPTION OF PACKAGES AND
    GOODS``.
    """
    if value is None:
        return False
    if field_name in {"invoice_no", "bl_no"}:
        text=_canonical_text(value)
        return len(text) >= 3 and any(ch.isdigit() for ch in text) and text not in {"and","date","number","invoice","bill"}
    if field_name in {"buyer", "shipper", "consignee"}:
        text=_canonical_text(value)
        if len(text) < 3 or not any(ch.isalpha() for ch in text):
            return False
        forbidden=(
            "bill of lading", "description of package", "description of goods",
            "particulars furnished", "gross weight", "booking no", "for delivery to",
            "shipper phone", "consignee phone", "notify party", "port and country",
        )
        if text in {"bill","bill o","consignee","shipper","buyer","exporter"}:
            return False
        return not any(marker in text for marker in forbidden)
    if field_name == "goods_description":
        text=_canonical_text(value)
        if len(text) < 2 or not any(ch.isalpha() for ch in text):
            return False
        return text not in {
            "description of goods", "description of package and goods",
            "description of packages and goods", "goods description",
        }
    if field_name == "amount":
        return isinstance(value, Mapping) and isinstance(value.get("value"), (int,float))
    if field_name == "currency":
        if isinstance(value, Mapping):
            return bool(value.get("code") or value.get("symbol"))
        return bool(_canonical_text(value))
    if field_name in {"gross_weight", "number_of_packages"}:
        return isinstance(value, Mapping) and isinstance(value.get("value"),(int,float)) and bool(value.get("unit"))
    if field_name == "quantity":
        return isinstance(value, Mapping) and isinstance(value.get("items"), list) and len(value.get("items")) > 0
    if field_name in {"date", "on_board_date"}:
        if isinstance(value, str):
            return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
        if isinstance(value, Mapping):
            return bool(value.get("candidates"))
        return False
    return True


@dataclass(frozen=True)
class FieldOracleDiagnostic:
    field_name: str
    actual_status: str
    oracle_status: str
    actual_value: object
    oracle_value: object
    classification: str
    agreement_score: float


def compare_actual_to_oracle(
    actual_document: Mapping[str, object],
    oracle_document: Mapping[str, object],
) -> dict[str, FieldOracleDiagnostic]:
    actual_fields = actual_document["fields"]  # type: ignore[index]
    oracle_fields = oracle_document["fields"]  # type: ignore[index]
    output: dict[str, FieldOracleDiagnostic] = {}
    for field_name in sorted(set(actual_fields) | set(oracle_fields)):  # type: ignore[arg-type]
        actual = actual_fields[field_name]  # type: ignore[index]
        oracle = oracle_fields[field_name]  # type: ignore[index]
        actual_status = str(actual["status"])
        oracle_status = str(oracle["status"])
        actual_value = _normalized_payload(actual)
        oracle_value = _normalized_payload(oracle)
        actual_valid = _semantic_value_valid(field_name, actual_value) if actual_status != "missing" else False
        oracle_valid = _semantic_value_valid(field_name, oracle_value) if oracle_status != "missing" else False
        agreement = 0.0

        if oracle_status == "missing":
            # GT does not carry semantic field identities, and some templates
            # genuinely omit a field.  Both-missing is therefore not an
            # extractor failure and must be excluded from accuracy denominators.
            classification = "both_missing_or_oracle_unavailable" if actual_status == "missing" else "oracle_unavailable_for_found_value"
        elif not oracle_valid:
            classification = "oracle_semantically_invalid"
        elif actual_status != "missing" and not actual_valid:
            classification = "semantic_validation_failure"
        else:
            agreement = _field_agreement(field_name, actual_value, oracle_value)
            if actual_status == oracle_status and agreement >= _agreement_threshold(field_name):
                classification = "e2e_matches_oracle"
            elif oracle_status == "found" and actual_status in {"missing", "ambiguous"}:
                classification = "ocr_value_degradation"
            elif oracle_status == "found" and actual_status == "found":
                classification = "ocr_or_extractor_value_mismatch"
            else:
                classification = "extractor_instability_or_ambiguity"
        output[field_name] = FieldOracleDiagnostic(
            field_name, actual_status, oracle_status, actual_value, oracle_value, classification, agreement
        )
    return output


def build_oracle_document(
    form_type: str,
    document_id: str,
    predictions: Sequence[OCRPrediction],
    ground_truth: Sequence[OCRBoundingBox],
) -> Mapping[str, object]:
    oracle_predictions = inject_ground_truth_values(predictions, ground_truth)
    fields = normalize_fields(extract_fields(form_type, oracle_predictions))
    return build_common_document_from_form_type(form_type, document_id, fields)
