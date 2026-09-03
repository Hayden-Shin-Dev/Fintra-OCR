"""Create a comparable lightweight-sample report for AI-Hub and PaddleOCR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    "exact_text_recall",
    "segmentation_aware_recall",
    "similarity_90_recall",
    "mean_cer",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(aihub: dict[str, Any], paddle: dict[str, Any]) -> dict[str, Any]:
    by_form: dict[str, Any] = {}
    for form in sorted(set(aihub["by_form"]) | set(paddle["by_form"])):
        ai = aihub["by_form"].get(form, {})
        pd = paddle["by_form"].get(form, {})
        by_form[form] = {
            "documents": ai.get("documents", pd.get("documents", 0)),
            "aihub": {metric: ai.get(metric) for metric in METRICS},
            "paddle": {metric: pd.get(metric) for metric in METRICS},
            "delta_aihub_minus_paddle": {
                metric: float(ai[metric]) - float(pd[metric])
                for metric in METRICS
                if metric in ai and metric in pd
            },
        }

    return {
        "dataset": aihub.get("dataset"),
        "evaluated_documents": aihub.get("evaluated_documents"),
        "aihub": {
            "backend": aihub.get("backend"),
            "elapsed_seconds": aihub.get("elapsed_seconds"),
            "real_pretrained_inference": True,
            "detector": "AI-Hub OCRMaskRCNN / ResNet-50 + FPN + mask head",
            "recognizer": "AI-Hub vitstr_small_patch16_224",
        },
        "paddle": {
            "backend": paddle.get("backend"),
            "elapsed_seconds": paddle.get("elapsed_seconds"),
        },
        "by_form": by_form,
        "field_quality": {
            "aihub": aihub.get("field_quality", {}),
            "paddle": paddle.get("field_quality", {}),
            "note": "Field coverage/agreement is extractor-dependent and is not an OCR-only metric.",
        },
        "metric_note": (
            "Both backends use the same lightweight target labels and evaluator. "
            "AI-Hub confidence comes from recognizer token probabilities; no fake score is inserted."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aihub", type=Path, default=Path("analysis/aihub_sample_e2e/summary.json"))
    parser.add_argument("--paddle", type=Path, default=Path("analysis/sample_e2e/summary.json"))
    parser.add_argument("--output", type=Path, default=Path("analysis/aihub_paddle_ab.json"))
    args = parser.parse_args()
    report = compare(_load(args.aihub), _load(args.paddle))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["by_form"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
