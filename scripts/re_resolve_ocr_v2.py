"""Rebuild only OCR v2 resolved views from already saved raw regions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fintra.ocr_v2.merge import resolve
from fintra.ocr_v2.models import RawOCRRegion


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root
    count = 0
    for path in sorted(root.glob("*/outputs/recognition/paddle.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = [RawOCRRegion(
            int(item.get("region_id", index)), str(item.get("text", "")), item.get("confidence"),
            item.get("polygon", []), int(item.get("page", 1)), str(item.get("pass_name", "full")),
            int(item.get("pass_index", 0)), int(item.get("source_region_index", index)),
        ) for index, item in enumerate(payload.get("raw_regions", []))]
        resolved, stats = resolve(raw)
        payload["regions"] = [region.to_dict() for region in resolved]
        payload["resolved_regions"] = [region.to_dict() for region in resolved]
        payload.setdefault("metadata", {}).update(stats)
        payload["metadata"]["raw_region_count"] = len(raw)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1
    print(json.dumps({"root": str(root), "re_resolved_cases": count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
