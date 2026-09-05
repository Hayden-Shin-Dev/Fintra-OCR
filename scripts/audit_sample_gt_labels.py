from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fintra_ocr.sample_dataset import iter_target_documents

PHRASES = {
    "invoice_number": [r"invoice\s*(?:number|no\.?)"],
    "buyer": [r"\bbuyer\b"],
    "total_amount": [r"\btotal\b", r"\bamount\b"],
    "quantity": [r"\bquantity\b", r"\bqty\b"],
    "gross_weight": [r"gross\s*(?:weight|wt)"],
    "bl_number": [r"(?:b\s*/\s*l|bill\s+of\s+lading).*?(?:number|no\.?)"],
    "shipper": [r"\bshipper\b"],
    "consignee": [r"\bconsignee\b"],
    "on_board": [r"on\s+board"],
}

parser = argparse.ArgumentParser()
parser.add_argument("sample_zip")
parser.add_argument("--output", default="analysis/sample_gt_anchor_audit.json")
args = parser.parse_args()
report: dict[str, object] = {}
for document in iter_target_documents(args.sample_zip):
    joined = "\n".join(str(item.get("data", "")) for item in document.label.get("bbox", []))
    counts = report.setdefault(document.form_type, {key: 0 for key in PHRASES})
    for key, patterns in PHRASES.items():
        if any(re.search(pattern, joined, re.I) for pattern in patterns):
            counts[key] += 1
report["_note"] = (
    "Counts are documents whose GT bbox text contains static-looking semantic captions. "
    "Low counts mean GT-only label-anchor coverage must not be treated as field existence rate."
)
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
