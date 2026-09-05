"""Run the official AI-Hub logistics OCR against the lightweight sample ZIP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintra_ocr.aihub_backend import AIHubModelPaths, AIHubOCRBackend
from fintra_ocr.sample_validation import validate_sample


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("sample_zip", nargs="?", default="data/sample.zip")
parser.add_argument("--source-root", required=True, help="extracted AI-Hub source_code root")
parser.add_argument("--dictionary", required=True, help="AI-Hub dictionary or recognizer metadata file")
parser.add_argument("--detector-config", type=Path)
parser.add_argument("--detector-checkpoint", type=Path)
parser.add_argument("--recognizer-checkpoint", type=Path)
parser.add_argument("--runtime-python", default=sys.executable)
parser.add_argument("--device", default="cpu")
parser.add_argument("--score-threshold", type=float, default=0.2)
parser.add_argument("--limit", type=int)
parser.add_argument("--output-dir", default="analysis/aihub_sample_e2e")
args = parser.parse_args()

sample_path = Path(args.sample_zip)
if not sample_path.is_file():
    parser.error(f"sample ZIP not found: {sample_path.resolve()}")

model = AIHubModelPaths(
    source_root=Path(args.source_root),
    dictionary=Path(args.dictionary),
    detector_config=args.detector_config,
    detector_checkpoint=args.detector_checkpoint,
    recognizer_checkpoint=args.recognizer_checkpoint,
    runtime_python=args.runtime_python,
    device=args.device,
    timeout_seconds=1200,
)
backend = AIHubOCRBackend(model, score_threshold=args.score_threshold)
print(f"[Fintra OCR] sample={sample_path.resolve()}")
print(f"[Fintra OCR] backend={backend.name} device={args.device} threshold={args.score_threshold}")
print(f"[Fintra OCR] output={Path(args.output_dir).resolve()}")
summary = validate_sample(str(sample_path), backend, output_dir=args.output_dir, limit=args.limit)
print(json.dumps({key: value for key, value in summary.items() if key != "documents"}, ensure_ascii=False, indent=2))
