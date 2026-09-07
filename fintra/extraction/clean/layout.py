"""Scale-independent OCR layout and semantic-anchor discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from statistics import median

from fintra.ocr.adapter import OCRRegion, OCRResult


def canonical(value: str) -> str:
    return " ".join(re.findall(r"[A-Z0-9]+", (value or "").upper()))


@dataclass(frozen=True)
class Cell:
    index: int
    text: str
    box: tuple[float, float, float, float]
    polygon: list
    confidence: float | None
    page: int

    @property
    def x(self) -> float:
        return (self.box[0] + self.box[2]) / 2

    @property
    def y(self) -> float:
        return (self.box[1] + self.box[3]) / 2

    @property
    def width(self) -> float:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]


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
        return (self.box[0] + self.box[2]) / 2

    @property
    def y(self) -> float:
        return (self.box[1] + self.box[3]) / 2

    @property
    def text(self) -> str:
        return " ".join(cell.text for cell in self.cells)


def _area(cell: Cell) -> float:
    return max(1.0, cell.width * cell.height)


def _contained_fragment(small: OCRRegion, large: OCRRegion) -> bool:
    if small.page != large.page:
        return False
    sx1, sy1, sx2, sy2 = small.bbox
    lx1, ly1, lx2, ly2 = large.bbox
    small_area = max(1.0, (sx2 - sx1) * (sy2 - sy1))
    large_area = max(1.0, (lx2 - lx1) * (ly2 - ly1))
    if large_area <= small_area * 1.15:
        return False
    overlap = max(0.0, min(sx2, lx2) - max(sx1, lx1)) * max(0.0, min(sy2, ly2) - max(sy1, ly1))
    if overlap / small_area < 0.70:
        return False
    left, right = canonical(small.text), canonical(large.text)
    return bool(left and left != right and (left in right or SequenceMatcher(None, left, right).ratio() >= 0.92))


class Layout:
    def __init__(self, result: OCRResult):
        self.result = result
        regions = sorted(result.regions, key=lambda item: (item.page, item.bbox[1], item.bbox[0], item.index))
        kept: list[OCRRegion] = []
        for region in sorted(regions, key=lambda item: ((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]), item.index), reverse=True):
            if any(_contained_fragment(region, prior) for prior in kept):
                continue
            if region.text and region.text.strip():
                kept.append(region)
        kept.sort(key=lambda item: (item.page, item.bbox[1], item.bbox[0], item.index))
        width = float(result.metadata.get("page_width") or max((r.bbox[2] for r in kept), default=1.0))
        height = float(result.metadata.get("page_height") or max((r.bbox[3] for r in kept), default=1.0))
        self.width = max(width, 1.0)
        self.height = max(height, 1.0)
        self.cells = [
            Cell(
                region.index,
                region.text.replace("?쇳몴", ",").strip(),
                (region.bbox[0] / self.width, region.bbox[1] / self.height, region.bbox[2] / self.width, region.bbox[3] / self.height),
                region.polygon,
                region.confidence,
                region.page,
            )
            for region in kept
        ]
        self.line_height = median([cell.height for cell in self.cells]) if self.cells else 0.01
        self.lines = self._lines(self.cells)

    @staticmethod
    def _lines(cells: list[Cell]) -> list[list[Cell]]:
        if not cells:
            return []
        result: list[list[Cell]] = []
        for cell in sorted(cells, key=lambda item: (item.page, item.y, item.box[0], item.index)):
            same = [line for line in result if line[0].page == cell.page and abs(median(x.y for x in line) - cell.y) <= max(0.006, min(cell.height, median(x.height for x in line)) * 0.65)]
            if same:
                min(same, key=lambda line: abs(median(x.y for x in line) - cell.y)).append(cell)
            else:
                result.append([cell])
        return [sorted(line, key=lambda item: (item.box[0], item.index)) for line in sorted(result, key=lambda line: (line[0].page, median(x.y for x in line)))]

    def text(self, cells: list[Cell] | tuple[Cell, ...]) -> str:
        values = list(cells)
        if not values:
            return ""
        y_span = max(cell.y for cell in values) - min(cell.y for cell in values)
        # OCR often emits a second wrapped line only a little below the
        # first one.  Treating that span as one horizontal line reorders the
        # text by x-coordinate (e.g. ``ASSEMBL TOOL,BRIDLE``).  The line
        # builder uses a tighter band, so use the same normalized geometry
        # scale here and preserve reading order for wrapped values.
        same_line = y_span <= max(self.line_height * 0.70, 0.008)
        key = (lambda item: (item.page, item.box[0], item.y, item.index)) if same_line else (lambda item: (item.page, item.y, item.box[0], item.index))
        return " ".join(cell.text for cell in sorted(values, key=key))

    def box(self, cells: list[Cell] | tuple[Cell, ...]) -> list[list[float]] | None:
        if not cells:
            return None
        return [
            [min(cell.polygon[0][0] for cell in cells), min(cell.polygon[0][1] for cell in cells)],
            [max(cell.polygon[1][0] for cell in cells), min(cell.polygon[1][1] for cell in cells)],
            [max(cell.polygon[2][0] for cell in cells), max(cell.polygon[2][1] for cell in cells)],
            [min(cell.polygon[3][0] for cell in cells), max(cell.polygon[3][1] for cell in cells)],
        ]

    def anchors(self, aliases: dict[str, tuple[str, ...]]) -> list[Anchor]:
        found: list[Anchor] = []
        for field, names in aliases.items():
            for line in self.lines:
                for start in range(len(line)):
                    for stop in range(start + 1, min(len(line), start + 6) + 1):
                        cells = tuple(line[start:stop])
                        if any(b.box[0] - a.box[2] > max(0.035, self.line_height * 3.0) for a, b in zip(cells, cells[1:])):
                            break
                        phrase = canonical(self.text(cells))
                        if not phrase:
                            continue
                        for alias in names:
                            target = canonical(alias)
                            if phrase == target:
                                found.append(Anchor(field, alias, cells, 1.0))
                            elif re.search(r"(?:^| )" + re.escape(target) + r"(?: |$)", phrase):
                                found.append(Anchor(field, alias, cells, 0.92))
                            elif len(target) >= 6 and len(phrase.split()) <= len(target.split()) + 1 and SequenceMatcher(None, phrase, target).ratio() >= 0.87:
                                found.append(Anchor(field, alias, cells, 0.80))
                            else:
                                # Recognition output can corrupt a label one
                                # token at a time (BWL/BL, LADIN/LADING,
                                # CONSINEE/CONSIGNEE).  Compare aligned token
                                # shapes as a fallback while retaining the
                                # bounded line-span and anchor context.
                                observed = phrase.split()
                                expected = target.split()
                                if len(observed) == len(expected):
                                    similarities = [SequenceMatcher(None, left, right).ratio() for left, right in zip(observed, expected)]
                                    if sum(similarities) / len(similarities) >= 0.76 and min(similarities) >= 0.60:
                                        found.append(Anchor(field, alias, cells, 0.70))
        selected: list[Anchor] = []
        for anchor in sorted(found, key=lambda item: (item.strength, len(item.cells), len(item.alias)), reverse=True):
            key = {cell.index for cell in anchor.cells}
            if not any(item.field == anchor.field and key & {cell.index for cell in item.cells} for item in selected):
                selected.append(anchor)
        return selected

    def nearby(self, anchor: Anchor, anchors: list[Anchor], predicate, *, max_vertical: float = 0.18) -> list[tuple[float, list[Cell], str, str]]:
        labels = {cell.index for item in anchors for cell in item.cells}
        candidates: list[tuple[float, list[Cell], str, str]] = []
        ax1, ay1, ax2, ay2 = anchor.box
        next_boundary = min((other.box[1] for other in anchors if other is not anchor and other.box[1] > ay2 and abs(other.x - anchor.x) < 0.22), default=ay2 + max_vertical)
        for line in self.lines:
            if not line or line[0].page != anchor.cells[0].page:
                continue
            line_cells = [cell for cell in line if cell.index not in labels]
            if not line_cells:
                continue
            clusters: list[list[Cell]] = []
            for cell in line_cells:
                if not clusters or cell.box[0] - clusters[-1][-1].box[2] > max(0.035, self.line_height * 3.0):
                    clusters.append([cell])
                else:
                    clusters[-1].append(cell)
            for cells in clusters:
                y = median(cell.y for cell in cells)
                x1, x2 = min(cell.box[0] for cell in cells), max(cell.box[2] for cell in cells)
                right = abs(y - anchor.y) <= max(self.line_height * 1.4, 0.012) and x1 >= ax2 - 0.01
                below = y >= ay2 - 0.01 and y < next_boundary and abs((x1 + x2) / 2 - anchor.x) <= 0.32
                if not (right or below):
                    continue
                value = predicate(self.text(cells))
                if value is None:
                    continue
                score = anchor.strength * 4.0 + (1.2 if right else 0.0) - abs(y - anchor.y) * 10 - abs(x1 - ax1) * 1.5
                candidates.append((score, cells, value, "right" if right else "below"))
        return sorted(candidates, key=lambda item: item[0], reverse=True)
