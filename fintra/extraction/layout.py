"""Scale-independent OCR layout. No document identifiers or gold access."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from statistics import median

from fintra.ocr.adapter import OCRResult
from fintra.domain.schema import evidence, missing


def canonical(text):
    return ' '.join(re.findall(r'[A-Z0-9]+', text.upper()))


@dataclass(frozen=True)
class Cell:
    index: int
    text: str
    box: tuple[float, float, float, float]
    polygon: list
    confidence: float | None = None
    page: int = 1

    @property
    def cx(self): return (self.box[0]+self.box[2])/2
    @property
    def cy(self): return (self.box[1]+self.box[3])/2
    @property
    def width(self): return self.box[2]-self.box[0]
    @property
    def height(self): return self.box[3]-self.box[1]


@dataclass(frozen=True)
class Span:
    cells: tuple[Cell, ...]

    @property
    def text(self): return ' '.join(c.text for c in self.cells)
    @property
    def box(self): return (min(c.box[0] for c in self.cells), min(c.box[1] for c in self.cells), max(c.box[2] for c in self.cells), max(c.box[3] for c in self.cells))
    @property
    def cx(self): return (self.box[0]+self.box[2])/2
    @property
    def cy(self): return (self.box[1]+self.box[3])/2


@dataclass(frozen=True)
class Anchor:
    field: str
    span: Span
    strength: float
    alias: str


class Layout:
    def __init__(self, result: OCRResult):
        self.result=result
        self.width=float(result.metadata.get('page_width') or max((r.bbox[2] for r in result.regions), default=1))
        self.height=float(result.metadata.get('page_height') or max((r.bbox[3] for r in result.regions), default=1))
        self.cells=[Cell(r.index, r.text.replace('쉼표',',').strip(),
                         (r.bbox[0]/self.width,r.bbox[1]/self.height,r.bbox[2]/self.width,r.bbox[3]/self.height),
                         r.polygon,r.confidence,r.page) for r in result.regions if r.text.strip()]
        self.line_height=median([c.height for c in self.cells]) if self.cells else .01
        self.lines=self.group_lines(self.cells)
        self.spans=[]
        for line in self.lines:
            for start in range(len(line)):
                for stop in range(start+1,min(start+6,len(line))+1):
                    cells=line[start:stop]
                    if any(b.box[0]-a.box[2] > max(.025,self.line_height*3) for a,b in zip(cells,cells[1:])):
                        break
                    self.spans.append(Span(tuple(cells)))

    def group_lines(self, cells):
        lines=[]
        for c in sorted(cells,key=lambda x:(x.page,x.cy,x.box[0])):
            candidates=[ln for ln in lines if ln[0].page==c.page and abs(median(x.cy for x in ln)-c.cy)<=.6*max(self.line_height,min(c.height,median(x.height for x in ln)))]
            if candidates:
                min(candidates,key=lambda ln:abs(median(x.cy for x in ln)-c.cy)).append(c)
            else: lines.append([c])
        return [sorted(ln,key=lambda x:x.box[0]) for ln in sorted(lines,key=lambda ln:(ln[0].page,median(x.cy for x in ln)))]

    def read(self,cells):
        return ' '.join(c.text for ln in self.group_lines(cells) for c in ln)

    def evidence(self,cells,value=None,method='relative_layout'):
        cells=list({c.index:c for c in cells}.values())
        if not cells: return missing()
        text=self.read(cells) if value is None else value
        if not text.strip(): return missing()
        xs=[p[0] for c in cells for p in c.polygon];ys=[p[1] for c in cells for p in c.polygon]
        confidence=[c.confidence for c in cells if c.confidence is not None]
        return evidence(text,source_text=self.read(cells),bbox=[[min(xs),min(ys)],[max(xs),min(ys)],[max(xs),max(ys)],[min(xs),max(ys)]],
                        confidence=min(confidence) if confidence else None,method=method)

    def anchors(self, aliases):
        found=[]
        for field,names in aliases.items():
            for span in self.spans:
                text=canonical(span.text)
                if not text: continue
                scores=[]
                for alias in names:
                    target=canonical(alias)
                    # Fuzzy matching is restricted to label words, never values.
                    similarity=1.0 if text==target else SequenceMatcher(None,text,target).ratio() if len(target)>=5 else 0
                    if similarity>=.78 and abs(len(text.split())-len(target.split()))<=1:
                        scores.append((similarity,alias))
                if scores:
                    score,alias=max(scores)
                    found.append(Anchor(field,span,score,alias))
        # Prefer strongest longest span when competing spans overlap for a field.
        result=[]
        for a in sorted(found,key=lambda a:(a.strength,len(a.alias)),reverse=True):
            ids={c.index for c in a.span.cells}
            if not any(b.field==a.field and ids & {c.index for c in b.span.cells} for b in result):
                result.append(a)
        return result

    def candidates(self, anchor, anchors, predicate):
        box=anchor.span.box
        labels={c.index for a in anchors for c in a.span.cells}
        same_page=anchor.span.cells[0].page
        spans=[s for s in self.spans if s.cells[0].page==same_page and not any(c.index in labels for c in s.cells)]
        ranked=[]
        for span in spans:
            dy=span.cy-anchor.span.cy
            right=abs(dy)<=self.line_height and span.box[0]>=box[2]-.005
            below=dy>0 and dy<max(.1,6*self.line_height) and span.box[0]>=box[0]-.04 and span.box[0]<box[2]+.12
            if not (right or below): continue
            # A competing heading between the value and label ends the section.
            if below and any(a.field!=anchor.field and box[3]<a.span.cy<span.cy and abs(a.span.box[0]-span.box[0])<.1 for a in anchors): continue
            value=predicate(span.text)
            if value is None: continue
            score=anchor.strength*4 + (1 if right else 0) - abs(dy)*12 - abs(span.box[0]-box[0])*2
            confidence=[c.confidence for c in span.cells if c.confidence is not None]
            if confidence: score+=min(confidence)*.2
            ranked.append((score,span,value))
        return sorted(ranked,key=lambda t:t[0],reverse=True)
