"""Prepare one verified AI-Hub validation document for the bundled detector."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def polygon_area(points):
    return abs(
        sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )
        / 2.0
    )


def build_coco(gt):
    image_info = gt["Images"]
    image_name = f'{image_info["identifier"]}.{image_info["type"]}'
    annotations = []

    for annotation_id, item in enumerate(gt["bbox"], start=1):
        xs = [int(value) for value in item["x"]]
        ys = [int(value) for value in item["y"]]
        if len(xs) != 4 or len(ys) != 4:
            raise ValueError(f"bbox {annotation_id} does not contain four points")

        points = [[xs[index], ys[index]] for index in range(4)]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        annotations.append(
            {
                "id": annotation_id,
                "image_id": 0,
                "category_id": 1,
                "segmentation": [[value for point in points for value in point]],
                "area": polygon_area(points),
                "bbox": [x_min, y_min, x_max - x_min, y_max - y_min],
                "iscrowd": 0,
            }
        )

    return {
        "info": {"description": "AI-Hub logistics validation case"},
        "licenses": [],
        "images": [
            {
                "id": 0,
                "file_name": image_name,
                "width": int(image_info["width"]),
                "height": int(image_info["height"]),
            }
        ],
        "annotations": annotations,
        "categories": [{"id": 1, "name": "text", "supercategory": "text"}],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    with args.gt.open("r", encoding="utf-8") as handle:
        gt = json.load(handle)

    image_info = gt["Images"]
    image_name = f'{image_info["identifier"]}.{image_info["type"]}'
    image_destination = args.output_root / "transit_train" / "imgs_resize" / image_name
    json_destination = (
        args.output_root
        / "transit_train"
        / "convert_json"
        / "2023-01-22_latest_test.json"
    )
    raw_gt_destination = args.output_root / "source_gt" / args.gt.name

    image_destination.parent.mkdir(parents=True, exist_ok=True)
    json_destination.parent.mkdir(parents=True, exist_ok=True)
    raw_gt_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.image, image_destination)
    shutil.copy2(args.gt, raw_gt_destination)
    json_destination.write_text(
        json.dumps(build_coco(gt), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"IMAGE={image_destination}")
    print(f"COCO={json_destination}")
    print(f"RAW_GT={raw_gt_destination}")
    print(f"ANNOTATIONS={len(gt['bbox'])}")


if __name__ == "__main__":
    main()
