"""Field-level regression evaluation for stored OCR predictions.

The evaluator deliberately separates three observations:

* the OCR result itself (raw predictions and detector timing),
* the field extractor result, and
* the oracle-value diagnostic already produced by the sample pipeline.

The sample annotations are value boxes rather than semantic field IDs.  A
valid ``oracle_fields`` entry is therefore used as an explicit diagnostic
proxy, and every result records ``oracle_proxy`` so it cannot be mistaken for
human field annotation ground truth.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
from time import perf_counter

from .common_schema import DOCUMENT_FIELD_KEYS, document_type_from_form_type
from .field_extraction import extract_fields
from .normalization import normalize_fields
from .oracle_validation import (
    _agreement_threshold,
    _field_agreement,
    _semantic_value_valid,
)
from .prediction_parser import OCRPrediction


def _payload(field: Mapping[str, object]) -> object:
    return field.get("normalized") if field.get("normalized") is not None else field.get("value")


def _prediction_list(row: Mapping[str, object]) -> list[OCRPrediction]:
    output: list[OCRPrediction] = []
    for item in row.get("ocr_predictions", []):
        box = item["bbox"]  # type: ignore[index]
        output.append(
            OCRPrediction(
                str(item["text"]),  # type: ignore[index]
                tuple(int(point[0]) for point in box),
                tuple(int(point[1]) for point in box),
                float(item["confidence"]),  # type: ignore[index]
            )
        )
    return output


def _raw_value_present(field_name: str, expected: Mapping[str, object], predictions: Sequence[OCRPrediction]) -> bool:
    """Whether the unmodified OCR contains a plausible expected value.

    This is intentionally a conservative proxy.  It checks OCR line spans and
    individual predictions using the same agreement thresholds as the oracle
    diagnostic, but does not invent a semantic field label for a GT box.
    """
    expected_value = _payload(expected)
    expected_raw = expected.get("raw_text") or expected_value
    if expected_value is None and not expected_raw:
        return False
    from .layout_reconstruction import reconstruct_layout

    texts = [prediction.text for prediction in predictions]
    texts.extend(line.text for line in reconstruct_layout(predictions).lines)
    threshold = _agreement_threshold(field_name)

    def raw_agrees(text: str) -> bool:
        candidate = text.casefold()
        if field_name == "amount" and isinstance(expected_value, Mapping):
            number = expected_value.get("value")
            if number is not None:
                numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", candidate)
                if any(float(item.replace(",", "")) == float(number) for item in numbers):
                    code = expected_value.get("currency_code")
                    return not code or str(code).casefold() in candidate
        if field_name == "currency" and isinstance(expected_value, Mapping):
            code = expected_value.get("code")
            symbol = expected_value.get("symbol")
            return bool((code and str(code).casefold() in candidate) or (symbol and str(symbol) in text))
        expected_text = str(expected_raw or expected_value or "")
        if field_name in {"date", "on_board_date"}:
            expected_text = re.sub(r"[^0-9a-z]", "", expected_text.casefold())
            candidate_text = re.sub(r"[^0-9a-z]", "", candidate)
            return bool(expected_text and expected_text in candidate_text)
        return _field_agreement(field_name, text, expected_value) >= threshold

    for text in texts:
        if raw_agrees(text):
            return True
    return False


def _classify_field(
    field_name: str,
    actual: Mapping[str, object],
    expected: Mapping[str, object],
    predictions: Sequence[OCRPrediction],
) -> dict[str, object]:
    actual_status = str(actual.get("status", "missing"))
    oracle_status = str(expected.get("status", "missing"))
    actual_value = _payload(actual)
    expected_value = _payload(expected)
    oracle_valid = oracle_status == "found" and _semantic_value_valid(field_name, expected_value)
    if not oracle_valid:
        return {
            "outcome": "unknown",
            "cause": "ORACLE_UNAVAILABLE",
            "oracle_proxy": False,
            "agreement": None,
        }

    agreement = _field_agreement(field_name, actual_value, expected_value) if actual_status != "missing" else 0.0
    if actual_status == "found" and agreement >= _agreement_threshold(field_name):
        return {"outcome": "correct", "cause": "NONE", "oracle_proxy": True, "agreement": agreement}
    if actual_status == "ambiguous":
        outcome = "ambiguous"
    elif actual_status == "missing":
        outcome = "missing"
    else:
        outcome = "wrong"

    present = _raw_value_present(field_name, expected, predictions)
    if outcome == "wrong" and present:
        cause = "WRONG_SELECTION"
    elif present:
        cause = "EXTRACTION_MISSING"
    else:
        cause = "OCR_MISSING"
    return {
        "outcome": outcome,
        "cause": cause,
        "oracle_proxy": True,
        "agreement": agreement,
    }


def _split_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, str]:
    """Stratified holdout split: last ceil(type_count / 3) by document ID."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[str(row["form_type"])].append(str(row["document_id"]))
    split: dict[str, str] = {}
    for form_type, document_ids in grouped.items():
        document_ids.sort()
        holdout_count = max(1, (len(document_ids) + 2) // 3)
        for document_id in document_ids[-holdout_count:]:
            split[document_id] = "holdout"
        for document_id in document_ids[:-holdout_count]:
            split[document_id] = "development"
    return split


def _field_metrics(results: Sequence[Mapping[str, object]]) -> dict[str, object]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    causes: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        key = str(result["form_type"])
        counters[key][str(result["outcome"])] += 1
        causes[key][str(result["cause"])] += 1
    return {
        "outcomes": {key: dict(value) for key, value in sorted(counters.items())},
        "causes": {key: dict(value) for key, value in sorted(causes.items())},
    }


def evaluate_prediction_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Evaluate baseline JSON fields against improved extraction on same OCR."""
    split = _split_rows(rows)
    field_results: list[dict[str, object]] = []
    document_results: list[dict[str, object]] = []
    extraction_times: list[float] = []

    for row in sorted(rows, key=lambda item: str(item["document_id"])):
        document_id = str(row["document_id"])
        form_type = str(row["form_type"])
        document_type = document_type_from_form_type(form_type)
        predictions = _prediction_list(row)
        started = perf_counter()
        improved_evidence = normalize_fields(extract_fields(form_type, predictions))
        extraction_seconds = perf_counter() - started
        extraction_times.append(extraction_seconds)
        improved_fields = {
            name: {
                "status": value.status,
                "value": value.value,
                "normalized": value.normalized,
                "raw_text": value.raw_text,
                "confidence": value.confidence,
            }
            for name, value in improved_evidence.items()
        }
        baseline_fields = row.get("fields", {})
        oracle_fields = row.get("oracle_fields", {})
        per_document: list[dict[str, object]] = []
        for field_name in sorted(DOCUMENT_FIELD_KEYS[document_type]):
            baseline = baseline_fields.get(field_name, {"status": "missing"})  # type: ignore[union-attr]
            improved = improved_fields.get(field_name, {"status": "missing"})
            expected = oracle_fields.get(field_name, {"status": "missing"})  # type: ignore[union-attr]
            baseline_class = _classify_field(field_name, baseline, expected, predictions)
            improved_class = _classify_field(field_name, improved, expected, predictions)
            result = {
                "document_id": document_id,
                "form_type": form_type,
                "document_type": document_type,
                "split": split[document_id],
                "field_name": field_name,
                "oracle_proxy": improved_class["oracle_proxy"],
                "expected": {"status": expected.get("status"), "value": _payload(expected)},
                "baseline": {
                    "status": baseline.get("status"),
                    "value": _payload(baseline),
                    **baseline_class,
                },
                "improved": {
                    "status": improved.get("status"),
                    "value": _payload(improved),
                    **improved_class,
                },
            }
            field_results.append(result)
            per_document.append(result)
        document_results.append({
            "document_id": document_id,
            "form_type": form_type,
            "split": split[document_id],
            "ocr_prediction_count": len(predictions),
            "ocr_elapsed_seconds": row.get("elapsed_seconds"),
            "field_extraction_seconds": extraction_seconds,
            "baseline_status_counts": dict(Counter(str(item["baseline"]["status"]) for item in per_document)),
            "improved_status_counts": dict(Counter(str(item["improved"]["status"]) for item in per_document)),
            "fields": per_document,
        })

    proxy_results = [item for item in field_results if item["oracle_proxy"]]
    baseline_flat = [{**item, **item["baseline"]} for item in proxy_results]
    improved_flat = [{**item, **item["improved"]} for item in proxy_results]
    return {
        "evaluation": "field_extractor_regression",
        "oracle_note": "oracle_fields are a GT-value-box diagnostic proxy, not semantic human field annotations",
        "document_count": len(rows),
        "field_result_count": len(field_results),
        "oracle_proxy_field_count": len(proxy_results),
        "split_counts": dict(Counter(split[ str(row["document_id"]) ] for row in rows)),
        "baseline": _field_metrics(baseline_flat),
        "improved": _field_metrics(improved_flat),
        "field_results": field_results,
        "document_results": document_results,
        "timing": {
            "field_extraction_mean_seconds": sum(extraction_times) / len(extraction_times) if extraction_times else 0.0,
            "field_extraction_total_seconds": sum(extraction_times),
        },
    }


def load_prediction_rows(input_dir: str | Path) -> list[dict[str, object]]:
    root = Path(input_dir)
    rows: list[dict[str, object]] = []
    for path in sorted(root.glob("*.json")):
        if path.name == "summary.json":
            continue
        with path.open("r", encoding="utf-8") as stream:
            rows.append(json.load(stream))
    return rows
