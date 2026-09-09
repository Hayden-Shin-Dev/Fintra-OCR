import json,time,argparse
from pathlib import Path
from fintraocr.compact import CompactSelector
from fintraocr.models import OCRDocument
from fintraocr.mapping import MappingEngine
from scripts.run_benchmark import score
p=argparse.ArgumentParser();p.add_argument('--model',default='qwen3.5:4b');p.add_argument('--id',default='sample_packing_list');a=p.parse_args()
d=OCRDocument.model_validate_json(Path('outputs/benchmark',a.id,'medium.ocr.json').read_text(encoding='utf-8'))
s=CompactSelector(a.model);out=Path('outputs/compact-study',a.model.replace(':','-'),a.id);out.mkdir(parents=True,exist_ok=True);s.trace_path=out/'trace.json'
t=time.perf_counter();r=MappingEngine(s).map(d);elapsed=time.perf_counter()-t
entries=json.loads(Path('data/holdout/manifest.json').read_text(encoding='utf-8'))+json.loads(Path('data/fresh/manifest.json').read_text(encoding='utf-8'));e=next(x for x in entries if x['id']==a.id)
m=score(json.loads(Path(e['gold']).read_text(encoding='utf-8')),r.model_dump());m['seconds']=elapsed;m['calls']=s.metadata['calls'];(out/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8');(out/'score.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print(json.dumps(m),flush=True)
