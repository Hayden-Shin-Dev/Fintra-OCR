"""Isolated stage worker; web.py may retain a separate warm OCR process."""
import json
import sys
import time
from pathlib import Path

def main():
    req=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"));stage=sys.argv[2]
    folder=Path(req["folder"]);s=req["settings"];started=time.monotonic()
    if stage=="ocr":
        from .ocr import PaddleEngine
        engine=PaddleEngine(s["lang"],s["device"],s["profile"])
        initialized=time.monotonic()
        (folder/'ocr-timing.json').write_text(json.dumps({'initialization_seconds':initialized-started,'ocr_seconds':None}),encoding='utf-8')
        doc=engine.extract(req["files"],s["max_side"],s["enhance"])
        timings={'initialization_seconds':initialized-started,'ocr_seconds':time.monotonic()-initialized}
        (folder/"ocr.json").write_text(doc.model_dump_json(indent=2),encoding="utf-8")
    elif stage=="mapping":
        from .models import OCRDocument
        from .compact import CompactSelector
        from .mapping import MappingEngine
        doc=OCRDocument.model_validate_json((folder/"ocr.json").read_text(encoding="utf-8"))
        from .fast import StructuralSelector
        selector=StructuralSelector() if s.get('mapping_strategy','semantic')=='fast' else CompactSelector(s['model'])
        selector.trace_path=folder/'mapping-trace.json'
        try:
            result=MappingEngine(selector,date_order=s["date_order"],decimal_separator=s["decimal_separator"]).map(doc)
        finally:
            (folder/'mapping-trace.json').write_text(json.dumps(selector.metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        timings={'mapping_seconds':time.monotonic()-started,'model_load_seconds':sum(c.get('load_seconds',0) for c in selector.metadata['calls'])}
        (folder/"result.json").write_text(result.model_dump_json(indent=2),encoding="utf-8")
    else: raise ValueError("Unknown stage")
    (folder/(stage+"-timing.json")).write_text(json.dumps({"seconds":time.monotonic()-started,**timings}),encoding="utf-8")
if __name__=="__main__":main()
