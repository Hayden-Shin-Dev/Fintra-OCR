"""Create a non-destructive GT/prediction debug overlay with OpenCV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from evaluate_baseline import _iou, _match, _polygon, _read_gt, _read_predictions


def _points(polygon):
    return np.asarray([[int(round(x)), int(round(y))] for x, y in polygon], dtype=np.int32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--gt-json", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    args = parser.parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        raise ValueError(f"unable to read image: {args.image}")
    gt_record = _read_gt(args.gt_json)
    prediction_map = _read_predictions(args.predictions)
    predictions = prediction_map.get(gt_record["image_stem"], [])
    for prediction in predictions:
        prediction["polygon"] = _polygon(prediction["polygon"])
    matches = _match(gt_record["gt"], predictions, args.iou_threshold)
    by_gt = {gt: (pred, score) for gt, pred, score in matches}
    by_pred = {pred: (gt, score) for gt, pred, score in matches}

    for gt_index, item in enumerate(gt_record["gt"]):
        matched = gt_index in by_gt
        color = (0, 190, 0) if matched else (0, 0, 255)
        cv2.polylines(image, [_points(item["polygon"])], True, color, 2)
        x, y = _points(item["polygon"])[0]
        label = f"GT {gt_index} {'M' if matched else 'MISS'}"
        if matched:
            label += f" P{by_gt[gt_index][0]} IoU {by_gt[gt_index][1]:.2f}"
        cv2.putText(image, label, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

    for pred_index, item in enumerate(predictions):
        matched = pred_index in by_pred
        color = (255, 150, 0) if matched else (255, 0, 255)
        cv2.polylines(image, [_points(item["polygon"])], True, color, 1)
        x, y = _points(item["polygon"])[0]
        label = f"P {pred_index} {'M' if matched else 'FP'}"
        if matched:
            label += f" G{by_pred[pred_index][0]}"
        cv2.putText(image, label, (int(x), int(y) + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.36, color, 1, cv2.LINE_AA)

    legend = "GT matched=green GT miss=red | pred matched=orange pred FP=magenta | labels/text in matches.csv"
    cv2.rectangle(image, (0, 0), (image.shape[1], 30), (30, 30, 30), -1)
    cv2.putText(image, legend, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), image):
        raise RuntimeError(f"unable to write overlay: {args.output}")
    print(json.dumps({"output": str(args.output), "gt": len(gt_record["gt"]), "predictions": len(predictions), "matches": len(matches)}))


if __name__ == "__main__":
    main()
