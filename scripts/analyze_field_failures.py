"""Write evidence-rich RCA for all evaluable field failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintra_ocr.failure_analysis import analyze_failure_directory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-zip", help="Optional paired sample ZIP used to reconstruct full oracle evidence")
    parser.add_argument("--baseline-report", help="Existing baseline evaluation JSON defining the failure denominator")
    parser.add_argument("--comparison-report", help="Optional second-backend report defining a comparable field intersection")
    args = parser.parse_args()
    report = analyze_failure_directory(args.input_dir, args.sample_zip, args.baseline_report, args.comparison_report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"failures": report["failure_count"], "classes": report["failure_class_counts"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
