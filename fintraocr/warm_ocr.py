"""One OCR model per child process; stdin EOF releases GPU on server exit."""
import json
import sys
import time
import traceback
from pathlib import Path


def main():
    engine = None
    for line in sys.stdin:
        request_path = Path(json.loads(line))
        req = json.loads(request_path.read_text(encoding="utf-8"))
        folder = Path(req["folder"])
        s = req["settings"]
        started = time.monotonic()
        reused = engine is not None
        try:
            if engine is None:
                from .ocr import PaddleEngine
                engine = PaddleEngine(s["lang"], s["device"], s["profile"])
            initialized = time.monotonic()
            timing = {"initialization_seconds": initialized-started, "ocr_seconds": None, "model_reused": reused}
            (folder/"ocr-timing.json").write_text(json.dumps(timing), encoding="utf-8")
            doc = engine.extract(req["files"], s["max_side"], s["enhance"])
            if getattr(engine,'device','').startswith('gpu'):
                import paddle
                paddle.device.cuda.empty_cache()
            timing.update(ocr_seconds=time.monotonic()-initialized, seconds=time.monotonic()-started)
            (folder/"ocr.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            (folder/"ocr-timing.json").write_text(json.dumps(timing), encoding="utf-8")
            outcome = {"ok": True}
        except Exception:
            outcome = {"ok": False, "error": traceback.format_exc()}
        tmp = folder/"ocr-done.tmp"
        tmp.write_text(json.dumps(outcome), encoding="utf-8")
        tmp.replace(folder/"ocr-done.json")
        if not outcome["ok"]:
            break

if __name__ == "__main__":
    main()
