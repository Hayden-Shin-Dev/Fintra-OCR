"""Re-evaluate historical extractor checkpoints without changing the worktree.

The historical ``documents.py`` source is loaded from a Git object into an
isolated module.  OCR JSON, Gold, and the evaluator contract are unchanged;
the current working tree is never checked out or reset.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import evaluate_field_extraction as evaluator


DEFAULT_REVISIONS = ("b8d53ee", "d23a7cb", "055d28f")


def _load_documents(revision: str) -> ModuleType:
    source = subprocess.check_output(
        ["git", "show", f"{revision}:fintra/extraction/documents.py"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    module = ModuleType(f"fintra.extraction.historical_documents_{revision}")
    module.__file__ = f"git:{revision}:fintra/extraction/documents.py"
    module.__package__ = "fintra.extraction"
    sys.modules[module.__name__] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def _evaluate_with_module(module: ModuleType, cases: Path, output: Path, gold_source: str, gold_root: Path | None) -> dict[str, object]:
    functions = {
        "Commercial Invoice": module.extract_commercial_invoice,
        "Packing List": module.extract_packing_list,
        "B/L": module.extract_bill_of_lading,
    }
    original = evaluator._document_payload

    def payload(result, strategy="active"):
        return functions[result.document_type](result).to_dict()

    evaluator._document_payload = payload
    try:
        return evaluator.evaluate(cases, output, strategy="historical", gold_source=gold_source, gold_root=gold_root)
    finally:
        evaluator._document_payload = original


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/fintra/extractor-rebuild/historical")
    parser.add_argument("--revisions", nargs="+", default=list(DEFAULT_REVISIONS))
    args = parser.parse_args()
    datasets = (
        ("Accurate75-1", ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1", "semantic-v4", ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases"),
        ("Fast300", ROOT / "artifacts/fintra/train-scale-v1/balanced300-eval-cases-v1", "semantic-v4", ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases"),
        ("DEV60-legacy", ROOT / "artifacts/fintra/field_eval/cases", "legacy", None),
    )
    report: dict[str, object] = {"revisions": {}, "ocr_modified": False, "gold_modified": False}
    for revision in args.revisions:
        module = _load_documents(revision)
        revision_report: dict[str, object] = {}
        for name, cases, gold_source, gold_root in datasets:
            revision_report[name] = _evaluate_with_module(module, cases, args.output / revision / name, gold_source, gold_root)
        report["revisions"][revision] = revision_report
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "historical_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"revisions": list(report["revisions"]), "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
