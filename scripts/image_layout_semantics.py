"""Image-derived, prediction-blind layout evidence for semantic Gold.

AI-Hub Training labels annotate value words but deliberately omit most printed
form headers.  This module uses only the original document pixels and source
token geometry to identify ruled table/party structure.  It never opens OCR
or extractor output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import cv2
import numpy as np


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    cross_start: float
    cross_end: float


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    horizontal: tuple[Segment, ...]
    vertical: tuple[Segment, ...]
    table: tuple[float, float, float, float] | None
    columns: tuple[float, ...]

    @property
    def has_table(self) -> bool:
        return self.table is not None


def _merge(values: list[Segment], *, tolerance: int) -> tuple[Segment, ...]:
    merged: list[Segment] = []
    for item in sorted(values, key=lambda value: (value.start, value.end)):
        if not merged or item.start - merged[-1].end > tolerance:
            merged.append(item)
            continue
        prior = merged[-1]
        merged[-1] = Segment(
            min(prior.start, item.start), max(prior.end, item.end),
            min(prior.cross_start, item.cross_start), max(prior.cross_end, item.cross_end),
        )
    return tuple(merged)


def _segments(mask: np.ndarray, *, horizontal: bool, minimum: int) -> tuple[Segment, ...]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output: list[Segment] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if horizontal:
            if width >= minimum:
                output.append(Segment(float(y), float(y + height), float(x), float(x + width)))
        elif height >= minimum:
            output.append(Segment(float(x), float(x + width), float(y), float(y + height)))
    return _merge(output, tolerance=4)


def _table(grid_width: int, grid_height: int, horizontal: tuple[Segment, ...], vertical: tuple[Segment, ...]) -> tuple[tuple[float, float, float, float] | None, tuple[float, ...]]:
    """Return the largest ruled band with at least four content columns."""
    h = [segment for segment in horizontal if segment.cross_end - segment.cross_start >= .45 * grid_width]
    if len(h) < 2:
        return None, ()
    intervals: list[tuple[float, float, list[Segment]]] = []
    for upper, lower in zip(h, h[1:]):
        top = (upper.start + upper.end) / 2
        bottom = (lower.start + lower.end) / 2
        if bottom - top < .03 * grid_height:
            continue
        crossing = [line for line in vertical if line.cross_start <= top + 3 and line.cross_end >= bottom - 3]
        if len(crossing) >= 5:
            intervals.append((top, bottom, crossing))
    if not intervals:
        # Some Packing List templates draw a header and outer table borders
        # but leave their body columns open.  The large ruled body remains
        # visible evidence of a table even though vertical separators do not
        # span every item row.  Keep its column list empty rather than
        # inventing column boundaries from page coordinates.
        candidates = []
        for upper, lower in zip(h, h[1:]):
            top = (upper.start + upper.end) / 2
            bottom = (lower.start + lower.end) / 2
            if (.07 * grid_height <= bottom - top <= .55 * grid_height
                    and .20 * grid_height <= top <= .85 * grid_height):
                candidates.append((top, bottom))
        if not candidates:
            return None, ()
        top, bottom = max(candidates, key=lambda item: item[1] - item[0])
        left = min(segment.cross_start for segment in h if segment.start <= top + 3)
        right = max(segment.cross_end for segment in h if segment.start <= top + 3)
        return (left, top, right, bottom), ()
    # A document may have a large outer form grid with only a few long
    # verticals and a compact item grid with more columns.  Do not merge
    # adjacent bands merely because they touch: that turns the outer form
    # into a false item table.  Prefer the horizontal band whose *complete*
    # vertical-column structure is strongest, then its height.
    top, bottom, crossing = max(
        intervals,
        key=lambda item: (len(item[2]), item[1] - item[0]),
    )
    xs = sorted((line.start + line.end) / 2 for line in crossing)
    columns: list[float] = []
    for value in xs:
        if not columns or value - columns[-1] > .012 * grid_width:
            columns.append(value)
    if len(columns) < 5:
        return None, ()
    return (min(columns), top, max(columns), bottom), tuple(columns)


def detect_grid(image_path: Path) -> Grid:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"cannot read original image: {image_path}")
    height, width = image.shape[:2]
    binary = cv2.threshold(image, 210, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, width // 14), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, height // 16)))
    horizontal_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    horizontal = _segments(horizontal_mask, horizontal=True, minimum=max(80, width // 4))
    vertical = _segments(vertical_mask, horizontal=False, minimum=max(100, height // 10))
    table, columns = _table(width, height, horizontal, vertical)
    return Grid(width, height, horizontal, vertical, table, columns)


def inside(box: tuple[float, float, float, float], region: tuple[float, float, float, float], *, margin: float = 3.0) -> bool:
    left, top, right, bottom = box
    region_left, region_top, region_right, region_bottom = region
    return left >= region_left - margin and right <= region_right + margin and top >= region_top - margin and bottom <= region_bottom + margin


def party_zone(grid: Grid) -> tuple[float, float, float, float] | None:
    """The structured left party area ends before the detected item table."""
    if grid.table is None:
        return None
    left, table_top, _, _ = grid.table
    return 0.0, .06 * grid.height, max(left, .52 * grid.width), table_top


def table_row_inventory(tokens: list[dict], grid: Grid, document_type: str) -> list[float]:
    """Independently count typed rows inside the image-derived table body.

    This deliberately does not inspect Gold field names or source-token
    selections.  It is used by the audit to catch a generator that emits fewer
    item rows than the original ruled table contains.
    """
    if grid.table is None:
        return []
    left, top, right, bottom = grid.table
    scoped = [token for token in tokens if inside(tuple(token["bbox"]), (left, top, right, bottom), margin=5)]
    scoped.sort(key=lambda token: ((token["bbox"][1] + token["bbox"][3]) / 2, token["bbox"][0]))
    lines: list[list[dict]] = []
    tolerance = .014 * grid.height
    for token in scoped:
        center = (token["bbox"][1] + token["bbox"][3]) / 2
        if not lines:
            lines.append([token]); continue
        current_center = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in lines[-1]) / len(lines[-1])
        if abs(center - current_center) <= tolerance:
            lines[-1].append(token)
        else:
            lines.append([token])
    rows = []
    for line in lines:
        text = " ".join(str(token.get("text", "")) for token in line)
        numeric = sum(bool(re.fullmatch(r"[+$€£¥]?\s*\d[\d,]*(?:\.\d+)?", str(token.get("text", "")).strip())) for token in line)
        alpha = sum(bool(re.search(r"[A-Za-z]", str(token.get("text", "")))) for token in line)
        if document_type == "Commercial Invoice":
            qualifying = numeric >= 2 and alpha >= 1
        elif document_type == "Packing List":
            # A packing item can put its merchandise unit on the following
            # printed line, so inventory base rows from independent source
            # text/numeric evidence only.  The generator later has to bind a
            # unit to that row; this count catches omissions without reading
            # Gold values or selections.
            numeric_like = sum(bool(re.search(r"\d", str(token.get("text", "")))) for token in line)
            has_description_word = any(
                len(re.sub(r"[^A-Za-z]", "", str(token.get("text", "")))) >= 3
                and not re.fullmatch(r"[A-Za-z]*\d[A-Za-z0-9./_-]*", str(token.get("text", "")).strip())
                for token in line
            )
            qualifying = numeric_like >= 2 and alpha >= 1 and has_description_word and not re.search(r"TOTAL\s+(?:GROSS|NET|CTNS|WEIGHT)", text, re.I)
        else:
            qualifying = False
        if qualifying:
            rows.append(sum((token["bbox"][1] + token["bbox"][3]) / 2 for token in line) / len(line))
    return rows
