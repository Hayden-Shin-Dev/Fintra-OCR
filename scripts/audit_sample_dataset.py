from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fintra_ocr.sample_dataset import audit_sample_zip

parser = argparse.ArgumentParser()
parser.add_argument("sample_zip")
parser.add_argument("--output", default="analysis/sample_audit.json")
args = parser.parse_args()
report = audit_sample_zip(args.sample_zip)
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
