"""Scale-independent OCR layout and semantic-anchor primitives."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from statistics import median
from typing import Iterable

from fintra.ocr.adapter import OCRResult


def canonical(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    text = text.replace("&", " AND ")
    return " ".join(re.findall(r"[A-Z0-9]+", text))


def compact(value: str) -> str:
    return canonical(value).replace(" ", "")


@dataclass(frozen=True)
class Cell:
    index: int
    text: str
    box: tuple[float, float, float, float]
    polygon: list[list[float]]
    confidence: float | None
    page: int

    @property
    def x(self) -> float:
        return (self.box[0] + self.box[2]) / 2.0

    @property
    def y(self) -> float:
        return (self.box[1] + self.box[3]) / 2.0

    @property
    def width(self) -> float:
        return max(0.0, self.box[2] - self.box[0])

    @property
    def height(self) -> float:
        return max(0.0, self.box[3] - self.box[1])


@dataclass(frozen=True)
class Anchor:
    field: str
    alias: str
    cells: tuple[Cell, ...]
    strength: float

    @property
    def box(self) -> tuple[float, float, float, float]:
        return (
            min(cell.box[0] for cell in self.cells),
            min(cell.box[1] for cell in self.cells),
            max(cell.box[2] for cell in self.cells),
            max(cell.box[3] for cell in self.cells),
        )

    @property
    def x(self) -> float:
        return (self.box[0] + self.box[2]) / 2.0

    @property
    def y(self) -> float:
        return (self.box[1] + self.box[3]) / 2.0

    @property
    def text(self) -> str:
        return " ".join(cell.text for cell in self.cells)


def _span_score(observed: str, expected: str) -> float:
    left, right = canonical(observed), canonical(expected)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if re.search(rf"(?:^| ){re.escape(right)}(?: |$)", left):
        return 0.94
    if left.startswith(right + " ") or left.endswith(" " + right):
        return 0.90
    if len(right) >= 5:
        return SequenceMatcher(None, left, right).ratio()
    return 0.0


class Layout:
    """Immutable projection of OCR regions into normalized page geometry.

    No region is discarded here.  The original OCRResult remains the source
    of evidence; this object only adds normalized coordinates and reading
    order for candidate generation.
    """

    def __init__(self, result: OCRResult):
        self.result = result
        source = [region for region in result.regions if str(region.text or "").strip()]
        width = float(result.metadata.get("page_width") or max((r.bbox[2] for r in source), default=1.0))
        height = float(result.metadata.get("page_height") or max((r.bbox[3] for r in source), default=1.0))
        self.width, self.height = max(width, 1.0), max(height, 1.0)
        self.cells = [
            Cell(
                region.index,
                str(region.text).strip(),
                (region.bbox[0] / self.width, region.bbox[1] / self.height,
                 region.bbox[2] / self.width, region.bbox[3] / self.height),
                region.polygon,
                region.confidence,
                region.page,
            )
            for region in sorted(source, key=lambda r: (r.page, r.bbox[1], r.bbox[0], r.index))
        ]
        self.line_height = median([cell.height for cell in self.cells]) if self.cells else 0.01
        self.lines = self._group_lines(self.cells)

    @staticmethod
    def _group_lines(cells: list[Cell]) -> list[list[Cell]]:
        lines: list[list[Cell]] = []
        for cell in cells:
            matches = [line for line in lines if line[0].page == cell.page and
                       abs(median(item.y for item in line) - cell.y) <=
                       max(0.006, min(cell.height, median(item.height for item in line)) * 0.62)]
            if matches:
                min(matches, key=lambda line: abs(median(item.y for item in line) - cell.y)).append(cell)
            else:
                lines.append([cell])
        return [sorted(line, key=lambda item: (item.box[0], item.index))
                for line in sorted(lines, key=lambda line: (line[0].page, median(item.y for item in line)))]

    def text(self, cells: Iterable[Cell]) -> str:
        values = list(cells)
        if not values:
            return ""
        y_span = max(item.y for item in values) - min(item.y for item in values)
        same_line = y_span <= max(self.line_height * 0.72, 0.008)
        key = (lambda item: (item.page, item.box[0], item.y, item.index)) if same_line else (lambda item: (item.page, item.y, item.box[0], item.index))
        return " ".join(item.text for item in sorted(values, key=key))

    def box(self, cells: Iterable[Cell]) -> list[list[float]] | None:
        values = list(cells)
        if not values:
            return None
        x1 = min(item.box[0] for item in values) * self.width
        y1 = min(item.box[1] for item in values) * self.height
        x2 = max(item.box[2] for item in values) * self.width
        y2 = max(item.box[3] for item in values) * self.height
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def line_for(self, cell: Cell) -> list[Cell] | None:
        return next((line for line in self.lines if cell in line), None)

    def anchors(self, field: str, aliases: tuple[str, ...]) -> list[Anchor]:
        found: list[Anchor] = []
        for line in self.lines:
            for start in range(len(line)):
                for stop in range(start + 1, min(len(line), start + 5) + 1):
                    cells = tuple(line[start:stop])
                    if any(right.box[0] - left.box[2] > max(0.04, self.line_height * 3.0)
                           for left, right in zip(cells, cells[1:])):
                        break
                    phrase = self.text(cells)
                    for alias in aliases:
                        score = _span_score(phrase, alias)
                        if score < 0.76:
                            continue
                        found.append(Anchor(field, alias, cells, score))
        selected: list[Anchor] = []
        for anchor in sorted(found, key=lambda item: (item.strength, -len(item.cells), len(item.alias)), reverse=True):
            ids = {cell.index for cell in anchor.cells}
            if not any(item.field == field and ids & {cell.index for cell in item.cells} for item in selected):
                selected.append(anchor)
        return sorted(selected, key=lambda item: (item.cells[0].page, item.y, item.x))

    def all_anchors(self, fields: dict[str, tuple[str, ...]]) -> list[Anchor]:
        result: list[Anchor] = []
        for field, aliases in fields.items():
            result.extend(self.anchors(field, aliases))
        return result

    def adjacent(self, anchor: Anchor, all_anchors: list[Anchor]) -> list[tuple[list[Cell], str, float]]:
        """Return bounded right/below text blocks with a relation label."""
        page = anchor.cells[0].page
        used = {cell.index for item in all_anchors for cell in item.cells}
        ax1, ay1, ax2, ay2 = anchor.box
        other = [item for item in all_anchors if item is not anchor and item.cells[0].page == page]
        next_y = min((item.box[1] for item in other if item.box[1] > ay2 and abs(item.x - anchor.x) < 0.28), default=1.0)
        output: list[tuple[list[Cell], str, float]] = []
        for line in self.lines:
            if not line or line[0].page != page:
                continue
            available = [cell for cell in line if cell.index not in used]
            if not available:
                continue
            clusters: list[list[Cell]] = []
            for cell in available:
                if not clusters or cell.box[0] - clusters[-1][-1].box[2] > max(0.04, self.line_height * 3.0):
                    clusters.append([cell])
                else:
                    clusters[-1].append(cell)
            for cells in clusters:
                x1, x2 = min(item.box[0] for item in cells), max(item.box[2] for item in cells)
                y = median(item.y for item in cells)
                right = abs(y - anchor.y) <= max(self.line_height * 1.35, 0.012) and x1 >= ax2 - 0.012
                below = y >= ay2 - 0.008 and y < next_y and abs((x1 + x2) / 2 - anchor.x) <= 0.34
                if right or below:
                    distance = abs(y - anchor.y) * 8.0 + abs(x1 - ax2) * 1.5
                    output.append((cells, "right" if right else "below", distance))
        return sorted(output, key=lambda item: item[2])


__all__ = ["Anchor", "Cell", "Layout", "canonical", "compact"]
