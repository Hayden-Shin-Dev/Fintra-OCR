"""Typed candidates and deterministic ranking for Extractor v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .layout import Anchor, Cell, Layout, canonical


@dataclass(frozen=True)
class Candidate:
    field: str
    value: str
    source_text: str
    source_label: str | None
    cells: tuple[Cell, ...]
    anchor: Anchor | None
    relation: str
    type_valid: bool
    section: str | None
    score: float
    reject_reason: str | None = None

    @property
    def confidence(self) -> float | None:
        values = [cell.confidence for cell in self.cells if cell.confidence is not None]
        return min(values) if values else None

    def evidence(self, layout: Layout, *, method: str = "v2_candidate_rank") -> dict[str, Any]:
        return {
            "value": self.value,
            "normalized_value": canonical(self.value),
            "confidence": self.confidence,
            "source_text": self.source_text,
            "source_label": self.source_label,
            "bbox": layout.box(self.cells),
            "page": self.cells[0].page if self.cells else 1,
            "extraction_method": method,
            "status": "extracted" if self.value else "missing",
            "candidate": {
                "semantic_anchor": self.anchor.alias if self.anchor else None,
                "relation": self.relation,
                "normalized_geometry": {
                    "x": sum(cell.x for cell in self.cells) / len(self.cells) if self.cells else None,
                    "y": sum(cell.y for cell in self.cells) / len(self.cells) if self.cells else None,
                },
                "type_valid": self.type_valid,
                "section": self.section,
                "score": round(self.score, 6),
                "reject_reason": self.reject_reason,
            },
        }


def rank(candidates: Iterable[Candidate]) -> list[Candidate]:
    return sorted(
        (candidate for candidate in candidates if candidate.type_valid and candidate.value.strip()),
        key=lambda item: (item.score, item.confidence if item.confidence is not None else 0.0, len(item.value)),
        reverse=True,
    )


def select(layout: Layout, candidates: Iterable[Candidate], *, method: str = "v2_candidate_rank") -> dict[str, Any]:
    ordered = rank(candidates)
    if not ordered:
        return {"value": None, "status": "missing", "extraction_method": method}
    winner = ordered[0]
    if len(ordered) > 1:
        second = ordered[1]
        if abs(winner.score - second.score) < 0.22 and canonical(winner.value) != canonical(second.value):
            return {
                "value": None,
                "source_text": f"{winner.source_text} | {second.source_text}",
                "source_label": winner.source_label,
                "bbox": layout.box(tuple(winner.cells) + tuple(second.cells)),
                "confidence": min(x for x in (winner.confidence, second.confidence) if x is not None) if winner.confidence is not None and second.confidence is not None else winner.confidence or second.confidence,
                "extraction_method": method,
                "status": "ambiguous",
                "candidate": {"top": winner.evidence(layout), "runner_up": second.evidence(layout)},
            }
    return winner.evidence(layout, method=method)


__all__ = ["Candidate", "rank", "select"]
