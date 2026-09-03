"""Evidence-first root-cause analysis for field regression failures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path

from .common_schema import DOCUMENT_FIELD_KEYS, document_type_from_form_type
from .field_evaluation import _payload, _prediction_list, evaluate_prediction_rows, load_prediction_rows
from .field_extraction import extract_fields
from .normalization import normalize_fields
from .oracle_validation import _agreement_threshold, _field_agreement, _semantic_value_valid
from .prediction_parser import OCRPrediction
from .label_bbox import parse_bounding_boxes
from .oracle_validation import build_oracle_document
from .sample_dataset import iter_target_documents


def _box(item: OCRPrediction) -> list[list[int]]:
    return [[min(item.x), min(item.y)], [max(item.x), min(item.y)], [max(item.x), max(item.y)], [min(item.x), max(item.y)]]


def _expected_text_matches(field_name: str, expected: Mapping[str, object], predictions: Sequence[OCRPrediction]) -> list[dict[str, object]]:
    expected_value = _payload(expected)
    expected_raw = str(expected.get("raw_text") or expected.get("value") or "")
    matches: list[dict[str, object]] = []
    from .layout_reconstruction import reconstruct_layout

    text_items = [(index, prediction.text, _box(prediction), prediction.score) for index, prediction in enumerate(predictions)]
    text_items.extend((None, line.text, [[line.bbox[0], line.bbox[1]], [line.bbox[2], line.bbox[1]], [line.bbox[2], line.bbox[3]], [line.bbox[0], line.bbox[3]]], line.confidence) for line in reconstruct_layout(predictions).lines)
    for index, text, bbox, confidence in text_items:
        score = _field_agreement(field_name, text, expected_value)
        if score >= _agreement_threshold(field_name):
            matches.append({"index": index, "text": text, "bbox": bbox, "confidence": confidence, "agreement": score})
            continue
        # For numeric normalized oracle values, compare the expected raw text
        # directly to preserve evidence such as '$19,000.01' and '30'.
        canonical_expected = " ".join(expected_raw.casefold().split())
        canonical_text = " ".join(text.casefold().split())
        if expected_raw and (
            expected_raw.casefold() in text.casefold()
            or canonical_expected in canonical_text
        ):
            matches.append({"index": index, "text": text, "bbox": bbox, "confidence": confidence, "agreement": 1.0})
    return matches


def _cause_detail(field_name: str, cause: str, actual: Mapping[str, object], matches: Sequence[Mapping[str, object]]) -> str:
    if cause == "OCR_MISSING":
        return "expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it"
    if cause == "EXTRACTION_MISSING":
        if str(actual.get("status")) == "ambiguous":
            return "expected OCR evidence exists, but competing anchored candidates did not clear the selection margin"
        return "expected OCR evidence exists, but label/value attachment did not produce a valid field candidate"
    if field_name in {"buyer", "seller", "shipper", "consignee"}:
        selected = str(actual.get("value") or "").casefold()
        if selected in {"phone", "notiyy", "notiy", "co., ltd.", "co., ltd"} or "phone" in selected:
            return "party-role extraction selected a neighbouring contact/control token; semantic party guard or cell boundary was insufficient"
        return "multiple party blocks were geometrically plausible and the selected block did not match the expected party evidence"
    if field_name == "amount":
        return "amount candidate was selected from a nearby monetary/table region, but numeric formatting or total-row evidence did not match the expected value"
    if field_name in {"invoice_no", "bl_no"}:
        return "reference-number candidate was selected from a competing reference region; the expected identifier was not sufficiently distinguished"
    if field_name == "date":
        return "date candidate came from a competing date context; invoice-date role was not sufficiently separated"
    if field_name == "quantity":
        return "quantity column grouping did not retain the complete expected row sequence"
    return "selected candidate disagreed with oracle evidence despite a matching OCR candidate"


def analyze_failures(
    rows: Sequence[Mapping[str, object]],
    *,
    failure_keys: set[tuple[str, str]] | None = None,
    baseline_items: Mapping[tuple[str, str], Mapping[str, object]] | None = None,
) -> dict[str, object]:
    evaluated = evaluate_prediction_rows(rows)
    row_by_id = {str(row["document_id"]): row for row in rows}
    failures: list[dict[str, object]] = []
    for item in evaluated["field_results"]:
        # seller is a newly added backward-compatible field and is reported in
        # the dedicated seller section of the regression, not mixed into the
        # 18-field baseline failure denominator.
        key = (str(item["document_id"]), str(item["field_name"]))
        if item["field_name"] == "seller":
            continue
        if failure_keys is not None and key not in failure_keys:
            continue
        baseline_item = (baseline_items or {}).get(key)
        if failure_keys is None and (not item["oracle_proxy"] or item["improved"]["outcome"] == "correct"):
            continue
        row = row_by_id[str(item["document_id"])]
        predictions = _prediction_list(row)
        actual_fields = normalize_fields(extract_fields(str(row["form_type"]), predictions))
        actual = actual_fields[str(item["field_name"])]
        reconstructed_expected = row.get("oracle_fields", {}).get(str(item["field_name"]), {})  # type: ignore[union-attr]
        expected = reconstructed_expected
        stored_expected = baseline_item.get("expected", {}) if baseline_item is not None else expected
        oracle_conflict = False
        oracle_conflict_detail = None
        if baseline_item is not None and _semantic_value_valid(str(item["field_name"]), _payload(reconstructed_expected)):
            stored_value = _payload(stored_expected)
            reconstructed_value = _payload(reconstructed_expected)
            oracle_conflict = (
                _field_agreement(str(item["field_name"]), stored_value, reconstructed_value)
                < _agreement_threshold(str(item["field_name"]))
            )
            if oracle_conflict:
                oracle_conflict_detail = "stored regression oracle and reconstructed GT oracle disagree; treat the stored failure as oracle disagreement/manual review"
        if baseline_item is not None and not _semantic_value_valid(str(item["field_name"]), _payload(expected)):
            # Static-label oracle cases remain part of the requested baseline
            # failure list, but their full evidence bbox is legitimately
            # unavailable. Keep the stored expected value and mark that gap.
            expected = baseline_item.get("expected", expected)  # type: ignore[assignment]
        expected_valid = _semantic_value_valid(str(item["field_name"]), _payload(expected))
        matches = _expected_text_matches(str(item["field_name"]), expected, predictions)
        selected_indices = list(actual.source_indices)
        selected_predictions = [predictions[index] for index in selected_indices if 0 <= index < len(predictions)]
        selected_bbox = (
            [
                [min(point[0] for point in actual.bbox), min(point[1] for point in actual.bbox)],
                [max(point[0] for point in actual.bbox), min(point[1] for point in actual.bbox)],
                [max(point[0] for point in actual.bbox), max(point[1] for point in actual.bbox)],
                [min(point[0] for point in actual.bbox), max(point[1] for point in actual.bbox)],
            ]
            if actual.bbox is not None else None
        )
        root_cause = (
            oracle_conflict_detail
            if oracle_conflict_detail is not None
            else _cause_detail(
                str(item["field_name"]),
                str(baseline_item["improved"]["cause"] if baseline_item is not None else item["improved"]["cause"]),
                {"status": actual.status, "value": actual.value}, matches,
            )
        )
        failures.append({
            "document_id": row["document_id"],
            "document_type": document_type_from_form_type(str(row["form_type"])),
            "form_type": row["form_type"],
            "split": item["split"],
            "field": item["field_name"],
            "oracle_proxy": True,
            "oracle_expected_value": _payload(expected),
            "stored_baseline_expected_value": _payload(stored_expected),
            "reconstructed_oracle_value": _payload(reconstructed_expected),
            "oracle_conflict": oracle_conflict,
            "oracle_conflict_detail": oracle_conflict_detail,
            "true_failure_under_reconstructed_oracle": (
                not oracle_conflict
                and _semantic_value_valid(str(item["field_name"]), _payload(reconstructed_expected))
                and (
                    actual.status != "found"
                    or _field_agreement(str(item["field_name"],), actual.normalized, _payload(reconstructed_expected))
                    < _agreement_threshold(str(item["field_name"]))
                )
            ),
            "oracle_expected_raw_text": expected.get("raw_text"),
            "oracle_expected_bbox": expected.get("bbox"),
            "expected_bbox_source": "oracle_fields[field].bbox; semantic GT field bbox unavailable",
            "expected_text_in_raw_ocr": bool(matches),
            "expected_text_matches": matches,
            "extractor_output": actual.value,
            "extractor_status": actual.status,
            "baseline_failure_outcome": baseline_item["improved"]["outcome"] if baseline_item is not None else item["improved"]["outcome"],
            "baseline_failure_cause": baseline_item["improved"]["cause"] if baseline_item is not None else item["improved"]["cause"],
            "current_outcome_under_selected_oracle": item["improved"]["outcome"],
            "extractor_normalized": actual.normalized,
            "extractor_reason": actual.reason,
            "selected_candidate": {
                "value": actual.value,
                "raw_text": actual.raw_text,
                "source_indices": selected_indices,
                "bbox": selected_bbox,
                "predictions": [
                    {"index": index, "text": predictions[index].text, "bbox": _box(predictions[index]), "confidence": predictions[index].score}
                    for index in selected_indices if 0 <= index < len(predictions)
                ],
            },
            "failure_classification": baseline_item["improved"]["cause"] if baseline_item is not None else item["improved"]["cause"],
            "root_cause": root_cause,
            "all_raw_prediction_count": len(predictions),
            "oracle_expected_value_valid": expected_valid,
        })
    failures.sort(key=lambda item: (str(item["split"]), str(item["document_type"]), str(item["document_id"]), str(item["field"])))
    counts = {}
    for failure in failures:
        key = str(failure["failure_classification"])
        counts[key] = counts.get(key, 0) + 1
    return {
        "analysis": "field_failure_root_cause",
        "oracle_note": evaluated["oracle_note"],
        "failure_count": len(failures),
        "failure_class_counts": counts,
        "failures": failures,
    }


def analyze_failure_directory(
    input_dir: str | Path,
    sample_zip: str | Path | None = None,
    baseline_report: str | Path | None = None,
    comparison_report: str | Path | None = None,
) -> dict[str, object]:
    rows = load_prediction_rows(input_dir)
    baseline_rows = rows
    if sample_zip is not None:
        samples = {sample.document_id: sample for sample in iter_target_documents(str(sample_zip), paired_only=True)}
        enriched_rows: list[dict[str, object]] = []
        for row in rows:
            sample = samples.get(str(row["document_id"]))
            if sample is None:
                enriched_rows.append(row)
                continue
            predictions = _prediction_list(row)
            ground_truth = parse_bounding_boxes(sample.label)
            oracle = build_oracle_document(str(row["form_type"]), str(row["document_id"]), predictions, ground_truth)
            enriched = dict(row)
            enriched["oracle_fields"] = oracle["fields"]
            enriched_rows.append(enriched)
        rows = enriched_rows
    baseline = None
    allowed: set[tuple[str, str]] | None = None
    baseline_items: dict[tuple[str, str], Mapping[str, object]] | None = None
    if baseline_report is not None and Path(baseline_report).is_file():
        with Path(baseline_report).open("r", encoding="utf-8") as stream:
            baseline = json.load(stream)
        baseline_items = {
            (str(item["document_id"]), str(item["field_name"])): item
            for item in baseline["field_results"]
        }
        allowed = {
            key for key, item in baseline_items.items()
            if item["oracle_proxy"] and item["improved"]["outcome"] != "correct" and key[1] != "seller"
        }
        if comparison_report is not None and Path(comparison_report).is_file():
            with Path(comparison_report).open("r", encoding="utf-8") as stream:
                comparison = json.load(stream)
            comparison_keys = {
                (str(item["document_id"]), str(item["field_name"]))
                for item in comparison["field_results"]
                if item["oracle_proxy"]
            }
            allowed &= comparison_keys
    report = analyze_failures(rows, failure_keys=allowed, baseline_items=baseline_items)
    if sample_zip is not None:
        # Keep the requested 18-field baseline denominator.  Reconstructed GT
        # evidence may make previously unavailable fields evaluable (for
        # example a table gross weight), but those are not silently added to
        # the baseline failure set.
        if baseline is None:
            baseline = evaluate_prediction_rows(baseline_rows)
            baseline_items = {
                (str(item["document_id"]), str(item["field_name"])): item
                for item in baseline["field_results"]
            }
            allowed = {
                key for key, item in baseline_items.items()
                if item["oracle_proxy"] and item["improved"]["outcome"] != "correct" and key[1] != "seller"
            }
        # The first pass above has already selected the baseline failure keys;
        # its details are retained even when reconstructed oracle semantics are
        # unavailable for a static caption.
        report["failures"] = [
            item for item in report["failures"]
            if (str(item["document_id"]), str(item["field"])) in allowed
        ]
        report["failure_count"] = len(report["failures"])
        report["failure_class_counts"] = {
            cause: sum(1 for item in report["failures"] if item["failure_classification"] == cause)
            for cause in sorted({str(item["failure_classification"]) for item in report["failures"]})
        }
    report["oracle_source"] = (
        "reconstructed from lightweight sample GT labels and raw OCR predictions"
        if sample_zip is not None else
        "stored row oracle_fields; raw_text/bbox may be unavailable"
    )
    return report
