"""Compare Modern Detection JSON with the already-produced original PKL."""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon


def load_reference(path, image_index):
    with path.open("rb") as stream:
        payload = pickle.load(stream)
    if isinstance(payload, dict) and "boundary_result" in payload:
        return payload["boundary_result"]
    if isinstance(payload, (list, tuple)):
        item = payload[image_index]
        if isinstance(item, dict):
            return item["boundary_result"]
        if isinstance(item, (list, tuple)) and item and isinstance(item[0], dict):
            return item[0]["boundary_result"]
    raise ValueError("Unsupported original Detection PKL structure")


def polygon_iou(left, right):
    try:
        a = Polygon(np.asarray(left, dtype=float).reshape(4, 2))
        b = Polygon(np.asarray(right, dtype=float).reshape(4, 2))
        if not a.is_valid or not b.is_valid:
            return 0.0
        union = a.union(b).area
        return float(a.intersection(b).area / union) if union else 0.0
    except (ValueError, TypeError):
        return 0.0


def normalize_reference(rows, threshold):
    normalized = []
    for row in rows:
        score = float(row[-1])
        if score > threshold:
            normalized.append({"boundary": [float(value) for value in row[:-1]], "score": score})
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-pkl", required=True, type=Path)
    parser.add_argument("--modern-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--image-index", type=int, default=0)
    args = parser.parse_args()

    modern_payload = json.loads(args.modern_json.read_text(encoding="utf-8"))
    threshold = float(modern_payload.get("score_threshold", 0.2))
    reference_all = load_reference(args.reference_pkl, args.image_index)
    reference = normalize_reference(reference_all, threshold)
    modern = modern_payload["candidates"]
    pairs = []
    used = set()
    for ref_index, ref in enumerate(reference):
        choices = sorted(
            ((polygon_iou(ref["boundary"], item["boundary"]), index) for index, item in enumerate(modern) if index not in used),
            reverse=True,
        )
        if choices and choices[0][0] > 0:
            iou, modern_index = choices[0]
            used.add(modern_index)
            pairs.append((ref_index, modern_index, iou))

    ordered = min(len(reference), len(modern))
    coordinate_diffs = []
    score_diffs = []
    for index in range(ordered):
        coordinate_diffs.extend(abs(float(a) - float(b)) for a, b in zip(reference[index]["boundary"], modern[index]["boundary"]))
        score_diffs.append(abs(reference[index]["score"] - float(modern[index]["score"])))
    ious = [item[2] for item in pairs]
    result = {
        "reference_raw_candidate_count": len(reference_all),
        "modern_raw_candidate_count": int(modern_payload.get("raw_candidate_count", len(modern))),
        "reference_score_gt_0_2_count": len(reference),
        "modern_score_gt_0_2_count": len(modern),
        "matched_count": len(pairs),
        "unmatched_reference": len(reference) - len(pairs),
        "unmatched_modern": len(modern) - len(pairs),
        "mean_bbox_iou": float(np.mean(ious)) if ious else 0.0,
        "median_bbox_iou": float(np.median(ious)) if ious else 0.0,
        "iou_ge_0_5_match_rate": sum(iou >= 0.5 for iou in ious) / len(reference) if reference else 0.0,
        "iou_ge_0_8_match_rate": sum(iou >= 0.8 for iou in ious) / len(reference) if reference else 0.0,
        "mean_absolute_score_difference": float(np.mean(score_diffs)) if score_diffs else 0.0,
        "max_coordinate_difference": max(coordinate_diffs) if coordinate_diffs else 0.0,
        "candidate_order_same_count": sum(reference[i]["boundary"] == modern[i]["boundary"] for i in range(ordered)),
        "candidate_count_equal": len(reference) == len(modern),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

