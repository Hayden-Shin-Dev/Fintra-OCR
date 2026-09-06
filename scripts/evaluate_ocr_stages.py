"""Separate OCR-stage metrics from Fintra field-extractor outcomes.

This evaluator consumes frozen Modern and Paddle OCR JSON plus the reviewed
semantic field gold.  It never calls a field extractor and never rewrites GT,
OCR, or model artifacts.  Region matching uses polygon IoU and the same
maximum-cardinality one-to-one matcher as ``evaluate_baseline.py``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_baseline import _edit_distance, _iou, _match, _normalized_text, _polygon
from scripts.evaluate_field_extraction import normalize_field


DOCUMENT_TYPES = ("Commercial Invoice", "Packing List", "B/L")
PRIMARY_BASE_FIELDS = {
    "Commercial Invoice": {"seller", "buyer", "currency", "total_amount", "invoice_date", "quantity"},
    "Packing List": {"exporter", "consignee", "quantity", "package_count", "gross_weight", "net_weight"},
    "B/L": {"shipper", "consignee", "shipment_date", "on_board_date", "package_count", "gross_weight"},
}
RECOVERABLE = {
    "OCR_CORRECT_SINGLE_REGION",
    "OCR_CORRECT_MULTI_REGION",
    "OCR_MINOR_CHARACTER_ERROR",
}


def _box(poly: list[list[float]] | list[float]) -> tuple[float, float, float, float]:
    if poly and isinstance(poly[0], (int, float)):
        points = list(zip(poly[::2], poly[1::2]))
    else:
        points = poly  # type: ignore[assignment]
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _rect_poly(box: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    x1, y1, x2, y2 = box
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def _intersection_ratio(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    area = max(0.0, min(first[2], second[2]) - max(first[0], second[0])) * max(
        0.0, min(first[3], second[3]) - max(first[1], second[1])
    )
    first_area = max(1.0, (first[2] - first[0]) * (first[3] - first[1]))
    second_area = max(1.0, (second[2] - second[0]) * (second[3] - second[1]))
    return area / min(first_area, second_area)


def _read_gt(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        polygon = _polygon(zip(item["x"], item["y"]))
        result.append({"index": index, "polygon": polygon, "text": str(item.get("data") or "")})
    return result


def _read_detection(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    threshold = float(payload.get("score_threshold", 0.0))
    result = []
    for index, item in enumerate(payload.get("candidates", [])):
        score = float(item.get("score", 1.0))
        if score < threshold:
            continue
        polygon = _polygon(zip(item["boundary"][::2], item["boundary"][1::2]))
        result.append({"index": index, "polygon": polygon, "text": "", "score": score})
    return result


def _read_ocr(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for index, item in enumerate(payload.get("regions", [])):
        polygon_value = item.get("polygon", item.get("bbox"))
        if polygon_value and isinstance(polygon_value[0], (int, float)):
            polygon = _polygon(zip(polygon_value[::2], polygon_value[1::2]))
        else:
            polygon = _polygon(polygon_value)
        result.append(
            {
                "index": index,
                "polygon": polygon,
                "box": _box(polygon_value),
                "text": str(item.get("text") or ""),
                "confidence": item.get("confidence"),
            }
        )
    return result


def _metric(gt: list[dict[str, Any]], predictions: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    matches = _match(gt, predictions, threshold)
    exact = normalized = 0
    edit_sum = edit_denominator = 0
    for gt_index, pred_index, _ in matches:
        reference = gt[gt_index]["text"]
        hypothesis = predictions[pred_index].get("text", "")
        exact += reference == hypothesis
        normalized += _normalized_text(reference) == _normalized_text(hypothesis)
        edit_sum += _edit_distance(reference, hypothesis)
        edit_denominator += max(len(reference), 1)
    tp = len(matches)
    fp = len(predictions) - tp
    fn = len(gt) - tp
    precision = tp / len(predictions) if predictions else 0.0
    recall = tp / len(gt) if gt else 0.0
    return {
        "gt_regions": len(gt),
        "predicted_regions": len(predictions),
        "matched_regions": tp,
        "false_positive_regions": fp,
        "missed_regions": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "hmean": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "exact_text_matches": exact,
        "normalized_text_matches": normalized,
        "exact_text_match_rate_on_matched": exact / tp if tp else 0.0,
        "normalized_text_match_rate_on_matched": normalized / tp if tp else 0.0,
        "character_score_on_matched": 1.0 - edit_sum / edit_denominator if edit_denominator else 0.0,
        "cer_on_matched": edit_sum / edit_denominator if edit_denominator else 0.0,
        "matches": matches,
    }


def _e2e_metric(recognition: dict[str, Any]) -> dict[str, Any]:
    exact = int(recognition["exact_text_matches"])
    normalized = int(recognition["normalized_text_matches"])
    gt_count = int(recognition["gt_regions"])
    prediction_count = int(recognition["predicted_regions"])
    precision = exact / prediction_count if prediction_count else 0.0
    recall = exact / gt_count if gt_count else 0.0
    return {
        "gt_regions": gt_count,
        "predicted_regions": prediction_count,
        "matched_regions": exact,
        "false_positive_regions": prediction_count - exact,
        "missed_regions": gt_count - exact,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "hmean": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "exact_text_matches": exact,
        "normalized_text_matches": normalized,
        "exact_text_match_rate_on_matched": exact / int(recognition["matched_regions"]) if recognition["matched_regions"] else 0.0,
        "normalized_text_match_rate_on_matched": normalized / int(recognition["matched_regions"]) if recognition["matched_regions"] else 0.0,
        "character_score_on_matched": recognition["character_score_on_matched"],
        "cer_on_matched": recognition["cer_on_matched"],
        "matches": recognition["matches"],
    }


def _sum_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {key: sum(int(row[key]) for row in rows) for key in ("gt_regions", "predicted_regions", "matched_regions", "false_positive_regions", "missed_regions", "exact_text_matches", "normalized_text_matches")}
    totals["precision"] = totals["matched_regions"] / totals["predicted_regions"] if totals["predicted_regions"] else 0.0
    totals["recall"] = totals["matched_regions"] / totals["gt_regions"] if totals["gt_regions"] else 0.0
    totals["f1"] = totals["hmean"] = 2 * totals["precision"] * totals["recall"] / (totals["precision"] + totals["recall"]) if totals["precision"] + totals["recall"] else 0.0
    totals["exact_text_match_rate_on_matched"] = totals["exact_text_matches"] / totals["matched_regions"] if totals["matched_regions"] else 0.0
    totals["normalized_text_match_rate_on_matched"] = totals["normalized_text_matches"] / totals["matched_regions"] if totals["matched_regions"] else 0.0
    totals["cer_on_matched"] = sum(float(row["cer_on_matched"]) * int(row["matched_regions"]) for row in rows) / totals["matched_regions"] if totals["matched_regions"] else 0.0
    totals["character_score_on_matched"] = 1.0 - totals["cer_on_matched"]
    return totals


def _field_base(name: str) -> str:
    return re.sub(r"^items\[\d+\]\.", "", name)


def _join_reading_order(regions: list[dict[str, Any]]) -> str:
    if not regions:
        return ""
    lines: list[list[dict[str, Any]]] = []
    for region in sorted(regions, key=lambda item: (item["box"][1], item["box"][0])):
        height = max(1.0, region["box"][3] - region["box"][1])
        cy = (region["box"][1] + region["box"][3]) / 2
        line = next((line for line in lines if abs(cy - line[0]) <= max(height, line[1]) * 0.65), None)
        if line is None:
            lines.append([cy, height, region])
        else:
            line.append(region)
    ordered = []
    for line in sorted(lines, key=lambda item: item[0]):
        members = line[2:] if len(line) > 2 else [line[2]]
        ordered.extend(sorted(members, key=lambda item: item["box"][0]))
    return " ".join(item["text"] for item in ordered).strip()


def _fuzzy_similarity(expected: str, observed: str) -> tuple[float, float]:
    expected_norm = _normalized_text(expected).casefold()
    observed_norm = _normalized_text(observed).casefold()
    similarity = SequenceMatcher(None, expected_norm, observed_norm).ratio()
    cer = _edit_distance(expected_norm, observed_norm) / max(len(expected_norm), 1)
    return similarity, cer


def _candidate_regions(field: dict[str, Any], gt_tokens: list[dict[str, Any]], regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not gt_tokens:
        return []
    token_boxes = [_box(token["polygon"]) for token in gt_tokens]
    field_box = (min(box[0] for box in token_boxes), min(box[1] for box in token_boxes), max(box[2] for box in token_boxes), max(box[3] for box in token_boxes))
    field_height = max(1.0, field_box[3] - field_box[1])
    selected = []
    for region in regions:
        box = region["box"]
        overlap = max(_intersection_ratio(token_box, box) for token_box in token_boxes)
        near = (
            box[3] >= field_box[1] - field_height * 0.35
            and box[1] <= field_box[3] + field_height * 0.35
            and box[2] >= field_box[0] - field_height * 1.5
            and box[0] <= field_box[2] + field_height * 1.5
        )
        if overlap >= 0.35 or (near and _iou(_rect_poly(field_box), _rect_poly(box)) >= 0.02):
            selected.append(region)
    return selected


def _field_evidence(case: dict[str, Any], backend: str, regions: list[dict[str, Any]], gold_root: Path | None = None) -> list[dict[str, Any]]:
    gold_path = (gold_root / case["case_id"] / "semantic_gold_fields.json") if gold_root else case["path"] / "semantic_gold_fields.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    raw_gt_path = case.get("gt_path", case["path"] / "gt.json")
    raw_gt = json.loads(Path(raw_gt_path).read_text(encoding="utf-8"))
    rows = []
    for field in gold:
        if field.get("status") != "available":
            continue
        tokens = []
        for index in field.get("source_token_indices", []):
            item = raw_gt["bbox"][index]
            tokens.append({"polygon": list(zip(item["x"], item["y"]))})
        expected = str(field.get("value") or "")
        expected_normalized = normalize_field(expected, field["field_name"])
        candidates = _candidate_regions(field, tokens, regions)
        single_exact = any(item["text"] == expected for item in candidates)
        single_normalized = any(
            expected_normalized is not None
            and normalize_field(item["text"], field["field_name"]) is not None
            and normalize_field(item["text"], field["field_name"]) == expected_normalized
            for item in candidates
        )
        combined = _join_reading_order(candidates)
        multi_exact = combined == expected
        combined_normalized = normalize_field(combined, field["field_name"])
        multi_normalized = expected_normalized is not None and combined_normalized is not None and combined_normalized == expected_normalized
        closest = max(candidates, key=lambda item: _fuzzy_similarity(expected, item["text"])[0], default=None)
        combined_similarity, combined_cer = _fuzzy_similarity(expected, combined)
        closest_similarity, closest_cer = _fuzzy_similarity(expected, closest["text"]) if closest else (0.0, 1.0)
        fuzzy = max(combined_similarity, closest_similarity) >= 0.90 and min(combined_cer, closest_cer) <= 0.10
        if single_exact or single_normalized:
            classification = "OCR_CORRECT_SINGLE_REGION"
        elif multi_exact or multi_normalized:
            classification = "OCR_CORRECT_MULTI_REGION"
        elif fuzzy:
            classification = "OCR_MINOR_CHARACTER_ERROR"
        elif not candidates:
            classification = "OCR_DETECTION_MISSING"
        else:
            classification = "OCR_MAJOR_CHARACTER_ERROR"
        rows.append({
            "case_id": case["case_id"], "document_id": case["document_id"], "document_type": case["document_type"],
            "backend": backend, "field_name": field["field_name"], "field_base": _field_base(field["field_name"]),
            "gt_value": expected, "candidate_count": len(candidates),
            "single_exact": single_exact, "multi_region_exact": multi_exact,
            "normalized_exact": single_normalized, "multi_region_normalized": multi_normalized,
            "fuzzy_similarity": max(combined_similarity, closest_similarity), "fuzzy_cer": min(combined_cer, closest_cer),
            "classification": classification, "closest_ocr_text": closest["text"] if closest else "",
            "combined_ocr_text": combined, "neighboring_ocr_texts": " || ".join(item["text"] for item in candidates),
            "confidence": closest.get("confidence") if closest else None,
        })
    return rows


def _field_aggregate(rows: list[dict[str, Any]], key_names: tuple[str, ...] = ("document_type",)) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = " / ".join(str(row[name]) for name in key_names) if key_names else "overall"
        groups[key].append(row)
    result = {}
    for key, group in sorted(groups.items()):
        counter = Counter(item["classification"] for item in group)
        result[key] = {
            "applicable_fields": len(group),
            **{name: sum(bool(item.get(name)) for item in group) for name in ("single_exact", "multi_region_exact", "normalized_exact", "multi_region_normalized")},
            "fuzzy_recoverable": counter["OCR_MINOR_CHARACTER_ERROR"],
            "major_ocr_error": counter["OCR_MAJOR_CHARACTER_ERROR"],
            "detection_missing": counter["OCR_DETECTION_MISSING"],
            "recoverable": sum(item["classification"] in RECOVERABLE for item in group),
            "recoverability": sum(item["classification"] in RECOVERABLE for item in group) / len(group) if group else 0.0,
        }
    return result


def _load_extractor_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}


def _extractor_correct(row: dict[str, str] | None) -> bool:
    return bool(row and row.get("status") in {"exact_match", "normalized_match"})


def _candidate_hit(extractor_row: dict[str, str] | None, evidence_row: dict[str, Any]) -> bool:
    """Check whether the extractor selected text present in raw OCR evidence."""
    if not extractor_row or extractor_row.get("status") not in {"extracted", "exact_match", "normalized_match"}:
        return False
    source = _normalized_text(extractor_row.get("source_text", "")).strip().casefold()
    if not source:
        return False
    candidates = [
        _normalized_text(value).strip().casefold()
        for value in evidence_row.get("neighboring_ocr_texts", "").split(" || ")
        if value.strip()
    ]
    joined = _normalized_text(evidence_row.get("combined_ocr_text", "")).strip().casefold()
    return any(source == value or source in value or value in source for value in candidates) or source in joined


def _decomposition(rows: list[dict[str, Any]], extractor: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        prediction = extractor.get((row["case_id"], row["field_name"]))
        raw_recoverable = row["classification"] in RECOVERABLE
        candidate_hit = raw_recoverable and _candidate_hit(prediction, row)
        final_correct = _extractor_correct(prediction)
        result.append({
            **row,
            "raw_ocr_recoverable": raw_recoverable,
            "candidate_hit": candidate_hit,
            "resolver_correct": candidate_hit and final_correct,
            "final_correct": final_correct,
        })
    return result


def _decomposition_aggregate(rows: list[dict[str, Any]], key_names: tuple[str, ...] = ()) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = " / ".join(str(row[name]) for name in key_names) if key_names else "overall"
        groups[key].append(row)
    result = {}
    for key, group in sorted(groups.items()):
        applicable = len(group)
        recoverable = sum(row["raw_ocr_recoverable"] for row in group)
        candidate_hit = sum(row["candidate_hit"] for row in group)
        resolver_correct = sum(row["resolver_correct"] for row in group)
        final_correct = sum(row["final_correct"] for row in group)
        result[key] = {
            "applicable": applicable,
            "recoverable": recoverable,
            "candidate_hit": candidate_hit,
            "resolver_correct": resolver_correct,
            "final_correct": final_correct,
            "ocr_recoverability": recoverable / applicable if applicable else 0.0,
            "candidate_recall_on_recoverable": candidate_hit / recoverable if recoverable else 0.0,
            "resolver_accuracy_on_candidate_hit": resolver_correct / candidate_hit if candidate_hit else 0.0,
            "final_accuracy": final_correct / applicable if applicable else 0.0,
        }
    return result


def _extractor_accuracy(rows: dict[tuple[str, str], dict[str, str]]) -> dict[str, Any]:
    statuses = Counter(row.get("status", "") for row in rows.values())
    applicable = sum(row.get("gt_status") == "available" for row in rows.values())
    correct = statuses["exact_match"] + statuses["normalized_match"]
    return {"applicable": applicable, "correct": correct, "accuracy": correct / applicable if applicable else 0.0}


def evaluate(cases_root: Path, modern_field_csv: Path, paddle_field_csv: Path, output: Path, gold_root: Path | None = None) -> dict[str, Any]:
    cases = []
    for path in sorted(cases_root.iterdir()):
        manifest_path = path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases.append({"path": path, "case_id": manifest["case_id"], "document_id": manifest["document_id"], "document_type": manifest["document_type"]})
    modern_extractor = _load_extractor_rows(modern_field_csv)
    paddle_extractor = _load_extractor_rows(paddle_field_csv)
    stage_rows = []
    field_rows = []
    for case in cases:
        gt = _read_gt(case["path"] / "gt.json")
        detection = _read_detection(case["path"] / "outputs" / "detection.json")
        modern_path = next((case["path"] / "outputs" / "recognition").glob("*.json"))
        paddle_path = cases_root.parent.parent / "paddle_gpu_field_eval" / "cases" / case["case_id"] / "outputs" / "recognition" / "paddle.json"
        if not paddle_path.is_file():
            raise FileNotFoundError(f"Paddle OCR output missing: {paddle_path}")
        modern = _read_ocr(modern_path)
        paddle = _read_ocr(paddle_path)
        for backend, predictions in (("modern", modern), ("paddle", paddle)):
            detection_predictions = detection if backend == "modern" else [{"polygon": item["polygon"], "text": ""} for item in paddle]
            det = _metric(gt, detection_predictions, 0.5)
            rec = _metric(gt, predictions, 0.5)
            e2e = _e2e_metric(rec)
            stage_rows.append({"case_id": case["case_id"], "document_type": case["document_type"], "backend": backend, "detection": det, "recognition": rec, "e2e": e2e, "regions": predictions})
            field_rows.extend(_field_evidence(case, backend, predictions, gold_root))

    def by_type(rows: list[dict[str, Any]], section: str) -> dict[str, Any]:
        return {kind: _sum_metrics([row[section] for row in rows if row["document_type"] == kind]) for kind in DOCUMENT_TYPES}

    gold_status_counts = Counter()
    gold_status_by_type = {kind: Counter() for kind in DOCUMENT_TYPES}
    for case in cases:
        gold_path = (gold_root / case["case_id"] / "semantic_gold_fields.json") if gold_root else case["path"] / "semantic_gold_fields.json"
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        for field in gold:
            gold_status_counts[field.get("status", "unknown")] += 1
            gold_status_by_type[case["document_type"]][field.get("status", "unknown")] += 1

    stage = {}
    for backend in ("modern", "paddle"):
        rows = [row for row in stage_rows if row["backend"] == backend]
        stage[backend] = {"overall": {section: _sum_metrics([row[section] for row in rows]) for section in ("detection", "recognition", "e2e")}, "by_document_type": {section: by_type(rows, section) for section in ("detection", "recognition", "e2e")}}
    stage["references"] = {"modern_official_detection_hmean": 0.8972637218253485, "modern_official_recognition_score": 0.9181048007530593, "modern_official_e2e_hmean": 0.8037257364923692, "note": "Official AI-Hub reference uses its own PCC/LCS evaluator; local stage rows use polygon IoU 0.5 for both backends."}

    evidence = {backend: [row for row in field_rows if row["backend"] == backend] for backend in ("modern", "paddle")}
    evidence_report = {backend: {"overall": _field_aggregate(rows, ()), "by_document_type": _field_aggregate(rows, ("document_type",)), "by_field": _field_aggregate(rows, ("document_type", "field_base"))} for backend, rows in evidence.items()}
    primary_rows = {backend: [row for row in rows if row["field_base"] in PRIMARY_BASE_FIELDS.get(row["document_type"], set())] for backend, rows in evidence.items()}
    secondary_rows = {backend: [row for row in rows if row not in primary_rows[backend]] for backend, rows in evidence.items()}
    evidence_report["primary"] = {backend: {"overall": _field_aggregate(rows, ()), "by_document_type": _field_aggregate(rows, ("document_type",)), "by_field": _field_aggregate(rows, ("document_type", "field_base"))} for backend, rows in primary_rows.items()}
    evidence_report["secondary"] = {backend: {"overall": _field_aggregate(rows, ())} for backend, rows in secondary_rows.items()}
    decomposition = {
        "modern": _decomposition(evidence["modern"], modern_extractor),
        "paddle": _decomposition(evidence["paddle"], paddle_extractor),
    }

    pipeline = {}
    for backend, rows in primary_rows.items():
        extractor = modern_extractor if backend == "modern" else paddle_extractor
        loss = {}
        for scope, group in [("overall", rows), *[(kind, [row for row in rows if row["document_type"] == kind]) for kind in DOCUMENT_TYPES]]:
            applicable = len(group)
            detected = sum(item["classification"] != "OCR_DETECTION_MISSING" for item in group)
            recoverable = sum(item["classification"] in RECOVERABLE for item in group)
            extracted = sum(extractor.get((item["case_id"], item["field_name"]), {}).get("status") in ("exact_match", "normalized_match") for item in group)
            loss[scope] = {"applicable_primary_fields": applicable, "detection_evidence_present": detected, "recognition_recoverable": recoverable, "extractor_correct": extracted, "detection_survival_rate": detected / applicable if applicable else 0.0, "recognition_survival_given_detection": recoverable / detected if detected else 0.0, "extractor_accuracy_given_recoverable_ocr": extracted / recoverable if recoverable else 0.0}
        pipeline[backend] = loss

    modern_by_key = {(row["case_id"], row["field_name"]): row for row in evidence["modern"]}
    paddle_by_key = {(row["case_id"], row["field_name"]): row for row in evidence["paddle"]}
    hybrid_counts = Counter()
    hybrid_primary = Counter()
    for key, modern in modern_by_key.items():
        paddle = paddle_by_key[key]
        m = modern["classification"] in RECOVERABLE
        p = paddle["classification"] in RECOVERABLE
        hybrid_counts["both" if m and p else "modern_only" if m else "paddle_only" if p else "neither"] += 1
        if modern["field_base"] in PRIMARY_BASE_FIELDS.get(modern["document_type"], set()):
            hybrid_primary["both" if m and p else "modern_only" if m else "paddle_only" if p else "neither"] += 1
    total = sum(hybrid_counts.values())
    primary_total = sum(hybrid_primary.values())
    hybrid = {"overall": {**hybrid_counts, "total": total, "hybrid_recoverable": total - hybrid_counts["neither"], "hybrid_recoverability": (total - hybrid_counts["neither"]) / total if total else 0.0}, "primary": {**hybrid_primary, "total": primary_total, "hybrid_recoverable": primary_total - hybrid_primary["neither"], "hybrid_recoverability": (primary_total - hybrid_primary["neither"]) / primary_total if primary_total else 0.0}}

    output.mkdir(parents=True, exist_ok=True)
    with (output / "raw_field_evidence.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["case_id", "document_id", "document_type", "backend", "field_name", "field_base", "gt_value", "candidate_count", "single_exact", "multi_region_exact", "normalized_exact", "multi_region_normalized", "fuzzy_similarity", "fuzzy_cer", "classification", "closest_ocr_text", "combined_ocr_text", "neighboring_ocr_texts", "confidence"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(field_rows)
    with (output / "extraction_stage_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["case_id", "document_id", "document_type", "backend", "field_name", "field_base", "classification", "raw_ocr_recoverable", "candidate_hit", "resolver_correct", "final_correct"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in decomposition["modern"] + decomposition["paddle"]:
            writer.writerow({field: row.get(field) for field in fields})
    with (output / "stage_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["case_id", "document_type", "backend", "stage", "gt_regions", "predicted_regions", "matched_regions", "false_positive_regions", "missed_regions", "precision", "recall", "f1", "hmean", "exact_text_matches", "normalized_text_matches", "exact_text_match_rate_on_matched", "normalized_text_match_rate_on_matched", "character_score_on_matched", "cer_on_matched"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in stage_rows:
            for section in ("detection", "recognition", "e2e"):
                values = {key: value for key, value in row[section].items() if key != "matches"}; writer.writerow({"case_id": row["case_id"], "document_type": row["document_type"], "backend": row["backend"], "stage": section, **values})
    decomposition_report = {}
    for backend, rows in decomposition.items():
        primary = [row for row in rows if row["field_base"] in PRIMARY_BASE_FIELDS.get(row["document_type"], set())]
        secondary = [row for row in rows if row not in primary]
        decomposition_report[backend] = {
            "overall": _decomposition_aggregate(rows),
            "by_document_type": _decomposition_aggregate(rows, ("document_type",)),
            "by_field": _decomposition_aggregate(rows, ("document_type", "field_base")),
            "primary": {"overall": _decomposition_aggregate(primary), "by_document_type": _decomposition_aggregate(primary, ("document_type",)), "by_field": _decomposition_aggregate(primary, ("document_type", "field_base"))},
            "secondary": {"overall": _decomposition_aggregate(secondary)},
        }
    same_extractor = {"modern": _extractor_accuracy(modern_extractor), "paddle": _extractor_accuracy(paddle_extractor)}
    metrics = {"contract": "Frozen 60-case GT; stage metrics use IoU 0.5 maximum-cardinality matching; field evidence uses raw OCR only.", "documents": len(cases), "gold_status_counts": dict(gold_status_counts), "gold_status_by_document_type": {kind: dict(value) for kind, value in gold_status_by_type.items()}, "stage": stage, "true_field_evidence": evidence_report, "extraction_stage_decomposition": decomposition_report, "pipeline_loss_primary": pipeline, "hybrid_true_ocr_oracle": hybrid, "same_extractor_reference": same_extractor}
    (output / "ocr_stage_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = sorted((row for row in field_rows if row["classification"] not in ("OCR_CORRECT_SINGLE_REGION", "OCR_CORRECT_MULTI_REGION")), key=lambda row: (row["backend"], row["document_type"], row["case_id"], row["field_name"]))[:30]
    lines = ["# OCR stage evaluation", "", f"Documents evaluated: {len(cases)}", "", "## Contract", "", "Modern and Paddle are compared on the same raw AI-Hub GT boxes. Detection and recognition use polygon IoU 0.5 maximum-cardinality matching. Paddle canonical regions are used as its detector boxes because the saved Paddle adapter output does not expose a separate detector score. Field evidence does not read extractor predictions.", "", "## Stage summary", ""]
    for backend in ("modern", "paddle"):
        lines.append(f"### {backend}")
        overall = stage[backend]["overall"]
        for section in ("detection", "recognition", "e2e"):
            item = overall[section]
            if section == "e2e":
                lines.append(f"- {section}: P={item['precision']:.6f}, R={item['recall']:.6f}, Hmean={item['hmean']:.6f}, exact_pair_count={item['exact_text_matches']}, CER={item['cer_on_matched']:.6f}")
            else:
                lines.append(f"- {section}: P={item['precision']:.6f}, R={item['recall']:.6f}, Hmean={item['hmean']:.6f}, exact_on_matched={item['exact_text_match_rate_on_matched']:.6f}, CER={item['cer_on_matched']:.6f}")
    lines += ["", "## True raw OCR field evidence", "", "Recoverable means one of single exact, multi-region exact, multi-region normalized, or fuzzy recoverable (SequenceMatcher >= 0.90 and CER <= 0.10). These are evidence-availability metrics, not extractor accuracy.", ""]
    for backend in ("modern", "paddle"):
        for scope in ("primary", "secondary"):
            item = evidence_report[scope][backend]["overall"]["overall"]
            lines.append(f"- {backend} {scope}: {item['recoverable']}/{item['applicable_fields']} = {item['recoverability']:.6f}")
        lines.append(f"- {backend} primary by type: " + ", ".join(f"{kind}={evidence_report['primary'][backend]['by_document_type'][kind]['recoverable']}/{evidence_report['primary'][backend]['by_document_type'][kind]['applicable_fields']}" for kind in DOCUMENT_TYPES))
        lines.append(f"- {backend} primary failure counts: " + json.dumps({key: evidence_report['primary'][backend]['overall']['overall'][key] for key in ('fuzzy_recoverable', 'major_ocr_error', 'detection_missing')}, ensure_ascii=False))
    lines += ["", "## Extraction stage decomposition", "", "candidate_hit means the extractor source_text is present in the raw OCR regions selected by the frozen GT-token neighborhood (text evidence only). resolver_correct means candidate_hit plus exact/normalized final status; this does not generate or modify gold.", ""]
    for backend in ("modern", "paddle"):
        for scope in ("overall", "primary", "secondary"):
            item = decomposition_report[backend]["overall"]["overall"] if scope == "overall" else decomposition_report[backend][scope]["overall"]["overall"]
            lines.append(f"- {backend} {scope}: applicable={item['applicable']}, recoverable={item['recoverable']}, candidate_hit={item['candidate_hit']}, resolver_correct={item['resolver_correct']}, final_correct={item['final_correct']}; OCR={item['ocr_recoverability']:.6f}, candidate_recall={item['candidate_recall_on_recoverable']:.6f}, resolver={item['resolver_accuracy_on_candidate_hit']:.6f}, final={item['final_accuracy']:.6f}")
    lines += ["", "Gold exclusions (not in applicable evidence denominator):", json.dumps(metrics["gold_status_counts"], ensure_ascii=False), "", "Primary field detail is in ocr_stage_metrics.json under true_field_evidence.*.by_field."]
    lines += ["", "## Pipeline loss (primary fields)", ""]
    for backend, scopes in pipeline.items():
        item = scopes["overall"]
        lines.append(f"- {backend}: applicable={item['applicable_primary_fields']}, detection={item['detection_evidence_present']}, recognition={item['recognition_recoverable']}, extractor={item['extractor_correct']}; survival={item['detection_survival_rate']:.6f}/{item['recognition_survival_given_detection']:.6f}/{item['extractor_accuracy_given_recoverable_ocr']:.6f}")
    lines += ["", "## Hybrid raw OCR oracle", "", json.dumps(hybrid, ensure_ascii=False, indent=2), "", "## Same-extractor outcome (kept separate)", "", f"Modern {same_extractor['modern']['accuracy']:.6f}, Paddle {same_extractor['paddle']['accuracy']:.6f}. This is field-extractor outcome, not OCR character accuracy.", "", "## First 30 non-exact evidence cases", ""]
    for row in failures:
        lines.append(f"- {row['backend']} {row['case_id']} {row['document_type']} {row['field_name']}: GT={row['gt_value']!r}; closest={row['closest_ocr_text']!r}; neighbors={row['neighboring_ocr_texts']!r}; similarity={row['fuzzy_similarity']:.4f}; classification={row['classification']}")
    (output / "OCR_STAGE_EVALUATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"documents": len(cases), "output": str(output), "modern_primary_recoverability": evidence_report["primary"]["modern"]["overall"]["overall"]["recoverability"], "paddle_primary_recoverability": evidence_report["primary"]["paddle"]["overall"]["overall"]["recoverability"], "hybrid_primary_recoverability": hybrid["primary"]["hybrid_recoverability"]}, ensure_ascii=False))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "artifacts/fintra/field_eval/cases")
    parser.add_argument("--modern-field-csv", type=Path, default=ROOT / "artifacts/fintra/field_eval/field_results.csv")
    parser.add_argument("--paddle-field-csv", type=Path, default=ROOT / "artifacts/fintra/paddle_gpu_field_eval/field_results.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/fintra/ocr_stage_eval")
    parser.add_argument("--gold-root", type=Path, default=None, help="Root containing <case_id>/semantic_gold_fields.json")
    args = parser.parse_args()
    evaluate(args.cases, args.modern_field_csv, args.paddle_field_csv, args.output, args.gold_root)


if __name__ == "__main__":
    main()
