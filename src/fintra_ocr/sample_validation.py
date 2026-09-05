"""End-to-end validation on the lightweight Fintra sample ZIP."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from .e2e_pipeline import run_document
from .gt_recall import evaluate_gt_recall
from .label_bbox import parse_bounding_boxes
from .ocr_backends import OCRBackend
from .oracle_validation import build_oracle_document, compare_actual_to_oracle
from .sample_dataset import audit_sample_zip, iter_target_documents, read_image_bytes


def _field_summary(document: dict[str, Any]) -> dict[str, object]:
    fields = document.get("fields", {})
    result: dict[str, object] = {}
    for name, field in fields.items():
        result[name] = {
            "status": field["status"],
            "value": field["value"],
            "normalized": field["normalized"],
            "confidence": field["confidence"],
        }
    return result



def _prediction_summary(predictions: object) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for index, item in enumerate(predictions):  # type: ignore[union-attr]
        output.append({
            "index": index,
            "text": item.text,
            "confidence": item.score,
            "bbox": [
                [min(item.x), min(item.y)],
                [max(item.x), min(item.y)],
                [max(item.x), max(item.y)],
                [min(item.x), max(item.y)],
            ],
        })
    return output


def _field_quality(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    quality: dict[str, dict[str, object]] = {}
    names = sorted({name for row in rows for name in row["fields"]})  # type: ignore[index]
    excluded_classes = {
        "both_missing_or_oracle_unavailable",
        "oracle_unavailable_for_found_value",
        "oracle_semantically_invalid",
    }
    for name in names:
        relevant = [row for row in rows if name in row["fields"]]  # type: ignore[operator]
        statuses: dict[str, int] = {}
        classes: dict[str, int] = {}
        agreement_scores: list[float] = []
        evaluable_scores: list[float] = []
        evaluable = 0
        for row in relevant:
            field = row["fields"][name]  # type: ignore[index]
            status = str(field["status"])
            statuses[status] = statuses.get(status, 0) + 1
            diagnostic = row["field_diagnostics"][name]  # type: ignore[index]
            classification = str(diagnostic["classification"])
            classes[classification] = classes.get(classification, 0) + 1
            score = float(diagnostic.get("agreement_score", 0.0))
            agreement_scores.append(score)
            if classification not in excluded_classes:
                evaluable += 1
                evaluable_scores.append(score)
        total = len(relevant)
        matches = classes.get("e2e_matches_oracle", 0)
        covered = sum(count for status, count in statuses.items() if status in {"found", "ambiguous"})
        quality[name] = {
            "documents": total,
            "evaluable_documents": evaluable,
            "status_counts": statuses,
            "diagnostic_counts": classes,
            "coverage_rate": covered / total if total else 0.0,
            "oracle_agreement_rate": matches / evaluable if evaluable else None,
            "mean_agreement_score": mean(evaluable_scores) if evaluable_scores else None,
            "note": "oracle agreement excludes unavailable/semantically-invalid oracle cases; coverage is not accuracy",
        }
    return quality


def validate_sample(
    sample_zip: str,
    backend: OCRBackend,
    *,
    output_dir: str | Path,
    limit: int | None = None,
) -> dict[str, object]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    documents = list(iter_target_documents(sample_zip, paired_only=True))
    if limit is not None:
        documents = documents[:limit]

    rows: list[dict[str, object]] = []
    run_started = perf_counter()
    total = len(documents)
    print(f"[Fintra OCR] {total} paired target documents selected")
    print(f"[Fintra OCR] results -> {output_dir.resolve()}")
    for position, sample in enumerate(documents, start=1):
        print(f"[Fintra OCR] [{position}/{total}] {sample.document_type} / {sample.document_id} ...", flush=True)
        document_started = perf_counter()
        image_bytes = read_image_bytes(sample_zip, sample)
        pipeline = run_document(
            image_bytes,
            sample.form_type,
            sample.document_id,
            backend,
        )
        gt = parse_bounding_boxes(sample.label)
        recall = evaluate_gt_recall(gt, list(pipeline.predictions))
        oracle_document = build_oracle_document(
            sample.form_type, sample.document_id, list(pipeline.predictions), gt
        )
        diagnostics = compare_actual_to_oracle(pipeline.document, oracle_document)
        row = {
            "document_id": sample.document_id,
            "form_type": sample.form_type,
            "document_type": sample.document_type,
            "backend": backend.name,
            "gt_recall": {
                "gt_boxes": recall.gt_boxes,
                "predicted_boxes": recall.predicted_boxes,
                "geometric_recall": recall.geometric_recall,
                "exact_text_recall": recall.exact_text_recall,
                "segmentation_aware_recall": recall.segmentation_aware_recall,
                "similarity_90_recall": recall.similarity_90_recall,
                "mean_similarity": recall.mean_similarity,
                "mean_cer": recall.mean_cer,
            },
            "fields": _field_summary(dict(pipeline.document)),
            "oracle_fields": _field_summary(dict(oracle_document)),
            "field_diagnostics": {
                name: asdict(diagnostic) for name, diagnostic in diagnostics.items()
            },
            "ocr_predictions": _prediction_summary(pipeline.predictions),
            "elapsed_seconds": round(perf_counter() - document_started, 3),
            "common_json": pipeline.document,
        }
        rows.append(row)
        result_path = output_dir / f"{sample.document_id}.json"
        result_path.write_text(
            json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"[Fintra OCR] [{position}/{total}] done | "
            f"GT strict={recall.exact_text_recall:.3f} "
            f"seg-aware={recall.segmentation_aware_recall:.3f} "
            f"time={perf_counter() - document_started:.1f}s | saved={result_path}",
            flush=True,
        )

    by_form: dict[str, dict[str, object]] = {}
    for form_type in sorted({row["form_type"] for row in rows}):
        subset = [row for row in rows if row["form_type"] == form_type]
        by_form[str(form_type)] = {
            "documents": len(subset),
            "exact_text_recall": mean(float(row["gt_recall"]["exact_text_recall"]) for row in subset),
            "segmentation_aware_recall": mean(float(row["gt_recall"]["segmentation_aware_recall"]) for row in subset),
            "similarity_90_recall": mean(float(row["gt_recall"]["similarity_90_recall"]) for row in subset),
            "mean_cer": mean(float(row["gt_recall"]["mean_cer"]) for row in subset),
        }
    field_diagnostics: dict[str, dict[str, int]] = {}
    for row in rows:
        for field_name, diagnostic in row["field_diagnostics"].items():
            counts = field_diagnostics.setdefault(field_name, {})
            classification = diagnostic["classification"]
            counts[classification] = counts.get(classification, 0) + 1

    summary = {
        "dataset": audit_sample_zip(sample_zip),
        "backend": backend.name,
        "evaluated_documents": len(rows),
        "elapsed_seconds": round(perf_counter() - run_started, 3),
        "metric_note": (
            "GT JSON is incomplete for static form captions; prediction precision against all GT boxes is intentionally not reported. "
            "exact_text_recall is strict per-GT-box equality. segmentation_aware_recall also accepts the GT value when it is contained in a nearby OCR group, "
            "which is more tolerant of OCR box splitting/merging. Neither metric is a semantic field-accuracy score."
        ),
        "by_form": by_form,
        "field_diagnostics": field_diagnostics,
        "field_quality": _field_quality(rows),
        "documents": rows,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[Fintra OCR] complete | summary={summary_path.resolve()}", flush=True)
    return summary
