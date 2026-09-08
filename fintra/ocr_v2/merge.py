"""Geometry/text resolution for OCR v2.

Raw pass results are never deleted.  This module only constructs a separate
resolved view and records why a source group was represented by one region or
by a merged fragment.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from statistics import median
from typing import Iterable

from .models import RawOCRRegion, ResolvedOCRRegion


def _key(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def _box(region: RawOCRRegion | ResolvedOCRRegion) -> tuple[float, float, float, float]:
    return region.bbox


def _area(box: tuple[float, float, float, float]) -> float:
    return max(1.0, box[2] - box[0]) * max(1.0, box[3] - box[1])


def _iou(first: RawOCRRegion, second: RawOCRRegion) -> float:
    a, b = _box(first), _box(second)
    intersection = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return intersection / (_area(a) + _area(b) - intersection)


def _containment(first: RawOCRRegion, second: RawOCRRegion) -> float:
    a, b = _box(first), _box(second)
    intersection = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return intersection / min(_area(a), _area(b))


def _duplicate(first: RawOCRRegion, second: RawOCRRegion) -> bool:
    first_key, second_key = _key(first.text), _key(second.text)
    if not first_key or not second_key:
        return _iou(first, second) >= 0.70
    similarity = SequenceMatcher(None, first_key, second_key).ratio()
    overlap = _iou(first, second)
    contained = _containment(first, second)
    same_or_nested = first_key == second_key or first_key in second_key or second_key in first_key
    return contained >= 0.55 and (same_or_nested or similarity >= 0.70) or overlap >= 0.45 and similarity >= 0.82


def _quality(region: RawOCRRegion, repetition: int) -> tuple[float, float, float, float]:
    confidence = region.confidence if region.confidence is not None else 0.0
    text_key = _key(region.text)
    # Longer, coherent text wins only after confidence; repeated agreement is
    # a positive signal, not permission to discard raw evidence.
    # For overlapping nested strings, completeness comes before confidence:
    # a high-confidence tile fragment must not replace a complete full-pass
    # string. Confidence remains the tie-breaker among equally complete text.
    return min(1.0, len(text_key) / 40.0), confidence, min(1.0, repetition / 3.0), len(text_key)


def _union_groups(regions: list[RawOCRRegion]) -> list[list[RawOCRRegion]]:
    parent = list(range(len(regions)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    for left in range(len(regions)):
        for right in range(left + 1, len(regions)):
            if _duplicate(regions[left], regions[right]):
                union(left, right)
    groups: dict[int, list[RawOCRRegion]] = defaultdict(list)
    for index, region in enumerate(regions):
        groups[find(index)].append(region)
    return list(groups.values())


def resolve_duplicates(raw_regions: Iterable[RawOCRRegion]) -> tuple[list[ResolvedOCRRegion], dict[str, int]]:
    regions = [region for region in raw_regions if region.text.strip()]
    groups = _union_groups(regions)
    resolved: list[ResolvedOCRRegion] = []
    duplicate_groups = 0
    removed = 0
    for group_index, group in enumerate(groups):
        repetition = len(group)
        if repetition > 1:
            duplicate_groups += 1
            removed += repetition - 1
        representative = max(group, key=lambda region: _quality(region, repetition))
        resolution = "duplicate_representative" if repetition > 1 else "kept"
        resolved.append(ResolvedOCRRegion(
            region_id=len(resolved), text=representative.text,
            confidence=representative.confidence, polygon=representative.polygon,
            source_region_ids=[region.region_id for region in group],
            duplicate_group=group_index if repetition > 1 else None,
            resolution=resolution, page=representative.page,
        ))
    resolved.sort(key=lambda region: (region.bbox[1], region.bbox[0]))
    resolved = [ResolvedOCRRegion(index, region.text, region.confidence, region.polygon,
                                  region.source_region_ids, region.duplicate_group,
                                  region.resolution, region.page)
                for index, region in enumerate(resolved)]
    return resolved, {"duplicate_groups": duplicate_groups, "removed_duplicates": removed}


def _same_line(first: RawOCRRegion, second: RawOCRRegion, height: float) -> bool:
    a, b = _box(first), _box(second)
    return abs((a[1] + a[3]) / 2.0 - (b[1] + b[3]) / 2.0) <= max(height * 0.55, 6.0)


def _looks_like_heading_or_instruction(text: str) -> bool:
    upper = text.strip().upper()
    if not upper:
        return False
    markers = ("(", ")", "PLEASE", "PROVIDE", "COMPLETE", "NAME", "ADDRESS",
               "UNLESS", "ORDER", "PHONE", "FAX", "TEL.", "NO.")
    if any(marker in upper for marker in markers):
        return True
    return "/" in upper and len(upper.split()) <= 5


def _merge_pair(first: RawOCRRegion, second: RawOCRRegion) -> bool:
    a, b = _box(first), _box(second)
    height = median([max(1.0, a[3] - a[1]), max(1.0, b[3] - b[1])])
    if _same_line(first, second, height):
        left, right = sorted((first, second), key=lambda region: _box(region)[0])
        gap = _box(right)[0] - _box(left)[2]
        return -height * 0.2 <= gap <= max(12.0, height * 1.35)
    x_overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) / max(1.0, min(a[2] - a[0], b[2] - b[0]))
    upper, lower = sorted((first, second), key=lambda region: _box(region)[1])
    gap = _box(lower)[1] - _box(upper)[3]
    if x_overlap < 0.65 or not 0 <= gap <= max(10.0, height * 1.2):
        return False
    # A vertically stacked short line followed by another uppercase line is
    # normally a label/value or a new table row, not a broken OCR fragment.
    # Permit vertical reconstruction only when continuation punctuation,
    # lowercase continuation, or a long prose line supplies evidence.
    upper_text = upper.text.strip()
    lower_text = lower.text.strip()
    if _looks_like_heading_or_instruction(upper_text) or _looks_like_heading_or_instruction(lower_text):
        return False
    continuation_punctuation = upper_text.endswith((",", ";", "-", "/"))
    lower_continuation = bool(lower_text) and lower_text[0] in ",.;:/-()" or bool(lower_text) and lower_text[0].islower()
    long_prose = len(_key(upper_text)) >= 30 and not (len(upper_text.split()) <= 5 and len(lower_text.split()) <= 5)
    return continuation_punctuation or lower_continuation or long_prose


def merge_fragments(regions: list[ResolvedOCRRegion]) -> tuple[list[ResolvedOCRRegion], dict[str, int]]:
    # Only merge representatives that have not already been collapsed as
    # duplicates.  This keeps table columns and distinct labels separated.
    source = [RawOCRRegion(region.region_id, region.text, region.confidence, region.polygon, region.page)
              for region in regions]
    used: set[int] = set()
    merged: list[ResolvedOCRRegion] = []
    merges = 0
    for index, current in enumerate(regions):
        if index in used:
            continue
        group = [current]
        used.add(index)
        for other_index in range(index + 1, len(regions)):
            if other_index in used:
                continue
            if _merge_pair(source[index], source[other_index]):
                group.append(regions[other_index])
                used.add(other_index)
        if len(group) == 1:
            merged.append(current)
            continue
        merges += len(group) - 1
        ordered = sorted(group, key=lambda region: (region.bbox[1], region.bbox[0]))
        text = " ".join(region.text.strip() for region in ordered if region.text.strip())
        x1 = min(region.bbox[0] for region in ordered)
        y1 = min(region.bbox[1] for region in ordered)
        x2 = max(region.bbox[2] for region in ordered)
        y2 = max(region.bbox[3] for region in ordered)
        confidence_values = [region.confidence for region in ordered if region.confidence is not None]
        merged.append(ResolvedOCRRegion(
            region_id=len(merged), text=text,
            confidence=min(confidence_values) if confidence_values else None,
            polygon=[[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            source_region_ids=[source_id for region in ordered for source_id in region.source_region_ids],
            duplicate_group=None, resolution="fragment_merge", page=ordered[0].page,
        ))
    merged.sort(key=lambda region: (region.bbox[1], region.bbox[0]))
    merged = [ResolvedOCRRegion(index, region.text, region.confidence, region.polygon,
                                region.source_region_ids, region.duplicate_group,
                                region.resolution, region.page)
              for index, region in enumerate(merged)]
    return merged, {"merged_fragments": merges}


def resolve(raw_regions: list[RawOCRRegion]) -> tuple[list[ResolvedOCRRegion], dict[str, int]]:
    deduped, duplicate_stats = resolve_duplicates(raw_regions)
    merged, fragment_stats = merge_fragments(deduped)
    return merged, {**duplicate_stats, **fragment_stats, "resolved_region_count": len(merged)}
