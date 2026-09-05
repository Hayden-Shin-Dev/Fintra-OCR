"""Run the two-backend Fintra MVP hybrid on a bounded sample.

This runner is deliberately separate from the 6-variant preprocessing
experiment. It executes each backend once per document, arbitrates fields
without changing the extractor, and writes resumable per-document JSON output.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintra_ocr.aihub_backend import AIHubModelPaths, AIHubOCRBackend
from fintra_ocr.common_schema import DOCUMENT_FIELD_KEYS
from fintra_ocr.e2e_pipeline import build_document_from_predictions
from fintra_ocr.field_evaluation import _classify_field
from fintra_ocr.hybrid_pipeline import HybridPolicy, build_hybrid_document
from fintra_ocr.gt_recall import evaluate_gt_recall
from fintra_ocr.ocr_backends import PaddleOCRBackend
from fintra_ocr.oracle_validation import build_oracle_document
from fintra_ocr.sample_dataset import iter_target_documents, read_image_bytes
from fintra_ocr.label_bbox import parse_bounding_boxes


def _prediction_json(predictions):
    return [
        {
            "text": item.text,
            "confidence": item.score,
            "bbox": [
                [min(item.x), min(item.y)],
                [max(item.x), min(item.y)],
                [max(item.x), max(item.y)],
                [min(item.x), max(item.y)],
            ],
        }
        for item in predictions
    ]


def _document_fields(document, oracle_document, predictions, form_type):
    expected_fields = oracle_document["fields"]
    actual_fields = document["fields"]
    names = sorted(DOCUMENT_FIELD_KEYS[document["document_type"]])
    results = []
    for field_name in names:
        actual = actual_fields.get(field_name, {"status": "missing"})
        expected = expected_fields.get(field_name, {"status": "missing"})
        classification = _classify_field(field_name, actual, expected, predictions)
        results.append(
            {
                "field": field_name,
                "expected": expected,
                "actual": actual,
                **classification,
            }
        )
    return results


def _recall_report(ground_truth, predictions):
    report = evaluate_gt_recall(ground_truth, predictions)
    return {
        "gt_boxes": report.gt_boxes,
        "predicted_boxes": report.predicted_boxes,
        "geometric_recall": report.geometric_recall,
        "exact_text_recall": report.exact_text_recall,
        "segmentation_aware_recall": report.segmentation_aware_recall,
        "similarity_90_recall": report.similarity_90_recall,
        "mean_similarity": report.mean_similarity,
        "mean_cer": report.mean_cer,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_zip", nargs="?", default="data/sample.zip")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--dictionary", required=True)
    parser.add_argument("--recognizer-checkpoint", required=True)
    parser.add_argument("--detector-config", type=Path)
    parser.add_argument("--detector-checkpoint", type=Path)
    parser.add_argument("--runtime-python", required=True)
    parser.add_argument("--aihub-device", default="cuda:0")
    parser.add_argument("--paddle-device", default="gpu")
    parser.add_argument("--paddle-mode", choices=("fast", "accurate"), default="accurate")
    parser.add_argument("--primary", choices=("aihub", "paddle"), default="paddle")
    parser.add_argument("--fallback-min-confidence", type=float, default=0.90)
    parser.add_argument("--conflict-winner-margin", type=float, default=0.15)
    parser.add_argument("--conflict-winner-min-confidence", type=float, default=0.90)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-dir", default="analysis/hybrid_sample_e2e")
    args = parser.parse_args()

    sample_path = Path(args.sample_zip)
    if not sample_path.is_file():
        parser.error(f"sample ZIP not found: {sample_path.resolve()}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = AIHubModelPaths(
        source_root=Path(args.source_root),
        dictionary=Path(args.dictionary),
        detector_config=args.detector_config,
        detector_checkpoint=args.detector_checkpoint,
        recognizer_checkpoint=Path(args.recognizer_checkpoint),
        runtime_python=args.runtime_python,
        device=args.aihub_device,
        timeout_seconds=1200,
    )
    aihub = AIHubOCRBackend(model)
    paddle = PaddleOCRBackend(device=args.paddle_device, mode=args.paddle_mode)
    primary, fallback = (
        (aihub, paddle) if args.primary == "aihub" else (paddle, aihub)
    )
    policy = HybridPolicy(
        fallback_min_confidence=args.fallback_min_confidence,
        conflict_winner_margin=args.conflict_winner_margin,
        conflict_winner_min_confidence=args.conflict_winner_min_confidence,
    )

    documents = list(iter_target_documents(str(sample_path), paired_only=True))
    if args.limit is not None:
        documents = documents[: args.limit]
    field_counts = Counter()
    by_form = defaultdict(Counter)
    started = perf_counter()
    for position, sample in enumerate(documents, start=1):
        print(
            f"[Fintra Hybrid] [{position}/{len(documents)}] "
            f"{sample.document_type} / {sample.document_id} ...",
            flush=True,
        )
        image_bytes = read_image_bytes(str(sample_path), sample)
        document_started = perf_counter()
        primary_predictions = primary.predict_bytes(image_bytes)
        fallback_predictions = fallback.predict_bytes(image_bytes)
        hybrid = build_hybrid_document(
            sample.form_type,
            sample.document_id,
            list(primary_predictions),
            list(fallback_predictions),
            policy=policy,
        )
        primary_document = build_document_from_predictions(
            sample.form_type, sample.document_id, list(primary_predictions)
        )
        fallback_document = build_document_from_predictions(
            sample.form_type, sample.document_id, list(fallback_predictions)
        )
        ground_truth = parse_bounding_boxes(sample.label)
        oracle = build_oracle_document(
            sample.form_type,
            sample.document_id,
            list(primary_predictions + fallback_predictions),
            ground_truth,
        )
        field_results = _document_fields(
            hybrid.document, oracle, list(hybrid.predictions), sample.form_type
        )
        for item in field_results:
            field_counts[item["outcome"]] += 1
            by_form[sample.document_type][item["outcome"]] += 1
        elapsed = round(perf_counter() - document_started, 3)
        row = {
            "document_id": sample.document_id,
            "form_type": sample.form_type,
            "document_type": sample.document_type,
            "primary_backend": primary.name,
            "fallback_backend": fallback.name,
            "primary_document": primary_document.document,
            "fallback_document": fallback_document.document,
            "hybrid_document": hybrid.document,
            "hybrid_field_results": field_results,
            "gt_recall": {
                "primary": _recall_report(ground_truth, list(primary_predictions)),
                "fallback": _recall_report(ground_truth, list(fallback_predictions)),
            },
            "prediction_counts": {
                "primary": len(primary_predictions),
                "fallback": len(fallback_predictions),
                "hybrid": len(hybrid.predictions),
            },
            "elapsed_seconds": elapsed,
            "predictions": {
                "primary": _prediction_json(primary_predictions),
                "fallback": _prediction_json(fallback_predictions),
            },
        }
        (output_dir / f"{sample.document_id}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[Fintra Hybrid] done | time={elapsed:.1f}s", flush=True)

    summary = {
        "evaluation": "fintra_hybrid_sample",
        "sample_zip": str(sample_path.resolve()),
        "evaluated_documents": len(documents),
        "primary_backend": primary.name,
        "fallback_backend": fallback.name,
        "policy": asdict(policy),
        "field_outcomes": dict(field_counts),
        "by_document_type": {
            key: dict(value) for key, value in sorted(by_form.items())
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
        "note": (
            "Both backends are run once per document. Field extraction is run "
            "independently and only the final evidence arbitration is hybrid; "
            "no extractor rule or model checkpoint is changed."
        ),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
