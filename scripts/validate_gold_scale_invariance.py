"""Run prediction-blind scale invariance checks for a Gold generator."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_semantic_v3_2_gold import build_v3_2  # noqa: E402


def signature(fields: list[dict]) -> list[tuple]:
    return [(field["field_name"], field.get("value"), field.get("status"), tuple(field.get("source_token_indices", []))) for field in fields]


def scale_payload(payload: dict, factor: float) -> dict:
    scaled = json.loads(json.dumps(payload))
    image = scaled.setdefault("Images", {})
    image["width"] = float(image.get("width", 1654)) * factor
    image["height"] = float(image.get("height", 2340)) * factor
    for item in scaled.get("bbox", []):
        item["x"] = [value * factor for value in item.get("x", [])]
        item["y"] = [value * factor for value in item.get("y", [])]
    return scaled


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ids = [line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    failures = []
    types = Counter()
    processed = 0
    for case_id in ids:
        case = args.cases_root / case_id
        manifest = json.loads((case / "case_manifest.json").read_text(encoding="utf-8"))
        payload = json.loads((case / "source_annotation.json").read_text(encoding="utf-8"))
        document_type = manifest["document_type"]
        reference = signature(build_v3_2(payload, document_type))
        for factor in (0.5, 1.5, 2.0):
            actual = signature(build_v3_2(scale_payload(payload, factor), document_type))
            if actual != reference:
                failures.append({"case_id": case_id, "document_type": document_type, "scale": factor})
        types[document_type] += 1
        processed += 1
    result = {
        "cases": processed,
        "by_document_type": dict(types),
        "scales": [0.5, 1.5, 2.0],
        "failures": len(failures),
        "failure_examples": failures[:20],
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
        "status": "PASS" if not failures else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
