"""Application-facing OCR adapter types.

The adapter does not implement OCR. It consumes the validated Modern runtime
output or an explicitly configured external command and always preserves the
raw output path/content for audit traceability.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class OCRRegion:
    polygon: list[list[float]]
    text: str
    confidence: float | None = None
    page: int = 1
    index: int = 0

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs = [point[0] for point in self.polygon]
        ys = [point[1] for point in self.polygon]
        return min(xs), min(ys), max(xs), max(ys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "polygon": self.polygon,
            "text": self.text,
            "confidence": self.confidence,
            "page": self.page,
        }


@dataclass(frozen=True)
class OCRResult:
    document_id: str
    document_type: str
    source_file: str
    regions: list[OCRRegion]
    raw_output: str | None = None
    raw_output_path: str | None = None
    runtime: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "source_file": self.source_file,
            "regions": [region.to_dict() for region in self.regions],
            "raw_output": self.raw_output,
            "raw_output_path": self.raw_output_path,
            "runtime": self.runtime,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, path: Path, document_type: str | None = None) -> "OCRResult":
        payload = json.loads(path.read_text(encoding="utf-8"))
        regions_payload = payload.get("regions") or payload.get("predictions")
        if regions_payload is None and payload.get("documents"):
            regions_payload = payload["documents"][0].get("predictions", [])
        if regions_payload is None:
            regions_payload = payload.get("candidates", [])
        regions = []
        for index, item in enumerate(regions_payload):
            polygon = item.get("polygon") or item.get("bbox") or item.get("boundary")
            if polygon and isinstance(polygon[0], (int, float)):
                polygon = [[polygon[i], polygon[i + 1]] for i in range(0, len(polygon), 2)]
            regions.append(
                OCRRegion(
                    polygon=[[float(x), float(y)] for x, y in polygon],
                    text=str(item.get("text", item.get("data", ""))),
                    confidence=item.get("confidence", item.get("score")),
                    page=int(item.get("page", 1)),
                    index=index,
                )
            )
        metadata = dict(payload.get("metadata", {}))
        return cls(
            document_id=str(payload.get("document_id", path.stem)),
            document_type=document_type or str(payload.get("document_type", "Unknown")),
            source_file=str(payload.get("source_file", "")),
            regions=regions,
            raw_output=path.read_text(encoding="utf-8"),
            raw_output_path=str(path),
            runtime=str(metadata.get("runtime", payload.get("runtime", "fixture"))),
            metadata=metadata,
        )

    @classmethod
    def from_official_txt(
        cls,
        path: Path,
        document_id: str,
        document_type: str,
        source_file: str,
    ) -> "OCRResult":
        regions = []
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            parts = line.split(",", 8)
            if len(parts) != 9:
                raise ValueError(f"{path}:{index + 1}: expected official 8-coordinate TXT")
            coordinates = [float(value) for value in parts[:8]]
            regions.append(
                OCRRegion(
                    polygon=[[coordinates[i], coordinates[i + 1]] for i in range(0, 8, 2)],
                    text=parts[8],
                    index=len(regions),
                )
            )
        return cls(
            document_id=document_id,
            document_type=document_type,
            source_file=source_file,
            regions=regions,
            raw_output=path.read_text(encoding="utf-8"),
            raw_output_path=str(path),
            runtime="aihub-official-txt",
        )


class OCRAdapter(Protocol):
    def run_ocr(self, document_path: Path, document_type: str) -> OCRResult:
        ...


class FixtureOCRAdapter:
    """Read an explicitly supplied structured OCR fixture."""

    def __init__(self, fixture_dir: Path):
        self.fixture_dir = fixture_dir

    def run_ocr(self, document_path: Path, document_type: str) -> OCRResult:
        path = self.fixture_dir / f"{document_path.stem}.json"
        if not path.is_file():
            raise FileNotFoundError(f"OCR fixture not found: {path}")
        return OCRResult.from_json(path, document_type=document_type)


class CommandOCRAdapter:
    """Invoke a configured OCR command without guessing a Docker interface.

    The command template must explicitly contain `{document_path}`,
    `{document_type}`, and `{output_json}`. This prevents application code from
    silently selecting a different model or preprocessing pipeline.
    """

    def __init__(self, command_template: str, work_dir: Path | None = None):
        self.command_template = command_template
        self.work_dir = work_dir

    def run_ocr(self, document_path: Path, document_type: str) -> OCRResult:
        output_json = document_path.with_suffix(".fintra-ocr.json")
        command = self.command_template.format(
            document_path=str(document_path),
            document_type=document_type,
            output_json=str(output_json),
        )
        completed = subprocess.run(
            shlex.split(command, posix=False),
            cwd=self.work_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise RuntimeError(
                f"OCR command failed ({completed.returncode}): {completed.stderr[-2000:]}"
            )
        if not output_json.is_file():
            raise RuntimeError(f"OCR command did not create {output_json}")
        result = OCRResult.from_json(output_json, document_type=document_type)
        return OCRResult(
            document_id=result.document_id,
            document_type=result.document_type,
            source_file=str(document_path),
            regions=result.regions,
            raw_output=result.raw_output,
            raw_output_path=result.raw_output_path,
            runtime="configured-command",
            metadata={**result.metadata, "stdout_tail": completed.stdout[-1000:]},
        )
