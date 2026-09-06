"""Profile the existing accurate Paddle execution without changing its output.

The profiler wraps the already-validated backend at runtime. It records
per-document inference-call timings, deduplication timing, and the residual
time (decode, tile scheduling, merge, JSON conversion, and I/O). It never
writes OCR cache files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.ocr import paddle_backend as backend_module
from fintra.ocr.paddle_backend import PaddleOCRBackend


def _manifest(path: Path) -> dict[str, object]:
    return json.loads((path / "case_manifest.json").read_text(encoding="utf-8"))


def _select(gold_cases: Path, limit: int) -> list[Path]:
    selected: list[Path] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(item for item in gold_cases.iterdir() if item.is_dir()):
        manifest = _manifest(path)
        key = (str(manifest.get("document_type")), str(manifest.get("source_group")))
        if key in seen:
            continue
        seen.add(key)
        selected.append(path)
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        raise RuntimeError(f"Only {len(selected)} profile cases available")
    return selected


def profile_case(backend: PaddleOCRBackend, case_dir: Path) -> dict[str, object]:
    manifest = _manifest(case_dir)
    image = case_dir / str(manifest["image"])
    calls: list[dict[str, object]] = []
    original_predict = backend._predict_array

    def timed_predict(image_array):
        shape = tuple(int(value) for value in getattr(image_array, "shape", ()))
        started = time.perf_counter()
        regions, raw = original_predict(image_array)
        calls.append({
            "shape": shape,
            "seconds": time.perf_counter() - started,
            "regions": len(regions),
        })
        return regions, raw

    backend._predict_array = timed_predict
    original_deduplicate = backend_module._deduplicate
    deduplicate_seconds = 0.0

    def timed_deduplicate(regions):
        nonlocal deduplicate_seconds
        started = time.perf_counter()
        result = original_deduplicate(regions)
        deduplicate_seconds += time.perf_counter() - started
        return result

    backend_module._deduplicate = timed_deduplicate
    started = time.perf_counter()
    try:
        result = backend.run_ocr(image, str(manifest["document_type"]))
    finally:
        backend._predict_array = original_predict
        backend_module._deduplicate = original_deduplicate
    total_seconds = time.perf_counter() - started
    inference_seconds = sum(float(call["seconds"]) for call in calls)
    return {
        "case_id": manifest["case_id"],
        "document_type": manifest["document_type"],
        "source_group": manifest.get("source_group"),
        "image": str(image),
        "total_seconds": total_seconds,
        "inference_seconds": inference_seconds,
        "residual_seconds": max(0.0, total_seconds - inference_seconds),
        "deduplicate_seconds": deduplicate_seconds,
        "inference_calls": len(calls),
        "output_regions": len(result.regions),
        "calls": calls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-cases", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/cases")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/paddle-profile.json")
    parser.add_argument("--device", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument("--mode", choices=("accurate",), default="accurate")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    backend = PaddleOCRBackend(device=args.device, mode=args.mode)
    cases = _select(args.gold_cases, args.limit)
    records = []
    for case in cases:
        record = profile_case(backend, case)
        records.append(record)
        print(json.dumps({key: record[key] for key in ("case_id", "document_type", "source_group", "total_seconds", "inference_seconds", "residual_seconds", "deduplicate_seconds", "inference_calls", "output_regions")}, ensure_ascii=False), flush=True)
    summary = {
        "device": args.device,
        "mode": args.mode,
        "cases": len(records),
        "average_total_seconds": sum(float(item["total_seconds"]) for item in records) / len(records),
        "average_inference_seconds": sum(float(item["inference_seconds"]) for item in records) / len(records),
        "average_residual_seconds": sum(float(item["residual_seconds"]) for item in records) / len(records),
        "average_deduplicate_seconds": sum(float(item["deduplicate_seconds"]) for item in records) / len(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PROFILE={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
