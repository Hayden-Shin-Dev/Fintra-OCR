"""Evaluate the independent Extractor v2 through the frozen evaluator.

The evaluator implementation is not copied or modified.  This adapter only
supplies the v2 document payload to its existing normalization, denominator,
and status-comparison functions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fintra.extraction.v2 import EXTRACTORS
from scripts import evaluate_field_extraction as frozen_evaluator


def evaluate(cases: Path, output_dir: Path, gold_source: str, gold_root: Path | None = None):
    original = frozen_evaluator._document_payload

    def v2_payload(result, _strategy="v2"):
        return EXTRACTORS[result.document_type](result).to_dict()

    frozen_evaluator._document_payload = v2_payload
    try:
        return frozen_evaluator.evaluate(cases, output_dir, "v2", gold_source, gold_root)
    finally:
        frozen_evaluator._document_payload = original


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gold-source", default="semantic-v4")
    parser.add_argument("--gold-root", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.cases, args.output_dir, args.gold_source, args.gold_root)
    print({"documents": result["selection"]["documents"], "applicable_gold": result["overall"]["applicable_gold"], "normalized": result["overall"]["normalized_field_accuracy"]})
    print(f"FIELD_RESULTS={args.output_dir / 'field_results.csv'}")
    print(f"FIELD_METRICS={args.output_dir / 'field_metrics.json'}")


if __name__ == "__main__":
    main()
