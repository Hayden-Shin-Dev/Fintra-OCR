"""Evaluate AI-Hub Validation GT JSON against official OCR TXT output.

This evaluator never changes the raw OCR TXT. It reports polygon IoU metrics at
0.5 and 0.8, deterministic one-to-one matching, exact text metrics, a
whitespace/Unicode-normalized comparison, and error records for the 0.5 view.
The bundled AI-Hub evaluator is also documented separately because it uses
area-precision/PCC matching rather than IoU.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import statistics
import unicodedata
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "fintra-ocr-v2.evaluation.v2"


def _polygon(values: Iterable[Iterable[float]]) -> list[tuple[float, float]]:
    result = [(float(point[0]), float(point[1])) for point in values]
    if len(result) < 3 or any(not all(math.isfinite(v) for v in point) for point in result):
        raise ValueError("polygon must contain at least three finite points")
    # AI-Hub bbox x/y arrays are not guaranteed to be serialized in perimeter
    # order. Canonicalize only the in-memory evaluation polygon; source GT and
    # official OCR TXT remain untouched.
    center_x = sum(point[0] for point in result) / len(result)
    center_y = sum(point[1] for point in result) / len(result)
    result.sort(key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x))
    return result


def _signed_area(poly: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        poly[i][0] * poly[(i + 1) % len(poly)][1]
        - poly[(i + 1) % len(poly)][0] * poly[i][1]
        for i in range(len(poly))
    )


def _cross(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _inside(
    a: tuple[float, float],
    b: tuple[float, float],
    point: tuple[float, float],
    orientation: float,
) -> bool:
    return orientation * _cross(a, b, point) >= -1e-7


def _intersection(
    first: tuple[float, float],
    second: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> tuple[float, float]:
    dx, dy = second[0] - first[0], second[1] - first[1]
    ex, ey = b[0] - a[0], b[1] - a[1]
    denominator = dx * ey - dy * ex
    if abs(denominator) < 1e-12:
        return second
    t = ((a[0] - first[0]) * ey - (a[1] - first[1]) * ex) / denominator
    return first[0] + t * dx, first[1] + t * dy


def _clip(subject: list[tuple[float, float]], clip: list[tuple[float, float]]) -> list[tuple[float, float]]:
    output = subject
    orientation = 1.0 if _signed_area(clip) >= 0 else -1.0
    for index, edge_start in enumerate(clip):
        edge_end = clip[(index + 1) % len(clip)]
        if not output:
            return []
        input_points = output
        output = []
        previous = input_points[-1]
        previous_inside = _inside(edge_start, edge_end, previous, orientation)
        for current in input_points:
            current_inside = _inside(edge_start, edge_end, current, orientation)
            if current_inside:
                if not previous_inside:
                    output.append(_intersection(previous, current, edge_start, edge_end))
                output.append(current)
            elif previous_inside:
                output.append(_intersection(previous, current, edge_start, edge_end))
            previous, previous_inside = current, current_inside
    return output


def _area(poly: list[tuple[float, float]]) -> float:
    return abs(_signed_area(poly))


def _iou(first: list[tuple[float, float]], second: list[tuple[float, float]]) -> float:
    first_area = _area(first)
    second_area = _area(second)
    union = first_area + second_area
    if union <= 0:
        return 0.0
    intersection = _area(_clip(first, second))
    return intersection / (union - intersection) if union > intersection else 0.0


def _edit_distance(reference: str, hypothesis: str) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, reference_char in enumerate(reference, 1):
        current = [row]
        for column, hypothesis_char in enumerate(hypothesis, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (reference_char != hypothesis_char),
                )
            )
        previous = current
    return previous[-1]


def _normalized_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split())


def _match(
    gt: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    threshold: float,
) -> list[tuple[int, int, float]]:
    scores = [[_iou(item["polygon"], pred["polygon"]) for pred in predictions] for item in gt]
    adjacency = [
        sorted(
            (index for index, score in enumerate(row) if score >= threshold),
            key=lambda index: (-row[index], index),
        )
        for row in scores
    ]
    prediction_to_gt = [-1] * len(predictions)

    def visit(gt_index: int, seen: set[int]) -> bool:
        for prediction_index in adjacency[gt_index]:
            if prediction_index in seen:
                continue
            seen.add(prediction_index)
            previous_gt = prediction_to_gt[prediction_index]
            if previous_gt == -1 or visit(previous_gt, seen):
                prediction_to_gt[prediction_index] = gt_index
                return True
        return False

    for gt_index in range(len(gt)):
        visit(gt_index, set())
    return sorted(
        (gt_index, pred_index, scores[gt_index][pred_index])
        for pred_index, gt_index in enumerate(prediction_to_gt)
        if gt_index != -1
    )


def _read_gt(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    image = payload["Images"]
    gt = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item["x"], item["y"]
        if len(xs) != len(ys) or len(xs) < 3:
            raise ValueError(f"{path}: bbox {index} has invalid x/y length")
        gt.append(
            {
                "index": index,
                "polygon": _polygon(zip(xs, ys)),
                "text": "" if item.get("data") is None else str(item["data"]),
            }
        )
    return {
        "image_stem": str(image["identifier"]),
        "document_type": str(image.get("form_type", "Unknown")),
        "gt": gt,
        "source_file": str(path),
    }


def _read_predictions(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = {}
    for document in payload.get("documents", []):
        documents[Path(str(document["image_stem"])).stem] = document.get("predictions", [])
    return documents


def _raw_detection_count(path: Path | None) -> int | None:
    if path is None:
        return None
    result = pickle.loads(path.read_bytes())
    return sum(len(item.get("boundary_result", [])) for item in result)


def _metric_row(
    gt: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    threshold: float,
) -> tuple[dict[str, Any], list[tuple[int, int, float]]]:
    matches = _match(gt, predictions, threshold)
    matched_gt = {item[0] for item in matches}
    matched_pred = {item[1] for item in matches}
    all_ious = [_iou(item["polygon"], pred["polygon"]) for item in gt for pred in predictions]
    matched_ious = [item[2] for item in matches]
    exact = 0
    normalized_exact = 0
    edit_sum = 0
    edit_denominator = 0
    for gt_index, pred_index, _ in matches:
        reference, hypothesis = gt[gt_index]["text"], predictions[pred_index].get("text", "")
        exact += reference == hypothesis
        normalized_exact += _normalized_text(reference) == _normalized_text(hypothesis)
        edit_sum += _edit_distance(reference, hypothesis)
        edit_denominator += max(len(reference), 1)
    return {
        "gt_regions": len(gt),
        "prediction_regions": len(predictions),
        "matched": len(matches),
        "missed_gt": len(gt) - len(matches),
        "false_positive_predictions": len(predictions) - len(matches),
        "detection_precision": len(matches) / len(predictions) if predictions else 0.0,
        "detection_recall": len(matches) / len(gt) if gt else 0.0,
        "detection_f1": 2 * len(matches) / (len(gt) + len(predictions))
        if gt or predictions
        else 0.0,
        "matched_iou_mean": sum(matched_ious) / len(matched_ious) if matched_ious else 0.0,
        "matched_iou_min": min(matched_ious) if matched_ious else 0.0,
        "matched_iou_max": max(matched_ious) if matched_ious else 0.0,
        "all_pair_iou_ge_0_5": sum(score >= 0.5 for score in all_ious),
        "all_pair_iou_ge_0_8": sum(score >= 0.8 for score in all_ious),
        "recognition_exact_matches": exact,
        "recognition_text_mismatches": len(matches) - exact,
        "recognition_exact_accuracy_on_matched": exact / len(matches) if matches else 0.0,
        "normalized_exact_matches": normalized_exact,
        "normalized_exact_accuracy_on_matched": normalized_exact / len(matches) if matches else 0.0,
        "edit_distance_sum": edit_sum,
        "edit_denominator": edit_denominator,
        "cer_on_matched": edit_sum / edit_denominator if edit_denominator else 0.0,
        "end_to_end_exact_recall": exact / len(gt) if gt else 0.0,
        "end_to_end_normalized_exact_recall": normalized_exact / len(gt) if gt else 0.0,
    }, matches


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(
    gt_path: Path,
    prediction_path: Path,
    output_dir: Path,
    detection_pkl: Path | None,
    raw_detection_count: int | None,
    document_type: str,
) -> dict[str, Any]:
    gt_record = _read_gt(gt_path)
    prediction_map = _read_predictions(prediction_path)
    predictions = prediction_map.get(gt_record["image_stem"], [])
    for prediction in predictions:
        prediction["polygon"] = _polygon(prediction["polygon"])

    rows = {}
    matches_by_threshold = {}
    for threshold in (0.5, 0.8):
        row, matches = _metric_row(gt_record["gt"], predictions, threshold)
        rows[str(threshold)] = row
        matches_by_threshold[threshold] = matches

    primary_matches = matches_by_threshold[0.5]
    matched_gt = {gt_index for gt_index, _, _ in primary_matches}
    matched_pred = {pred_index for _, pred_index, _ in primary_matches}
    pair_scores = [
        _iou(gt_item["polygon"], pred_item["polygon"])
        for gt_item in gt_record["gt"]
        for pred_item in predictions
    ]
    errors = []
    for gt_index, gt_item in enumerate(gt_record["gt"]):
        if gt_index in matched_gt:
            continue
        best = max(
            (_iou(gt_item["polygon"], pred_item["polygon"]) for pred_item in predictions),
            default=0.0,
        )
        errors.append(
            {
                "kind": "partial_detection" if best > 0 else "detection_miss",
                "gt_index": gt_index,
                "prediction_index": "",
                "iou": best,
                "gt_text": gt_item["text"],
                "prediction_text": "",
            }
        )
    for pred_index, prediction in enumerate(predictions):
        if pred_index not in matched_pred:
            errors.append(
                {
                    "kind": "false_positive",
                    "gt_index": "",
                    "prediction_index": pred_index,
                    "iou": max(
                        (_iou(item["polygon"], prediction["polygon"]) for item in gt_record["gt"]),
                        default=0.0,
                    ),
                    "gt_text": "",
                    "prediction_text": prediction.get("text", ""),
                }
            )
    match_rows = []
    for gt_index, pred_index, score in primary_matches:
        gt_text = gt_record["gt"][gt_index]["text"]
        pred_text = predictions[pred_index].get("text", "")
        exact = gt_text == pred_text
        match_rows.append(
            {
                "gt_index": gt_index,
                "prediction_index": pred_index,
                "iou": score,
                "gt_text": gt_text,
                "prediction_text": pred_text,
                "exact": exact,
                "normalized_exact": _normalized_text(gt_text) == _normalized_text(pred_text),
                "error_kind": "" if exact else "recognition_error",
            }
        )
        if not exact:
            errors.append(
                {
                    "kind": "recognition_error",
                    "gt_index": gt_index,
                    "prediction_index": pred_index,
                    "iou": score,
                    "gt_text": gt_text,
                    "prediction_text": pred_text,
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_count = raw_detection_count if raw_detection_count is not None else _raw_detection_count(detection_pkl)
    metrics = {
        "schema_version": SCHEMA_VERSION,
        "baseline_name": "AI-Hub original weights/code CPU reference baseline",
        "document_type": document_type,
        "image_stem": gt_record["image_stem"],
        "inputs": {
            "gt_json": str(gt_path),
            "normalized_predictions": str(prediction_path),
            "detection_pkl": str(detection_pkl) if detection_pkl else None,
        },
        "counts": {
            "gt_annotations": len(gt_record["gt"]),
            "raw_detection_candidates": raw_count,
            "recognition_predictions": len(predictions),
        },
        "metrics_by_iou_threshold": rows,
        "iou_distribution": {
            "all_gt_prediction_pairs": len(pair_scores),
            "matched_at_0.5": len(primary_matches),
            "matched_iou_ge_0.5": sum(score >= 0.5 for _, _, score in primary_matches),
            "matched_iou_ge_0.8": sum(score >= 0.8 for _, _, score in primary_matches),
            "matched_iou_values": [score for _, _, score in primary_matches],
        },
        "matching": {
            "method": "deterministic maximum-cardinality one-to-one bipartite matching",
            "score": "polygon IoU",
            "thresholds": [0.5, 0.8],
        },
        "official_metric_note": {
            "bundled_evaluator": "evaluation_method/script.py",
            "matching": "PCC inclusion plus area precision constraint, default 0.5; not IoU",
            "e2e": "character-level LCS based score with exact case-sensitive text handling",
        },
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(
        output_dir / "matches.csv",
        match_rows,
        ["gt_index", "prediction_index", "iou", "gt_text", "prediction_text", "exact", "normalized_exact", "error_kind"],
    )
    _write_csv(
        output_dir / "errors.csv",
        errors,
        ["kind", "gt_index", "prediction_index", "iou", "gt_text", "prediction_text"],
    )
    lines = [
        "# AI-Hub original weights/code CPU reference baseline",
        "",
        f"- Document: `{document_type}` / `{gt_record['image_stem']}`",
        f"- GT annotations: {len(gt_record['gt'])}",
        f"- Raw Detection candidates: {raw_count if raw_count is not None else 'not supplied'}",
        f"- Recognition predictions: {len(predictions)}",
        "",
        "## IoU metrics",
        "",
    ]
    for threshold, row in rows.items():
        lines.extend(
            [
                f"### IoU >= {threshold}",
                f"- matched: {row['matched']}",
                f"- detection precision / recall / F1: {row['detection_precision']:.6f} / {row['detection_recall']:.6f} / {row['detection_f1']:.6f}",
                f"- exact recognition on matched: {row['recognition_exact_matches']} / {row['matched']}",
                f"- exact accuracy / CER: {row['recognition_exact_accuracy_on_matched']:.6f} / {row['cer_on_matched']:.6f}",
                f"- normalized exact accuracy: {row['normalized_exact_accuracy_on_matched']:.6f}",
                "",
            ]
        )
    lines.extend(
        [
            "## Matching and metric scope",
            "",
            "IoU metrics use polygon IoU and deterministic one-to-one matching. Raw text is preserved; normalized text is reported separately using Unicode NFKC plus whitespace collapse.",
            "The bundled AI-Hub evaluator is not an IoU evaluator: it uses PCC inclusion and area precision constraint 0.5. Its metric is therefore recorded separately and is not silently substituted here.",
        ]
    )
    (output_dir / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "evaluation_notes.md").write_text(
        "# Evaluation notes\n\n"
        "This evaluation uses the real AI-Hub Validation GT JSON and the unmodified official TXT OCR output. "
        "No threshold, model, preprocessing, decoder, or text correction was applied. "
        "The CPU reference output is not byte-identical evidence for a GPU run.\n",
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-json", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--detection-pkl", type=Path)
    parser.add_argument("--raw-detection-count", type=int)
    parser.add_argument("--document-type", default="Unknown")
    args = parser.parse_args()
    result = evaluate(
        args.gt_json,
        args.predictions,
        args.output_dir,
        args.detection_pkl,
        args.raw_detection_count,
        args.document_type,
    )
    print(json.dumps(result["metrics_by_iou_threshold"], ensure_ascii=False, indent=2))
    print(f"evaluation artifacts -> {args.output_dir}")


if __name__ == "__main__":
    main()
