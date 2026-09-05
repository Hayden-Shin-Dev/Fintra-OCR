from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fintra_ocr.e2e_pipeline import run_document
from fintra_ocr.ocr_backends import PaddleOCRBackend, TesseractOCRBackend

parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("--form-type", required=True, choices=("상업송장", "포장명세서", "선하증권"))
parser.add_argument("--backend", choices=("paddle", "tesseract"), default="paddle")
parser.add_argument("--device", default="auto", help="auto selects CUDA GPU when available")
parser.add_argument("--ocr-mode", choices=("fast", "accurate"), default="accurate")
parser.add_argument("--output")
args = parser.parse_args()

resolved_device = args.device
if args.backend == "paddle" and args.device == "auto":
    try:
        import paddle
        resolved_device = "gpu" if paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0 else "cpu"
    except Exception:
        resolved_device = "cpu"

backend = (
    PaddleOCRBackend(device=resolved_device, mode=args.ocr_mode)
    if args.backend == "paddle"
    else TesseractOCRBackend()
)
image_path = Path(args.image)
result = run_document(image_path.read_bytes(), args.form_type, image_path.stem, backend)
payload = dict(result.document)
text = json.dumps(payload, ensure_ascii=False, indent=2)
if args.output:
    Path(args.output).write_text(text, encoding="utf-8")
print(text)
