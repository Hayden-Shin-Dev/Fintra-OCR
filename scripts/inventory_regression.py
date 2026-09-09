import argparse,json,subprocess,sys
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from fintraocr.compact import CompactSelector
from fintraocr.mapping import MappingEngine
from fintraocr.models import OCRDocument
from scripts.run_benchmark import score
p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');p.add_argument('--replay-current',action='store_true');p.add_argument('--replay-source',default='live');p.add_argument('--replay-output',default='replay-current');p.add_argument('--ids',nargs='*');p.add_argument('--output-version',default='live');a=p.parse_args()
entries=json.loads(Path('data/holdout/manifest.json').read_text(encoding='utf-8'))+json.loads(Path('data/fresh/manifest.json').read_text(encoding='utf-8'))
cases=[(e['id'],Path('outputs/benchmark')/e['id']/'medium.ocr.json',Path(e['gold']),Path('outputs/compact-study/qwen3.5-4b')/e['id']/'trace.json') for e in entries]
for name,jid in [('lakay','664588c0c97c41ea809143df3503b07e'),('montana','47ddef93b8b34f1ea908b1cdd6a7bfb4'),('iccc','5330796a471143b38b6b9709cdf3ab55')]:
 cases.append(('external-'+name,Path('data/ui')/jid/'ocr.json',Path('data/external')/(name+'.gold.json'),Path('outputs/compact-study')/('external-'+name+'-final')/'trace.json'))
for name,ocr,gold,trace in cases:
 if a.ids and name not in a.ids:continue
 if a.replay_current:trace=Path('outputs/inventory-regression')/a.replay_source/name/'trace.json'
 out=Path('outputs/inventory-regression')/(a.replay_output if a.replay_current else 'replay' if a.replay else a.output_version)/name;out.mkdir(parents=True,exist_ok=True)
 try:
  if a.replay or a.replay_current:
   responses=[BytesIO(json.dumps(t['response']).encode()) for t in json.loads(trace.read_text(encoding='utf-8'))['trace'] if 'response' in t]
   with patch('fintraocr.compact.urlopen',side_effect=responses):r=MappingEngine(CompactSelector('replay')).map(OCRDocument.model_validate_json(ocr.read_text(encoding='utf-8')))
   metrics=score(json.loads(gold.read_text(encoding='utf-8')),r.model_dump());metrics['model_response_replayed']=True
   (out/'score.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8');(out/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
   print(name,metrics['precision'],metrics['recall'],metrics['errors'],flush=True)
  else:
   child=subprocess.run([sys.executable,'-X','utf8','-m','scripts.evaluate_compact','--ocr',str(ocr),'--gold',str(gold),'--output',str(out)],capture_output=True,text=True,encoding='utf-8')
   print(name,child.returncode,child.stdout if child.returncode==0 else child.stderr[-1500:],flush=True)
 except Exception as exc:print(name,type(exc).__name__,str(exc),flush=True)
