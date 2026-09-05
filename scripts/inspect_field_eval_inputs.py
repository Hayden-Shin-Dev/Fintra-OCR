"""Inspect downloaded AI-Hub Validation ZIP pairs without extracting images.

The inventory is a read-only structural check. It does not assign semantic
field labels and does not create evaluation gold values.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any


SUFFIX = re.compile(r"(?:INV|PL|BL)(\d{2})", re.IGNORECASE)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _kind(path: Path) -> str:
    match = SUFFIX.search(path.name)
    if not match:
        raise ValueError(f"cannot identify document kind: {path.name}")
    return "Commercial Invoice" if "INV" in path.name.upper() else "Packing List" if "PL" in path.name.upper() else "B/L"


def _image_name(payload: dict[str, Any]) -> str:
    image = payload["Images"]
    return f"{image['identifier']}.{image['type']}"


def inspect_pair(source_zip: Path, label_zip: Path) -> dict[str, Any]:
    with zipfile.ZipFile(source_zip) as source, zipfile.ZipFile(label_zip) as labels:
        source_images = {
            Path(name).name: name
            for name in source.namelist()
            if Path(name).suffix.lower() in IMAGE_EXTENSIONS
        }
        label_records = []
        for name in labels.namelist():
            if not name.lower().endswith(".json"):
                continue
            try:
                payload = json.loads(labels.read(name).decode("utf-8"))
                image_name = _image_name(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
                continue
            label_records.append({
                "label_entry": name,
                "image_name": image_name,
                "source_entry": source_images.get(image_name),
                "annotations": len(payload.get("bbox", [])),
                "document_type": str(payload.get("Images", {}).get("form_type", "Unknown")),
            })
        return {
            "document_type": _kind(source_zip),
            "source_zip": str(source_zip),
            "label_zip": str(label_zip),
            "source_entries": len(source.namelist()),
            "source_images": len(source_images),
            "label_json": len(label_records),
            "matched_pairs": sum(item["source_entry"] is not None for item in label_records),
            "labels": label_records,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = {SUFFIX.search(path.name).group(0).upper(): path for path in (args.root / "source").rglob("*.zip") if SUFFIX.search(path.name)}
    labels = {SUFFIX.search(path.name).group(0).upper(): path for path in (args.root / "labels").rglob("*.zip") if SUFFIX.search(path.name)}
    keys = sorted(set(source) & set(labels))
    if len(keys) != 15:
        raise RuntimeError(f"expected 15 source/label pairs, found {len(keys)}")
    pairs = [inspect_pair(source[key], labels[key]) for key in keys]
    result = {
        "schema_version": "fintra-ocr-v2.field-eval-input-inventory.v1",
        "pairs": pairs,
        "totals": {
            "zip_pairs": len(pairs),
            "source_images": sum(item["source_images"] for item in pairs),
            "label_json": sum(item["label_json"] for item in pairs),
            "matched_pairs": sum(item["matched_pairs"] for item in pairs),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], ensure_ascii=False))
    for item in pairs:
        print(f"{item['document_type']}: {Path(item['source_zip']).name} images={item['source_images']} labels={item['label_json']} matched={item['matched_pairs']}")


if __name__ == "__main__":
    main()
