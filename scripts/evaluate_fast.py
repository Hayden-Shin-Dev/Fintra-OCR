"""Run inference before reading frozen gold; cached OCR only, no model response replay."""
import hashlib
import json
import time
from pathlib import Path
from fintraocr.fast import StructuralSelector
from fintraocr.mapping import MappingEngine
from fintraocr.models import OCRDocument
from scripts.run_benchmark import score
ROOT=Path(__file__).resolve().parents[1]

def main():
    dest=ROOT/'outputs/speed-study';dest.mkdir(parents=True,exist_ok=True)
    entries=[]
    for manifest in ('data/holdout/manifest.json','data/fresh/manifest.json'):
        entries.extend(json.loads((ROOT/manifest).read_text(encoding='utf-8')))
    for entry in entries:
        source=ROOT/'outputs/benchmark'/entry['id']/'medium.ocr.json'
        document=OCRDocument.model_validate_json(source.read_text(encoding='utf-8'))
        started=time.perf_counter()
        result=MappingEngine(StructuralSelector()).map(document)
        seconds=time.perf_counter()-started
        gold=ROOT/entry['gold']
        metrics=score(json.loads(gold.read_text(encoding='utf-8')),result.model_dump())
        metrics.update(seconds=seconds,ocr_cached=True,llm_called=False,gold_sha256=hashlib.sha256(gold.read_bytes()).hexdigest(),document_type=entry['kind'],source='sample' if entry['id'].startswith('sample_') else 'synthetic')
        (dest/(entry['id']+'.json')).write_text(json.dumps({'metrics':metrics,'result':result.model_dump()},ensure_ascii=False,indent=2),encoding='utf-8')
        print(entry['id'],metrics['precision'],metrics['recall'],round(seconds,3))
if __name__=='__main__':main()
