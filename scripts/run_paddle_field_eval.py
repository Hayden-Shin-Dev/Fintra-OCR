"""Run isolated PaddleOCR on the current field-evaluation cases.

This runner is deliberately separate from RUN_FIELD_EVAL_GPU.ps1. It creates a
new output tree and applies the existing extractor/evaluator to Paddle's
canonical OCR JSON without changing the Modern artifacts or gold files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.ocr.adapter import OCRResult
from fintra.ocr.paddle_backend import PaddleOCRBackend
from scripts.evaluate_field_extraction import evaluate


TYPE_ORDER = ("Commercial Invoice", "Packing List", "B/L")


def _manifest(case_dir: Path) -> dict[str, object]:
    return json.loads((case_dir / "case_manifest.json").read_text(encoding="utf-8"))


def select_cases(cases_root: Path, *, smoke: bool, limit: int | None) -> list[Path]:
    cases = []
    for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        if manifest_path.is_file():
            cases.append((case_dir, _manifest(case_dir)))
    if smoke:
        selected = []
        for document_type in TYPE_ORDER:
            match = next((item for item in cases if item[1].get("document_type") == document_type), None)
            if match is None:
                raise RuntimeError(f"Smoke case missing for {document_type}")
            selected.append(match)
        cases = selected
    if limit is not None:
        cases = cases[:limit]
    if not cases:
        raise RuntimeError("No prepared field-evaluation cases found")
    return [case_dir for case_dir, _ in cases]


def _prepare_case(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "case_manifest.json", destination / "case_manifest.json")
    shutil.copy2(source / "semantic_gold_fields.json", destination / "semantic_gold_fields.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "artifacts/fintra/field_eval/cases")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/fintra/paddle_field_eval")
    parser.add_argument("--device", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--mode", choices=("fast", "accurate"), default="accurate")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--smoke", action="store_true", help="run exactly one case of each document type")
    args = parser.parse_args()

    selected = select_cases(args.cases, smoke=args.smoke, limit=args.limit)
    case_output = args.output_dir / "cases"
    backend = PaddleOCRBackend(device=args.device, mode=args.mode)
    print(f"PADDLE_CASES={len(selected)}")
    print(f"PADDLE_DEVICE={args.device}")
    print(f"PADDLE_MODE={args.mode}")

    for source_case in selected:
        manifest = _manifest(source_case)
        image = source_case / str(manifest["image"])
        if not image.is_file():
            raise FileNotFoundError(image)
        destination = case_output / str(manifest["case_id"])
        _prepare_case(source_case, destination)
        existing = destination / "outputs" / "recognition" / "paddle.json"
        if existing.is_file():
            try:
                existing_payload = json.loads(existing.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing_payload = None
            if isinstance(existing_payload, dict) and isinstance(existing_payload.get("regions"), list):
                print(f"[{manifest['case_id']}] reusing existing Paddle output")
                continue
        result = backend.run_ocr(image, str(manifest["document_type"]))
        raw_dir = destination / "outputs" / "raw"
        recognition_dir = destination / "outputs" / "recognition"
        raw_dir.mkdir(parents=True, exist_ok=True)
        recognition_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "paddle_raw.json"
        raw_path.write_text(result.raw_output or "[]", encoding="utf-8")
        canonical = replace(result, raw_output_path=str(raw_path))
        (recognition_dir / "paddle.json").write_text(
            json.dumps(canonical.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[{manifest['case_id']}] regions={len(result.regions)}")

    report = evaluate(case_output, args.output_dir, strategy="active", gold_source="semantic-v2")
    print(json.dumps({
        "documents": report["selection"]["documents"],
        "applicable_gold": report["overall"]["applicable_gold"],
        "normalized_accuracy": report["overall"]["normalized_field_accuracy"],
        "output": str(args.output_dir.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
