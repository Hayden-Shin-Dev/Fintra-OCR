"""Subprocess adapter for the official AI-Hub logistics OCR models.

The AI-Hub package targets an old Python/PyTorch/MMOCR stack.  Keeping that
stack in a subprocess protects the production PaddleOCR environment while
still exposing the same ``OCRBackend`` protocol to Fintra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from .prediction_parser import OCRPrediction


class AIHubRuntimeError(RuntimeError):
    """A classified failure from the isolated AI-Hub runtime."""

    def __init__(self, message: str, *, category: str = "runtime") -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class AIHubModelPaths:
    """External paths for one official AI-Hub domain model package."""

    source_root: Path
    dictionary: Path
    detector_config: Path | None = None
    detector_checkpoint: Path | None = None
    recognizer_checkpoint: Path | None = None
    runtime_python: Path | str = sys.executable
    worker: Path | None = None
    device: str = "cpu"
    timeout_seconds: int = 900

    def resolved(self) -> "AIHubModelPaths":
        root = Path(self.source_root)
        worker = self.worker or (
            Path(__file__).resolve().parents[2] / "scripts" / "aihub_inference_worker.py"
        )
        return AIHubModelPaths(
            source_root=root,
            dictionary=Path(self.dictionary),
            detector_config=self.detector_config or root / "configs" / "transit_config.py",
            detector_checkpoint=self.detector_checkpoint or root / "transit_detection_model.pth",
            recognizer_checkpoint=self.recognizer_checkpoint or root / "transit_recog_model.pth",
            runtime_python=self.runtime_python,
            worker=Path(worker),
            device=self.device,
            timeout_seconds=self.timeout_seconds,
        )

    def validate(self) -> "AIHubModelPaths":
        paths = self.resolved()
        required = {
            "source_root": paths.source_root,
            "dictionary": paths.dictionary,
            "detector_config": paths.detector_config,
            "detector_checkpoint": paths.detector_checkpoint,
            "recognizer_checkpoint": paths.recognizer_checkpoint,
            "worker": paths.worker,
        }
        missing = [f"{name}={path}" for name, path in required.items() if not path.exists()]
        if missing:
            raise AIHubRuntimeError(
                "AI-Hub model package is incomplete; missing " + ", ".join(missing),
                category="missing_model_asset",
            )
        if paths.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        return paths


def _classify_failure(message: str) -> str:
    lowered = message.casefold()
    if "no module named" in lowered or "modulenotfounderror" in lowered:
        return "missing_dependency"
    if "cuda" in lowered or "cudnn" in lowered or "cuda_home" in lowered:
        return "cuda_compatibility"
    if "mmcv" in lowered or "mmocr" in lowered or "mmdet" in lowered:
        return "mmocr_mmcv_compatibility"
    if "size mismatch" in lowered or "missing key" in lowered or "unexpected key" in lowered:
        return "checkpoint_incompatibility"
    if "syntaxerror" in lowered or "python" in lowered and "version" in lowered:
        return "python_compatibility"
    return "runtime"


def _axis_box(points: Any) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if not isinstance(points, list) or len(points) < 4:
        raise ValueError("AI-Hub prediction bbox must contain at least four points")
    try:
        if points and not isinstance(points[0], (list, tuple)):
            if len(points) % 2:
                raise ValueError("flat polygon must contain pairs of coordinates")
            paired = list(zip(points[::2], points[1::2]))
        else:
            paired = points
        xs = [int(round(float(point[0]))) for point in paired]
        ys = [int(round(float(point[1]))) for point in paired]
    except (TypeError, ValueError, IndexError) as error:
        raise ValueError("AI-Hub prediction bbox contains invalid coordinates") from error
    return (min(xs), max(xs), max(xs), min(xs)), (min(ys), min(ys), max(ys), max(ys))


def _parse_worker_output(path: Path) -> list[OCRPrediction]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AIHubRuntimeError(f"AI-Hub worker output is not valid JSON: {path}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("predictions"), list):
        raise AIHubRuntimeError("AI-Hub worker output must contain a predictions list")

    predictions: list[OCRPrediction] = []
    for index, item in enumerate(payload["predictions"]):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise AIHubRuntimeError(f"AI-Hub prediction {index} has invalid text")
        score = item.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise AIHubRuntimeError(
                f"AI-Hub prediction {index} has no numeric recognizer confidence"
            )
        x, y = _axis_box(item.get("bbox"))
        predictions.append(OCRPrediction(item["text"], x, y, float(score)))
    return predictions


@dataclass
class AIHubOCRBackend:
    """Run official logistics AI-Hub OCR in an isolated Python subprocess."""

    model: AIHubModelPaths
    score_threshold: float = 0.2
    name: str = field(default="aihub-logistics", init=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score_threshold <= 1.0:
            raise ValueError("score_threshold must be between 0 and 1")

    def predict_bytes(self, image_bytes: bytes) -> list[OCRPrediction]:
        if not image_bytes:
            raise ValueError("image_bytes must not be empty")
        paths = self.model.validate()
        runtime_python = str(paths.runtime_python)
        with tempfile.TemporaryDirectory(prefix="fintra-aihub-") as temp_dir:
            temp = Path(temp_dir)
            image_path = temp / "input.png"
            output_path = temp / "result.json"
            image_path.write_bytes(image_bytes)
            command = [
                runtime_python,
                str(paths.worker),
                "--source-root",
                str(paths.source_root),
                "--detector-config",
                str(paths.detector_config),
                "--detector-checkpoint",
                str(paths.detector_checkpoint),
                "--recognizer-checkpoint",
                str(paths.recognizer_checkpoint),
                "--dictionary",
                str(paths.dictionary),
                "--image",
                str(image_path),
                "--output",
                str(output_path),
                "--device",
                paths.device,
                "--score-threshold",
                str(self.score_threshold),
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=paths.timeout_seconds,
                    check=False,
                )
            except FileNotFoundError as error:
                raise AIHubRuntimeError(
                    f"AI-Hub runtime Python was not found: {runtime_python}",
                    category="python_compatibility",
                ) from error
            except subprocess.TimeoutExpired as error:
                raise AIHubRuntimeError(
                    f"AI-Hub inference exceeded {paths.timeout_seconds}s",
                    category="runtime_timeout",
                ) from error

            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                category = _classify_failure(detail)
                raise AIHubRuntimeError(
                    f"AI-Hub worker failed ({category}): {detail[-4000:]}",
                    category=category,
                )
            return _parse_worker_output(output_path)
