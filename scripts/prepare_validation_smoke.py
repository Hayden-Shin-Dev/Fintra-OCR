"""Select one real document from each requested Azure Validation ZIP pair.

Only the selected image and its paired GT JSON are retained. Downloaded ZIP
copies are removed after successful extraction; Azure blobs are never changed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any


def _run_az(az: Path, args: list[str]) -> Any:
    command = [str(az)] + args
    result = subprocess.run(command, check=True, capture_output=True)
    stdout = result.stdout.decode("mbcs", errors="replace")
    return json.loads(stdout) if stdout.strip() else None


def _polygon_area(points: list[list[int]]) -> float:
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2.0)


def _build_coco(gt: dict[str, Any]) -> dict[str, Any]:
    image = gt["Images"]
    image_name = f'{image["identifier"]}.{image["type"]}'
    annotations = []
    for annotation_id, item in enumerate(gt.get("bbox", []), 1):
        xs, ys = [int(value) for value in item["x"]], [int(value) for value in item["y"]]
        points = [[xs[index], ys[index]] for index in range(len(xs))]
        x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
        annotations.append({
            "id": annotation_id,
            "image_id": 0,
            "category_id": 1,
            "segmentation": [[value for point in points for value in point]],
            "area": _polygon_area(points),
            "bbox": [x_min, y_min, x_max - x_min, y_max - y_min],
            "iscrowd": 0,
        })
    return {
        "info": {"description": "AI-Hub logistics validation smoke case"},
        "licenses": [],
        "images": [{
            "id": 0,
            "file_name": image_name,
            "width": int(image["width"]),
            "height": int(image["height"]),
        }],
        "annotations": annotations,
        "categories": [{"id": 1, "name": "text", "supercategory": "text"}],
    }


def _select_document(source_zip: Path, gt_zip: Path, case_dir: Path, config_template: Path) -> dict[str, Any]:
    with zipfile.ZipFile(source_zip) as source, zipfile.ZipFile(gt_zip) as labels:
        by_name: dict[str, list[str]] = {}
        for name in source.namelist():
            base = Path(name).name
            if Path(base).suffix.lower() in {".png", ".jpg", ".jpeg"}:
                by_name.setdefault(base, []).append(name)

        selected = None
        for label_name in sorted(labels.namelist()):
            if not label_name.lower().endswith(".json"):
                continue
            try:
                gt = json.loads(labels.read(label_name).decode("utf-8"))
                image = gt["Images"]
                image_name = f'{image["identifier"]}.{image["type"]}'
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            candidates = by_name.get(image_name, [])
            if not candidates:
                candidates = [name for name in source.namelist() if Path(name).stem == str(image["identifier"])]
            if candidates:
                selected = (gt, image_name, candidates[0], label_name)
                break
        if selected is None:
            raise RuntimeError(f"no image/GT pair found in {source_zip.name} and {gt_zip.name}")

        gt, image_name, source_name, label_name = selected
        image_path = case_dir / "transit_train" / "imgs_resize" / image_name
        coco_path = case_dir / "transit_train" / "convert_json" / "2023-01-22_latest_test.json"
        raw_gt_path = case_dir / "source_gt" / Path(label_name).name
        image_path.parent.mkdir(parents=True, exist_ok=True)
        coco_path.parent.mkdir(parents=True, exist_ok=True)
        raw_gt_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(source.read(source_name))
        raw_gt_path.write_bytes(labels.read(label_name))
        coco_path.write_text(json.dumps(_build_coco(gt), ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copy2(config_template, case_dir / "transit_train" / "one_doc_transit_config.py")
        return {
            "image": image_name,
            "source_entry": source_name,
            "gt_entry": label_name,
            "gt_annotations": len(gt.get("bbox", [])),
            "image_bytes": image_path.stat().st_size,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--az", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config-template", type=Path, required=True)
    parser.add_argument("--account", default="stfintradevkrc")
    parser.add_argument("--container", default="fintra")
    args = parser.parse_args()

    blobs = _run_az(args.az, [
        "storage", "blob", "list", "--account-name", args.account,
        "--container-name", args.container, "--auth-mode", "login",
        "--prefix", "raw/aihub/Validation/", "--num-results", "*",
        "--query", "[].{name:name,size:properties.contentLength}", "-o", "json",
    ])
    target_root = args.output_root / "smoke"
    target_root.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    targets = [(kind, index) for kind in ("INV", "PL", "BL") for index in range(1, 6)]
    for kind, index in targets:
        suffix = f"{kind}{index:02d}.zip"
        source = [item for item in blobs if "/01." in item["name"] and item["name"].endswith(suffix)]
        labels = [item for item in blobs if "/02." in item["name"] and item["name"].endswith(suffix)]
        if len(source) != 1 or len(labels) != 1:
            raise RuntimeError(f"expected one source/GT pair for {suffix}, got {len(source)}/{len(labels)}")

        case_id = {"INV": "ci", "PL": "pl", "BL": "bl"}[kind] + f"-{index:02d}"
        case_dir = target_root / case_id
        if case_dir.exists() and (case_dir / "case_manifest.json").exists():
            print(f"SKIP={case_id}")
            continue
        download_dir = target_root / ".downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        source_zip = download_dir / f"{case_id}_source.zip"
        gt_zip = download_dir / f"{case_id}_gt.zip"
        print(f"DOWNLOAD={case_id} source_bytes={source[0]['size']} gt_bytes={labels[0]['size']}", flush=True)
        try:
            _run_az(args.az, ["storage", "blob", "download", "--account-name", args.account, "--container-name", args.container, "--auth-mode", "login", "--name", source[0]["name"], "--file", str(source_zip), "--overwrite", "true", "--only-show-errors"])
            _run_az(args.az, ["storage", "blob", "download", "--account-name", args.account, "--container-name", args.container, "--auth-mode", "login", "--name", labels[0]["name"], "--file", str(gt_zip), "--overwrite", "true", "--only-show-errors"])
            selected = _select_document(source_zip, gt_zip, case_dir, args.config_template)
            record = {"case_id": case_id, "kind": kind, "index": index, "source_blob": source[0], "gt_blob": labels[0], **selected}
            (case_dir / "case_manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest.append(record)
            print(f"PREPARED={case_id} image={selected['image']} annotations={selected['gt_annotations']}", flush=True)
        finally:
            for path in (source_zip, gt_zip):
                if path.exists():
                    path.unlink()

    (target_root / "smoke_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PREPARED_COUNT={len(manifest)}")


if __name__ == "__main__":
    main()
