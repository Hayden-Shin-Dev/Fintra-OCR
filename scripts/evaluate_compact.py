"""Run real local model mapping on saved OCR; score only pre-annotated fields."""
import argparse,json,time,hashlib
from pathlib import Path
from fintraocr.compact import CompactSelector
from fintraocr.models import OCRDocument
from fintraocr.mapping import MappingEngine
from scripts.run_benchmark import score

def main():
 p=argparse.ArgumentParser();p.add_argument('--ocr',required=True);p.add_argument('--gold',required=True);p.add_argument('--output',required=True);p.add_argument('--model',default='qwen3.5:4b');a=p.parse_args()
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 selector=CompactSelector(a.model);selector.trace_path=out/'trace.json'
 started=time.perf_counter()
 try:result=MappingEngine(selector).map(OCRDocument.model_validate_json(Path(a.ocr).read_text(encoding='utf-8')))
 finally:selector.persist_trace()
 elapsed=time.perf_counter()-started
 gold=json.loads(Path(a.gold).read_text(encoding='utf-8'));metrics=score(gold,result.model_dump())
 metrics.update(seconds=elapsed,ocr_cached=True,model_called=True,gold_sha256=hashlib.sha256(Path(a.gold).read_bytes()).hexdigest(),calls=selector.metadata['calls'])
 metrics['unannotated_items']=[{k:v.value for k,v in row.items() if i<len(gold['items']) and k not in gold['items'][i]} for i,row in enumerate(result.items)]
 metrics['unannotated_fields']={k:v.value for k,v in result.fields.items() if k not in gold['fields']}
 (out/'score.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8');(out/'result.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
 print(json.dumps({k:metrics[k] for k in ['precision','recall','seconds','errors']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
