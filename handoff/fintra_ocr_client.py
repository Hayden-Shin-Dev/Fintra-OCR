"""Standard-library-only client for the pinned FintraOCR engine.

Copy this file into the team's backend. Install the engine in a separate venv.
No values are remapped here: result is the engine's existing schema_version 2.0.
One instance serializes requests. Use one shared instance/queue per GPU.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Sequence

DOCUMENT_TYPES = {"commercial_invoice", "packing_list", "bill_of_lading"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


class FintraOCRError(RuntimeError):
    """A stage failed; inspect only local logs, not public HTTP error details."""
    def __init__(self, stage: str, job_dir: Path, reason: str) -> None:
        self.stage, self.job_dir, self.reason = stage, job_dir, reason
        super().__init__(f"FintraOCR {stage} failed ({reason}); logs: {job_dir}")


@dataclass(frozen=True)
class OCRConfig:
    model: str = "qwen3.5:4b"
    profile: str = "medium"
    device: str = "auto"
    lang: str = "en"
    max_side: int = 2400
    enhance: bool = False
    date_order: str | None = None
    decimal_separator: str | None = None
    ocr_timeout: float = 600.0
    mapping_timeout: float = 600.0

    def __post_init__(self) -> None:
        if self.profile not in {"medium", "mobile"}:
            raise ValueError("profile must be medium or mobile")
        if self.device not in {"auto", "gpu:0", "cpu"}:
            raise ValueError("device must be auto, gpu:0 or cpu")
        if self.lang not in {"en", "korean"}:
            raise ValueError("lang must be en or korean; automatic language detection is not implemented")
        if not isinstance(self.max_side, int) or isinstance(self.max_side, bool) or not 640 <= self.max_side <= 4000:
            raise ValueError("max_side must be an integer between 640 and 4000")
        if not self.model.strip() or len(self.model) > 100 or any(c in self.model for c in "\r\n\x00"):
            raise ValueError("invalid local model name")
        if self.date_order not in {None, "DMY", "MDY"}:
            raise ValueError("date_order must be DMY, MDY or None")
        if self.decimal_separator not in {None, ".", ","}:
            raise ValueError("decimal_separator must be '.', ',' or None")
        for timeout in (self.ocr_timeout, self.mapping_timeout):
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("timeouts must be positive and finite")


@dataclass(frozen=True)
class ExtractionRun:
    job_dir: Path
    ocr_path: Path
    result_path: Path | None
    result: dict[str, Any] | None
    timings: dict[str, float] = field(default_factory=dict)


class FintraOCRClient:
    def __init__(self, engine_python: str | Path = sys.executable,
                 work_root: str | Path = "fintra-ocr-jobs", config: OCRConfig | None = None) -> None:
        # Bare command names are resolved once, never interpreted by a shell.
        raw = str(engine_python)
        resolved = shutil.which(raw) if not Path(raw).is_file() else str(Path(raw).resolve())
        if resolved is None:
            raise FileNotFoundError(f"Engine Python not found: {raw}")
        self.engine_python = str(Path(resolved).resolve())
        self.work_root = Path(work_root).expanduser().resolve()
        self.config = config or OCRConfig()
        self._lock = threading.Lock()

    @staticmethod
    def _file(value: str | Path) -> Path:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    @staticmethod
    def _dtype(value: str | None) -> None:
        if value is not None and value not in DOCUMENT_TYPES:
            raise ValueError("Unsupported document_type")

    def _job(self) -> Path:
        self.work_root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="job-", dir=self.work_root))

    def _run_stage(self, stage: str, args: list[str], job: Path, timeout: float) -> float:
        import os
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        started = time.perf_counter()
        try:
            with (job / f"{stage}.log").open("w", encoding="utf-8") as log:
                done = subprocess.run(
                    [self.engine_python, "-m", "fintraocr", *args],
                    cwd=str(job), env=env, stdout=log, stderr=subprocess.STDOUT,
                    timeout=timeout, check=False, shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            if done.returncode:
                raise FintraOCRError(stage, job, f"exit_{done.returncode}")
        except subprocess.TimeoutExpired as exc:
            self._record_failure(job, stage, "timeout")
            # subprocess.run terminates its child; it cannot cancel an already
            # accepted inference inside the separate Ollama server.
            raise FintraOCRError(stage, job, "timeout") from exc
        except FintraOCRError as exc:
            self._record_failure(job, stage, exc.reason)
            raise
        except OSError as exc:
            self._record_failure(job, stage, type(exc).__name__)
            raise FintraOCRError(stage, job, type(exc).__name__) from exc
        return time.perf_counter() - started

    @staticmethod
    def _record_failure(job: Path, stage: str, reason: str) -> None:
        (job / "error.json").write_text(json.dumps({"stage": stage, "reason": reason}), encoding="utf-8")

    def _map(self, job: Path, dtype: str | None, proposal: Path | None = None) -> float:
        args = ["map", str(job / "ocr.json"), "--output", str(job / "result.json")]
        args += ["--proposal", str(proposal)] if proposal else ["--model", self.config.model]
        if dtype:
            args += ["--document-type", dtype]
        if self.config.date_order:
            args += ["--date-order", self.config.date_order]
        if self.config.decimal_separator:
            args += ["--decimal-separator", self.config.decimal_separator]
        return self._run_stage("mapping", args, job, self.config.mapping_timeout)

    def _finish(self, job: Path, timings: dict[str, float], mapped: bool) -> ExtractionRun:
        result_path = job / "result.json" if mapped else None
        result = None
        try:
            if not (job / "ocr.json").is_file():
                raise ValueError("OCR output is absent")
            if result_path:
                result = json.loads(result_path.read_text(encoding="utf-8"))
                if not isinstance(result, dict) or result.get("schema_version") != "2.0":
                    raise ValueError("Unexpected result contract")
                if not isinstance(result.get("fields"), dict) or not isinstance(result.get("items"), list):
                    raise ValueError("Missing fields/items")
        except (OSError, ValueError) as exc:
            self._record_failure(job, "output", "invalid_output")
            raise FintraOCRError("output", job, "invalid_output") from exc
        (job / "handoff-timing.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
        return ExtractionRun(job, job / "ocr.json", result_path, result, dict(timings))

    def extract(self, image_paths: Sequence[str | Path], *, document_type: str | None = None,
                ocr_only: bool = False) -> ExtractionRun:
        """One document per call; image_paths are that document's ordered pages.

        Blocking: call from a job queue/thread, not directly in an async route.
        OCR exits before mapping starts, releasing that child's GPU allocations.
        """
        self._dtype(document_type)
        if isinstance(image_paths, (str, Path)) or not image_paths:
            raise ValueError("Pass a nonempty list of page-image paths")
        paths = [self._file(path) for path in image_paths]
        if any(path.suffix.lower() not in IMAGE_SUFFIXES for path in paths):
            raise ValueError("Only page images are accepted; render PDFs before calling")
        with self._lock:
            job = self._job()
            args = ["ocr", *map(str, paths), "--output", str(job / "ocr.json"),
                    "--profile", self.config.profile, "--device", self.config.device,
                    "--lang", self.config.lang, "--max-side", str(self.config.max_side)]
            if self.config.enhance:
                args += ["--enhance"]
            started = time.perf_counter()
            timings = {"ocr_process_seconds": self._run_stage("ocr", args, job, self.config.ocr_timeout)}
            if not ocr_only:
                timings["mapping_process_seconds"] = self._map(job, document_type)
            timings["total_seconds"] = time.perf_counter() - started
            return self._finish(job, timings, not ocr_only)

    def map_saved(self, ocr_json: str | Path, *, document_type: str | None = None,
                  proposal_json: str | Path | None = None) -> ExtractionRun:
        """Reuse OCR without rerunning Paddle. proposal_json is offline replay only.

        Do not expose arbitrary proposal uploads as trusted production mappings.
        """
        self._dtype(document_type)
        source = self._file(ocr_json)
        proposal = self._file(proposal_json) if proposal_json is not None else None
        with self._lock:
            job = self._job()
            shutil.copy2(source, job / "ocr.json")
            seconds = self._map(job, document_type, proposal)
            return self._finish(job, {"mapping_process_seconds": seconds, "ocr_reused": 1.0}, True)
