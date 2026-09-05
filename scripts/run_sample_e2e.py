from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fintra_ocr.ocr_backends import PaddleOCRBackend, TesseractOCRBackend
from fintra_ocr.sample_validation import validate_sample

parser = argparse.ArgumentParser(description="Run Fintra OCR E2E validation on the lightweight sample ZIP")
parser.add_argument(
    "sample_zip",
    nargs="?",
    default="data/sample.zip",
    help="sample ZIP path (default: data/sample.zip)",
)
parser.add_argument("--backend", choices=("paddle", "tesseract"), default="paddle")
parser.add_argument("--device", default="auto", help="auto selects GPU when the installed Paddle build can use CUDA")
parser.add_argument("--ocr-mode", choices=("fast", "accurate"), default="accurate", help="fast=single full-page pass, accurate=full-page + overlapping high-resolution tiles")
parser.add_argument("--limit", type=int)
parser.add_argument("--output-dir", default="analysis/sample_e2e")
args = parser.parse_args()

sample_path = Path(args.sample_zip)
if not sample_path.is_file():
    parser.error(f"sample ZIP not found: {sample_path.resolve()}")

resolved_device = args.device
if args.backend == "paddle" and args.device == "auto":
    try:
        import paddle
        resolved_device = "gpu" if paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0 else "cpu"
    except Exception:
        resolved_device = "cpu"

print(f"[Fintra OCR] sample={sample_path.resolve()}")
print(f"[Fintra OCR] backend={args.backend} device={resolved_device} mode={args.ocr_mode if args.backend == 'paddle' else 'smoke'}")
print(f"[Fintra OCR] output={Path(args.output_dir).resolve()}")

if args.backend == "paddle":
    backend = PaddleOCRBackend(device=resolved_device, mode=args.ocr_mode)
else:
    backend = TesseractOCRBackend()

summary = validate_sample(
    str(sample_path), backend, output_dir=args.output_dir, limit=args.limit
)
print(json.dumps({k: v for k, v in summary.items() if k != "documents"}, ensure_ascii=False, indent=2))
