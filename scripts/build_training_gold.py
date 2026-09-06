"""Build prediction-blind field gold for the deterministic Training DEV-SCALE.

This output is intentionally separate from the frozen 60-document
``semantic-v3.1`` benchmark.  It projects only AI-Hub word annotations into
the existing inspected template rules.  Images with a non-template native
size are normalized to the template coordinate system while building the
candidate, then evidence boxes are mapped back to native image coordinates.
No OCR or extractor output is read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import build_semantic_v3_gold as semantic_v3


TEMPLATE_WIDTH = 1654.0
TEMPLATE_HEIGHT = 2340.0


def _normalized_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], float, float]:
    image = payload.get("Images") or {}
    width = float(image.get("width") or TEMPLATE_WIDTH)
    height = float(image.get("height") or TEMPLATE_HEIGHT)
    sx, sy = TEMPLATE_WIDTH / width, TEMPLATE_HEIGHT / height
    normalized = dict(payload)
    boxes = []
    for item in payload.get("bbox", []):
        copied = dict(item)
        copied["x"] = [float(value) * sx for value in item.get("x", [])]
        copied["y"] = [float(value) * sy for value in item.get("y", [])]
        boxes.append(copied)
    normalized["bbox"] = boxes
    return normalized, sx, sy


def _native_bbox(field: dict[str, Any], sx: float, sy: float) -> None:
    bbox = field.get("bbox")
    if not bbox:
        return
    field["bbox"] = [[float(point[0]) / sx, float(point[1]) / sy] for point in bbox]


def _link_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    try:
        os.link(source, target)
    except OSError:
        target.write_bytes(source.read_bytes())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(input_root: Path, output_root: Path) -> dict[str, Any]:
    source_manifest = input_root / "manifest.jsonl"
    rows = [json.loads(line) for line in source_manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    case_root = output_root / "cases"
    case_root.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    document_type_counts: dict[str, int] = {}
    output_rows: list[dict[str, Any]] = []

    for row in rows:
        stable_id = str(row["stable_sample_id"])
        label_path = input_root / str(row["label_path"])
        image_path = input_root / str(row["source_path"])
        payload = json.loads(label_path.read_text(encoding="utf-8"))
        normalized, sx, sy = _normalized_payload(payload)
        fields = semantic_v3.build_v3(normalized, str(row["document_type"]))
        for field in fields:
            _native_bbox(field, sx, sy)
            status = str(field.get("status", "unknown"))
            status_counts[status] = status_counts.get(status, 0) + 1

        target = case_root / stable_id
        target.mkdir(parents=True, exist_ok=True)
        _link_or_copy(image_path, target / "image.png")
        _link_or_copy(label_path, target / "source_annotation.json")
        manifest = {
            "case_id": stable_id,
            "stable_sample_id": stable_id,
            "document_id": row["document_id"],
            "document_type": row["document_type"],
            "split": row["split"],
            "image": "image.png",
            "source_annotation": "source_annotation.json",
            "source_group": row["source_group"],
            "gold_method": "AI-Hub word-level annotation plus normalized inspected template rules; prediction-blind",
        }
        (target / "case_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "semantic_gold_fields.json").write_text(json.dumps(fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_rows.append({**row, "gold_case": f"cases/{stable_id}", "gold_fields": len(fields)})
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1
        document_type_counts[row["document_type"]] = document_type_counts.get(row["document_type"], 0) + 1

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.jsonl"
    manifest_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in output_rows) + "\n", encoding="utf-8")
    (output_root / "manifest.sha256").write_text(_sha256(manifest_path) + "  manifest.jsonl\n", encoding="utf-8")
    metrics = {
        "schema_version": "fintra-ocr-v2.train-scale-v1.gold.v1",
        "prediction_blind": True,
        "source_manifest": str(source_manifest),
        "documents": len(output_rows),
        "split_counts": dict(sorted(split_counts.items())),
        "document_type_counts": dict(sorted(document_type_counts.items())),
        "gold_status_counts": dict(sorted(status_counts.items())),
        "gold_root": str(case_root),
        "manifest": str(manifest_path),
        "note": "Separate Training-scale candidate gold; frozen semantic-v3.1 is unchanged.",
    }
    (output_root / "gold_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=Path("artifacts/fintra/devscale1500"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/fintra/train-scale-v1"))
    args = parser.parse_args()
    print(json.dumps(build(args.input_root, args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
