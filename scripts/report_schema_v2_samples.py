"""Render one cached Accurate OCR sample per document type through v2.

This reads existing Paddle JSON only; it never runs OCR and never reads Gold.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction.v2 import EXTRACTORS
from fintra.extraction.v2.specs import COMPATIBILITY_DOCUMENT_FIELDS, DOCUMENT_FIELDS, ITEM_FIELDS
from fintra.ocr.adapter import OCRResult


def _slots(document_type: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(DOCUMENT_FIELDS[document_type] + COMPATIBILITY_DOCUMENT_FIELDS.get(document_type, ())))


def render(cache_root: Path) -> dict:
    samples = {}
    for document_type in ("Commercial Invoice", "Packing List", "B/L"):
        selected = None
        for case_dir in sorted(path for path in cache_root.iterdir() if path.is_dir()):
            manifest = case_dir / "case_manifest.json"
            ocr_path = case_dir / "outputs/recognition/paddle.json"
            if not manifest.is_file() or not ocr_path.is_file():
                continue
            if json.loads(manifest.read_text(encoding="utf-8")).get("document_type") == document_type:
                selected = (case_dir, manifest, ocr_path)
                break
        if selected is None:
            raise FileNotFoundError(f"no cached sample for {document_type} under {cache_root}")
        case_dir, manifest, ocr_path = selected
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        result = OCRResult.from_json(ocr_path, document_type=document_type, preserve_raw=False)
        document = EXTRACTORS[document_type](result).to_dict()
        samples[document_type] = {
            "case_id": manifest_payload.get("case_id", case_dir.name),
            "cache_path": str(ocr_path),
            "fields": {name: document.get(name, {}).get("value") for name in _slots(document_type)},
            "items": [
                {name: row.get(name, {}).get("value") for name in ITEM_FIELDS.get(document_type, ())}
                for row in document.get("items", [])
            ],
        }
    return {"source": str(cache_root), "ocr_rerun": False, "gold_read": False, "samples": samples}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/paddle-ocr-accurate-holdout/cases"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/schema-v2"))
    args = parser.parse_args()
    report = render(args.cache_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "contract_sample_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Schema v2 cached contract samples", "", f"Source: `{report['source']}`", "", "No OCR rerun; Gold not read.", ""]
    for document_type, sample in report["samples"].items():
        lines.extend([f"## {document_type} — `{sample['case_id']}`", "", "| Field | Value |", "| --- | --- |"])
        lines.extend(f"| `{name}` | {json.dumps(value, ensure_ascii=False)} |" for name, value in sample["fields"].items())
        lines.extend(["", f"Items: {len(sample['items'])}", ""])
        for index, item in enumerate(sample["items"]):
            lines.append(f"- item[{index}]: {json.dumps(item, ensure_ascii=False)}")
        lines.append("")
    (args.output_dir / "SCHEMA_V2_CACHED_SAMPLES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output_dir / "contract_sample_report.json")
    print(args.output_dir / "SCHEMA_V2_CACHED_SAMPLES.md")


if __name__ == "__main__":
    main()
