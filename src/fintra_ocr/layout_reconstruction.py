"""Document-scale layout reconstruction for noisy OCR predictions.

The detector output remains the source of truth.  This module only builds a
derived representation used by field extraction: tokens are assigned to
reading-order lines using relative geometry and each line keeps the original
prediction indices for auditability.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median

from .prediction_parser import OCRPrediction


@dataclass(frozen=True)
class LayoutToken:
    """Geometry for one prediction, retaining its raw prediction index."""

    index: int
    text: str
    left: int
    top: int
    right: int
    bottom: int
    confidence: float

    @property
    def width(self) -> int:
        return max(1, self.right - self.left)

    @property
    def height(self) -> int:
        return max(1, self.bottom - self.top)

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2


@dataclass(frozen=True)
class ReconstructedLine:
    """One horizontal reading-order line made from raw prediction indices."""

    indices: tuple[int, ...]
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float


@dataclass(frozen=True)
class ReconstructedLayout:
    """Derived layout with scale statistics and line-level spans."""

    tokens: tuple[LayoutToken, ...]
    lines: tuple[ReconstructedLine, ...]
    median_height: float
    median_width: float

    @property
    def index_to_line(self) -> dict[int, int]:
        return {
            index: line_no
            for line_no, line in enumerate(self.lines)
            for index in line.indices
        }


def _token(index: int, prediction: OCRPrediction) -> LayoutToken:
    return LayoutToken(
        index=index,
        text=prediction.text,
        left=min(prediction.x),
        top=min(prediction.y),
        right=max(prediction.x),
        bottom=max(prediction.y),
        confidence=float(prediction.score),
    )


def vertical_overlap(first: LayoutToken, second: LayoutToken) -> float:
    overlap = max(0, min(first.bottom, second.bottom) - max(first.top, second.top))
    return overlap / max(1, min(first.height, second.height))


def horizontal_gap(first: LayoutToken, second: LayoutToken) -> float:
    if first.right < second.left:
        return float(second.left - first.right)
    if second.right < first.left:
        return float(first.left - second.right)
    return 0.0


def _same_line(token: LayoutToken, line: list[LayoutToken], scale: float) -> bool:
    # Use both normalized center distance and overlap.  The max-height term
    # tolerates a multi-word/tall detector box without allowing an entire
    # neighbouring row to become one line.
    center = median(item.center_y for item in line)
    line_height = median(item.height for item in line)
    center_limit = max(scale * 0.95, min(token.height, line_height) * 0.9)
    if abs(token.center_y - center) > center_limit:
        return False
    return max(vertical_overlap(token, item) for item in line) >= 0.50


def reconstruct_layout(predictions: Sequence[OCRPrediction]) -> ReconstructedLayout:
    """Build a scale-aware line representation without altering predictions."""
    tokens = tuple(_token(index, prediction) for index, prediction in enumerate(predictions))
    if not tokens:
        return ReconstructedLayout((), (), 1.0, 1.0)

    heights = [token.height for token in tokens if token.height > 0]
    widths = [token.width for token in tokens if token.width > 0]
    median_height = float(median(heights or [1]))
    median_width = float(median(widths or [1]))

    lines: list[list[LayoutToken]] = []
    # Detector result order is not reading order.  Assign each token to the
    # closest compatible existing line, then sort each line left-to-right.
    for token in sorted(tokens, key=lambda item: (item.center_y, item.left, item.index)):
        compatible = [
            (abs(token.center_y - median(item.center_y for item in line)), number, line)
            for number, line in enumerate(lines)
            if _same_line(token, line, median_height)
        ]
        if compatible:
            _, _, line = min(compatible, key=lambda item: item[0])
            line.append(token)
        else:
            lines.append([token])

    ordered_lines = sorted(lines, key=lambda line: (min(item.top for item in line), min(item.left for item in line)))
    result: list[ReconstructedLine] = []
    for line in ordered_lines:
        line.sort(key=lambda item: (item.left, item.top, item.index))
        result.append(
            ReconstructedLine(
                indices=tuple(item.index for item in line),
                text=" ".join(item.text.strip() for item in line if item.text.strip()),
                bbox=(
                    min(item.left for item in line),
                    min(item.top for item in line),
                    max(item.right for item in line),
                    max(item.bottom for item in line),
                ),
                confidence=sum(item.confidence for item in line) / len(line),
            )
        )
    return ReconstructedLayout(tokens, tuple(result), median_height, median_width)


def line_groups(predictions: Sequence[OCRPrediction]) -> list[list[int]]:
    """Compatibility view consumed by the existing extractor."""
    return [list(line.indices) for line in reconstruct_layout(predictions).lines]

