"""Audit AI-Hub OCR failures and compare recognizer crop preprocessing variants.

This script intentionally consumes stored detector predictions from the real
AI-Hub run. It does not change detector/recognizer checkpoints or field
extraction code. The detector boxes are reused so padding experiments isolate
crop/recognizer preprocessing from detector stochasticity.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fintra_ocr.field_evaluation import _classify_field, _prediction_list, evaluate_prediction_rows, load_prediction_rows
from fintra_ocr.sample_dataset import iter_target_documents, read_image_bytes
from fintra_ocr.prediction_parser import OCRPrediction


PADDINGS = (0.0, 0.02, 0.05, 0.08, 0.10)


def _bounds(box: object) -> tuple[float, float, float, float]:
    points = box  # type: ignore[assignment]
    return (
        min(float(point[0]) for point in points),
        min(float(point[1]) for point in points),
        max(float(point[0]) for point in points),
        max(float(point[1]) for point in points),
    )


def _box(box: object) -> list[list[int]]:
    x1, y1, x2, y2 = _bounds(box)
    return [[round(x1), round(y1)], [round(x2), round(y1)], [round(x2), round(y2)], [round(x1), round(y2)]]


def _overlap(first: object, second: object) -> tuple[float, float, float]:
    ax1, ay1, ax2, ay2 = _bounds(first)
    bx1, by1, bx2, by2 = _bounds(second)
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    area_a = max(1.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1.0, (bx2 - bx1) * (by2 - by1))
    union = max(1.0, area_a + area_b - intersection)
    return intersection / area_a, intersection / area_b, intersection / union


def _crop_bounds(box: object, image_shape: tuple[int, ...], padding: float) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = _bounds(box)
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    left = max(0, math.floor(x1 - width * padding))
    top = max(0, math.floor(y1 - height * padding))
    right = min(int(image_shape[1]), math.ceil(x2 + width * padding) + 1)
    bottom = min(int(image_shape[0]), math.ceil(y2 + height * padding) + 1)
    return left, top, right, bottom


def _contains(crop: tuple[int, int, int, int], box: object) -> bool:
    left, top, right, bottom = crop
    x1, y1, x2, y2 = _bounds(box)
    return left <= x1 and top <= y1 and right >= x2 and bottom >= y2


def _load_failures(path: Path) -> list[dict[str, object]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    return [item for item in report["failures"] if item["failure_classification"] == "OCR_MISSING"]


def audit_failures(rows: list[dict[str, object]], failures: list[dict[str, object]], output_root: Path, sample_zip: Path) -> dict[str, object]:
    import cv2
    import numpy as np

    row_by_id = {str(row["document_id"]): row for row in rows}
    samples = {sample.document_id: sample for sample in iter_target_documents(str(sample_zip), paired_only=True)}
    audits: list[dict[str, object]] = []
    for failure in failures:
        document_id = str(failure["document_id"])
        row = row_by_id[document_id]
        expected_box = failure.get("oracle_expected_bbox")
        predictions = row["ocr_predictions"]
        detector_candidates = []
        for index, prediction in enumerate(predictions):  # type: ignore[union-attr]
            coverage, inverse, iou = _overlap(expected_box, prediction["bbox"])
            if iou > 0.0:
                detector_candidates.append({
                    "index": index,
                    "text": prediction["text"],
                    "bbox": prediction["bbox"],
                    "score": prediction["confidence"],
                    "gt_coverage": coverage,
                    "detector_coverage": inverse,
                    "iou": iou,
                })
        detector_candidates.sort(key=lambda item: (float(item["iou"]), float(item["gt_coverage"])), reverse=True)
        image = cv2.imdecode(np.frombuffer(read_image_bytes(str(sample_zip), samples[document_id]), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"Unable to decode sample image {document_id}")
        if not detector_candidates:
            classification = "DETECTION_MISSING"
            crop_info = None
        else:
            best = detector_candidates[0]
            baseline_crop = _crop_bounds(best["bbox"], image.shape, 0.0)
            # GT value boxes can contain vertical whitespace and, for
            # multi-line quantity values, several independent text instances.
            # A single detector box that lies almost completely inside the GT
            # box is therefore considered full text coverage even when the GT
            # annotation rectangle is slightly larger than the glyph box.
            # Conversely, a low GT coverage with multiple independent boxes is
            # a genuinely partial detector segmentation (e.g. vertical 1/4/3).
            if (
                float(best["detector_coverage"]) < 0.90
                or (float(best["gt_coverage"]) < 0.20 and len(detector_candidates) > 1)
            ):
                classification = "DETECTION_PARTIAL"
            else:
                # The baseline crop is constructed directly from the detector
                # box and the saved image crops are inspected separately. A
                # geometric GT-box non-containment caused only by annotation
                # margin is not called a crop problem.
                classification = "RECOGNITION_ERROR"
            crop_dir = output_root / f"{document_id}__{failure['field']}"
            crop_dir.mkdir(parents=True, exist_ok=True)
            gt_crop = _crop_bounds(expected_box, image.shape, 0.0)
            cv2.imwrite(str(crop_dir / "gt_region.png"), image[gt_crop[1]:gt_crop[3], gt_crop[0]:gt_crop[2]])
            for padding in PADDINGS:
                crop = _crop_bounds(best["bbox"], image.shape, padding)
                cv2.imwrite(str(crop_dir / f"detector_crop_{int(padding * 100):02d}pct.png"), image[crop[1]:crop[3], crop[0]:crop[2]])
            crop_info = {
                "detector_crop_bounds_0pct": list(baseline_crop),
                "detector_crop_contains_gt_0pct": _contains(baseline_crop, expected_box),
                "gt_region_bounds": list(gt_crop),
                "crop_artifacts": str(crop_dir),
            }
        audits.append({
            "document_id": document_id,
            "document_type": failure["document_type"],
            "field": failure["field"],
            "expected": failure["oracle_expected_value"],
            "expected_bbox": expected_box,
            "baseline_extractor_output": failure["extractor_output"],
            "detector_box_count_overlapping_gt": len(detector_candidates),
            "detector_candidates": detector_candidates[:5],
            "classification": classification,
            "crop_evidence": crop_info,
            "evidence_note": "Detector evidence is the stored raw AI-Hub threshold-0.20 prediction bbox. Crop visibility is geometric GT-region inclusion; image crops are saved for visual inspection.",
        })
    counts = Counter(str(item["classification"]) for item in audits)
    return {"failure_count": len(audits), "classification_counts": dict(counts), "failures": audits}


def _recognize(crop_root: Path, source_root: Path, checkpoint: Path, dictionary: Path, batch_size: int) -> dict[int, tuple[str, float]]:
    import torch
    import torch.nn.functional as functional
    from dataset import AlignCollate, RawDataset
    from eval_utils import TokenLabelConverter
    from model import Model
    from aihub_inference_worker import _options

    option = _options(dictionary, checkpoint, batch_size)
    converter = TokenLabelConverter(option)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.nn.DataParallel(Model(option)).to(device)
    model.load_state_dict(torch.load(str(checkpoint), map_location=device))
    model.eval()
    dataset = RawDataset(root=str(crop_root), opt=option)
    loader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=False, num_workers=0,
        collate_fn=AlignCollate(imgH=option.imgH, imgW=option.imgW, keep_ratio_with_pad=option.PAD, opt=option),
        pin_memory=False,
    )
    output: dict[int, tuple[str, float]] = {}
    with torch.no_grad():
        for tensors, image_paths in loader:
            tensors = tensors.to(device)
            count = tensors.size(0)
            lengths = torch.IntTensor([option.batch_max_length] * count).to(device)
            text = torch.LongTensor(count, option.batch_max_length + 1).fill_(0).to(device)
            logits = model(tensors, text, is_train=False)
            _, indices = logits.max(2)
            decoded = converter.decode(indices[:, 1:], lengths)
            probabilities = functional.softmax(logits, dim=2).max(dim=2).values[:, 1:]
            for raw_text, token_probabilities, image_path in zip(decoded, probabilities, image_paths):
                eos = raw_text.find("[s]")
                value = raw_text if eos < 0 else raw_text[:eos]
                value = value.strip("\n\t")
                token_count = len(value)
                confidence = math.exp(float(torch.log(token_probabilities[:token_count].clamp_min(1e-12)).mean())) if token_count else 0.0
                output[int(Path(image_path).stem)] = (value, confidence)
    return output


def run_variants(rows: list[dict[str, object]], baseline_report: Path, paddle_report: Path, failures: list[dict[str, object]], sample_zip: Path, source_root: Path, checkpoint: Path, dictionary: Path, output_root: Path, batch_size: int, device_name: str) -> dict[str, object]:
    import cv2
    import numpy as np

    baseline_aihub = json.loads(baseline_report.read_text(encoding="utf-8"))
    baseline_paddle = json.loads(paddle_report.read_text(encoding="utf-8"))
    ai_items = {(str(item["document_id"]), str(item["field_name"])): item for item in baseline_aihub["field_results"]}
    paddle_items = {(str(item["document_id"]), str(item["field_name"])): item for item in baseline_paddle["field_results"]}
    comparable = {key for key, item in ai_items.items() if item["oracle_proxy"] and key in paddle_items and paddle_items[key]["oracle_proxy"]}
    failure_keys = {(str(item["document_id"]), str(item["field"])) for item in failures}
    correct_keys = {key for key in comparable if ai_items[key]["improved"]["outcome"] == "correct"}
    samples = {sample.document_id: sample for sample in iter_target_documents(str(sample_zip), paired_only=True)}
    rows_by_id = {str(row["document_id"]): row for row in rows}
    variants = [(f"padding_{int(padding * 100):02d}pct_stretch", padding, False) for padding in PADDINGS]
    variants.append(("padding_05pct_keep_ratio_pad", 0.05, True))
    results: list[dict[str, object]] = []
    for name, padding, keep_ratio_pad in variants:
        started = time.perf_counter()
        variant_rows: list[dict[str, object]] = []
        mapping: dict[int, tuple[str, int]] = {}
        with tempfile.TemporaryDirectory(prefix=f"fintra-aihub-{name}-") as temp:
            crop_root = Path(temp)
            serial = 0
            for row in sorted(rows, key=lambda item: str(item["document_id"])):
                image = cv2.imdecode(np.frombuffer(read_image_bytes(str(sample_zip), samples[str(row["document_id"])]), dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is None:
                    raise RuntimeError(f"Unable to decode {row['document_id']}")
                for prediction_index, prediction in enumerate(row["ocr_predictions"]):  # type: ignore[union-attr]
                    serial += 1
                    crop = _crop_bounds(prediction["bbox"], image.shape, padding)
                    path = crop_root / f"{serial:08d}.png"
                    if not cv2.imwrite(str(path), image[crop[1]:crop[3], crop[0]:crop[2]]):
                        raise RuntimeError(f"Unable to write crop {path}")
                    mapping[serial] = (str(row["document_id"]), prediction_index)
            # Keep the official model transform; only the optional PAD mode is varied.
            sys.path.insert(0, str(source_root / "text_recognition_baseline"))
            from aihub_inference_worker import _options
            import torch
            texts = _recognize_variant(crop_root, source_root, checkpoint, dictionary, batch_size, keep_ratio_pad, device_name)
            predictions_by_doc: dict[str, list[dict[str, object]]] = {str(row["document_id"]): [] for row in rows}
            for serial_number, (document_id, prediction_index) in mapping.items():
                raw = rows_by_id[document_id]["ocr_predictions"][prediction_index]  # type: ignore[index]
                text, score = texts[serial_number]
                predictions_by_doc[document_id].append({"text": text, "confidence": score, "bbox": raw["bbox"]})  # type: ignore[index]
            for row in rows:
                variant_row = dict(row)
                variant_row["ocr_predictions"] = predictions_by_doc[str(row["document_id"])]
                variant_rows.append(variant_row)
        evaluated = evaluate_prediction_rows(variant_rows)
        current = {(str(item["document_id"]), str(item["field_name"])): item for item in evaluated["field_results"]}
        selected = [current[key] for key in sorted(comparable)]
        outcomes = Counter(str(item["improved"]["outcome"]) for item in selected)
        recovered = sum(1 for key in failure_keys if key in current and current[key]["improved"]["outcome"] == "correct")
        regressions = [
            {"document_id": key[0], "field": key[1], "before": ai_items[key]["improved"], "after": current.get(key, {}).get("improved")}
            for key in sorted(correct_keys)
            if key in current and current[key]["improved"]["outcome"] != "correct"
        ]
        results.append({
            "configuration": name,
            "padding_fraction": padding,
            "resize": "keep_ratio_right_border_pad" if keep_ratio_pad else "official_stretch_224x224",
            "comparable_field_count": len(selected),
            "outcomes": dict(outcomes),
            "ocr_missing_baseline_count": len(failure_keys),
            "ocr_missing_recovered_count": recovered,
            "correct_field_regression_count": len(regressions),
            "correct_field_regressions": regressions,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        })
    return {"configurations": results, "note": "Each variant reuses the stored raw AI-Hub detector bbox and reruns only recognizer crop/transform. Field outcomes use the existing evaluator and fixed 46-field AI-Hub/Paddle intersection."}


def _recognize_variant(crop_root: Path, source_root: Path, checkpoint: Path, dictionary: Path, batch_size: int, keep_ratio_pad: bool, device_name: str) -> dict[int, tuple[str, float]]:
    """Official recognizer loop with only AlignCollate PAD toggled."""
    from aihub_inference_worker import _install_import_shims
    _install_import_shims()
    import torch
    from itertools import accumulate
    torch._utils._accumulate = accumulate
    import torch.nn.functional as functional
    from dataset import AlignCollate, RawDataset
    from eval_utils import TokenLabelConverter
    from model import Model
    from aihub_inference_worker import _options

    option = _options(dictionary, checkpoint, batch_size)
    option.PAD = keep_ratio_pad
    converter = TokenLabelConverter(option)
    device = torch.device(device_name)
    model = torch.nn.DataParallel(Model(option)).to(device)
    model.load_state_dict(torch.load(str(checkpoint), map_location=device))
    model.eval()
    loader = torch.utils.data.DataLoader(
        RawDataset(root=str(crop_root), opt=option), batch_size=batch_size, shuffle=False,
        num_workers=0,
        collate_fn=AlignCollate(imgH=option.imgH, imgW=option.imgW, keep_ratio_with_pad=option.PAD, opt=option),
        pin_memory=device.type == "cuda",
    )
    output: dict[int, tuple[str, float]] = {}
    with torch.no_grad():
        for tensors, image_paths in loader:
            tensors = tensors.to(device)
            count = tensors.size(0)
            lengths = torch.IntTensor([option.batch_max_length] * count).to(device)
            text = torch.LongTensor(count, option.batch_max_length + 1).fill_(0).to(device)
            logits = model(tensors, text, is_train=False)
            _, indices = logits.max(2)
            decoded = converter.decode(indices[:, 1:], lengths)
            probabilities = functional.softmax(logits, dim=2).max(dim=2).values[:, 1:]
            for raw_text, token_probabilities, image_path in zip(decoded, probabilities, image_paths):
                eos = raw_text.find("[s]")
                value = (raw_text if eos < 0 else raw_text[:eos]).strip("\n\t")
                token_count = len(value)
                score = math.exp(float(torch.log(token_probabilities[:token_count].clamp_min(1e-12)).mean())) if token_count else 0.0
                output[int(Path(image_path).stem)] = (value, score)
    return output


def _validate_device(requested: str) -> dict[str, object]:
    import torch

    if requested != "cpu" and not requested.startswith("cuda"):
        raise ValueError("--device must be 'cpu', 'cuda', or 'cuda:N'")
    cuda_available = bool(torch.cuda.is_available())
    if requested.startswith("cuda"):
        if not cuda_available:
            raise RuntimeError(
                f"CUDA was requested with --device {requested}, but this Python environment has no CUDA-enabled PyTorch."
            )
        device = torch.device(requested)
        if device.index is not None and device.index >= torch.cuda.device_count():
            raise RuntimeError(
                f"Requested {requested}, but only {torch.cuda.device_count()} CUDA device(s) are available."
            )
        torch.cuda.set_device(device)
        actual = str(torch.cuda.current_device())
        gpu_name = torch.cuda.get_device_name(torch.cuda.current_device())
        info = {
            "requested_device": requested,
            "device": f"cuda:{actual}",
            "cuda_available": cuda_available,
            "cuda_device_count": torch.cuda.device_count(),
            "gpu_name": gpu_name,
        }
    else:
        info = {
            "requested_device": requested,
            "device": "cpu",
            "cuda_available": cuda_available,
            "cuda_device_count": torch.cuda.device_count(),
            "gpu_name": None,
        }
    print(json.dumps({"runtime": info}, ensure_ascii=False), flush=True)
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--failure-report", required=True)
    parser.add_argument("--sample-zip", required=True)
    parser.add_argument("--baseline-aihub", required=True)
    parser.add_argument("--baseline-paddle", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--recognizer-checkpoint", required=True)
    parser.add_argument("--dictionary", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", default="cuda", help="cuda or cuda:N is strict; cpu is explicit CPU mode")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    device_info = _validate_device(args.device)
    rows = load_prediction_rows(args.input_dir)
    failures = _load_failures(Path(args.failure_report))
    audit_dir = Path(args.audit_dir)
    audit = audit_failures(rows, failures, audit_dir, Path(args.sample_zip))
    variants = {"configurations": [], "note": "variant execution skipped by --audit-only"}
    if not args.audit_only:
        variants = run_variants(rows, Path(args.baseline_aihub), Path(args.baseline_paddle), failures, Path(args.sample_zip), Path(args.source_root), Path(args.recognizer_checkpoint), Path(args.dictionary), audit_dir, args.batch_size, str(device_info["device"]))
    report = {
        "evaluation": "aihub_preprocessing_failure_decomposition",
        "baseline": "stored AI-Hub threshold-0.20 detector boxes and official PAD=False recognizer result",
        "audit": audit,
        "variant_evaluation": variants,
        "models_changed": False,
        "field_extractor_changed": False,
        "runtime": {**device_info, "batch_size": args.batch_size},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"audit": audit["classification_counts"], "variants": len(variants["configurations"]), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
