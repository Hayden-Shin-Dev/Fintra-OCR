"""Re-evaluate the public development case; never call it unseen after debugging."""
import json,time,hashlib
from pathlib import Path
from fintraocr.models import OCRDocument
from fintraocr.fast import StructuralSelector
from fintraocr.mapping import MappingEngine
from scripts.run_benchmark import score
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    jid=(ROOT/'outputs/speed-study/external-id.txt').read_text()
    doc=OCRDocument.model_validate_json((ROOT/'data/ui'/jid/'ocr.json').read_text(encoding='utf-8'))
    started=time.perf_counter();result=MappingEngine(StructuralSelector()).map(doc)
    seconds=time.perf_counter()-started
    gold=ROOT/'data/external/iccc.gold.json'
    metrics=score(json.loads(gold.read_text()),result.model_dump())
    metrics.update(mapping_seconds=seconds,split='external-development-after-first-evaluation',gold_sha256=hashlib.sha256(gold.read_bytes()).hexdigest(),ocr_cached=True)
    (ROOT/'outputs/speed-study/external-development.json').write_text(json.dumps({'metrics':metrics,'result':result.model_dump()},indent=2),encoding='utf-8')
    print(metrics['precision'],metrics['recall'],len(result.items),seconds)
