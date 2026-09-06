"""Create a resumable Paddle OCR cache for the Training DEV-SCALE.

The runner reads only the sampled images and source-derived gold manifests. It
does not modify the frozen OCR outputs or semantic-v3.1 benchmark. Existing
valid per-case JSON is reused so an interrupted run can resume safely.
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

from fintra.ocr.paddle_backend import PaddleOCRBackend


def _manifest(case_dir: Path) -> dict[str, object]:
    return json.loads((case_dir / "case_manifest.json").read_text(encoding="utf-8"))


def select_cases(gold_cases: Path, split: str, limit: int | None) -> list[Path]:
    cases = []
    for path in sorted(item for item in gold_cases.iterdir() if item.is_dir()):
        manifest_path = path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _manifest(path)
        if split != "all" and manifest.get("split") != split:
            continue
        cases.append(path)
    if limit is not None:
        cases = cases[:limit]
    if not cases:
        raise RuntimeError(f"No Training gold cases found for split={split}")
    return cases


def _prepare_case(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("case_manifest.json", "semantic_gold_fields.json"):
        shutil.copy2(source / name, destination / name)


def _valid_output(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and isinstance(payload.get("regions"), list)


def run(gold_cases: Path, output_dir: Path, device: str, mode: str, split: str, limit: int | None) -> dict[str, object]:
    selected = select_cases(gold_cases, split, limit)
    output_cases = output_dir / "cases"
    backend = PaddleOCRBackend(device=device, mode=mode)
    counts = {"selected": len(selected), "processed": 0, "reused": 0}
    for source_case in selected:
        manifest = _manifest(source_case)
        image = source_case / str(manifest["image"])
        if not image.is_file():
            raise FileNotFoundError(image)
        destination = output_cases / str(manifest["case_id"])
        _prepare_case(source_case, destination)
        recognition_dir = destination / "outputs" / "recognition"
        raw_dir = destination / "outputs" / "raw"
        canonical_path = recognition_dir / "paddle.json"
        if _valid_output(canonical_path):
            counts["reused"] += 1
            print(f"[{manifest['case_id']}] reusing existing Paddle output", flush=True)
            continue

        result = backend.run_ocr(image, str(manifest["document_type"]))
        recognition_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "paddle_raw.json"
        raw_path.write_text(result.raw_output or "[]", encoding="utf-8")
        canonical = replace(result, raw_output_path=str(raw_path))
        canonical_path.write_text(json.dumps(canonical.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts["processed"] += 1
        print(f"[{manifest['case_id']}] regions={len(result.regions)} processed={counts['processed']}", flush=True)

    summary = {**counts, "output_dir": str(output_dir.resolve()), "split": split, "device": device, "mode": mode}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"cache_summary_{split.lower()}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-cases", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/cases")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/paddle-ocr")
    parser.add_argument("--device", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument("--mode", choices=("fast", "accurate"), default="accurate")
    parser.add_argument("--split", choices=("DEV", "INTERNAL-HOLDOUT", "all"), default="DEV")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args.gold_cases, args.output_dir, args.device, args.mode, args.split, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
