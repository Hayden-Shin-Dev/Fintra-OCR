"""Replay frozen model responses to isolate shared resolver changes."""
import argparse,json
from io import BytesIO
from unittest.mock import patch
from scripts.azure_acceptance import ROOT
from fintraocr.compact import CompactSelector
from fintraocr.mapping import MappingEngine
from fintraocr.models import OCRDocument
from fintraocr.domain import document_heading_types
def main():
 p=argparse.ArgumentParser();p.add_argument('--existing',action='store_true');p.add_argument('--external',action='store_true');p.add_argument('--version',default='candidate1-replay');p.add_argument('--source',default='baseline');a=p.parse_args()
 if a.existing:
  folders=list((ROOT/'outputs/acceptance/baseline-20260909/documents').iterdir())
  cases=[(f.name,f/'ocr.json',f/'trace.json',ROOT/'outputs/inventory'/f.name/a.version) for f in folders]
 elif a.external:
  cases=[(f.name,f/a.source/'ocr.json',f/a.source/'trace.json',f/a.version) for f in (ROOT/'outputs/acceptance/external').iterdir() if (f/a.source/'result.json').exists()]
 else:
  cases=[(f.name,f/'ocr.json',f/a.source/'trace.json',f/a.version) for f in (ROOT/'outputs/acceptance/runs').iterdir() if (f/a.source/'result.json').exists()]
 failures=[]
 for name,ocr,trace,out in cases:
  out.mkdir(exist_ok=True)
  try:
   # A structural negative control legitimately makes no model request.
   # An empty side effect still fails if replay unexpectedly calls the model.
   data=json.loads(trace.read_text(encoding='utf-8')) if trace.exists() else {'trace':[]}
   responses=[BytesIO(json.dumps(t['response']).encode()) for t in data['trace'] if 'response' in t]
   document=OCRDocument.model_validate_json(ocr.read_text(encoding='utf-8')) if a.existing else OCRDocument.model_validate(json.loads((trace.parent/'result.json').read_text(encoding='utf-8'))['ocr'])
   # Current complete-title recognition may remove an old classification call.
   # Replay the remaining responses in order, never feed a type response to
   # the label selector. The original trace remains immutable.
   heading_kinds={kind for token in document.tokens for kind in document_heading_types(token.text)}
   if len(heading_kinds)==1 and data['trace'] and data['trace'][0]['stage']=='document_classification':
    responses=responses[1:]
   with patch('fintraocr.compact.urlopen',side_effect=responses):r=MappingEngine(CompactSelector('qwen3.5:4b')).map(document)
   (out/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
   (out/'map-timing.json').write_text(json.dumps({'seconds':0,'replayed':True}),encoding='utf-8')
   print(name,'replayed',flush=True)
  except Exception as e:failures.append((name,type(e).__name__,str(e)))
 print('Replay failures',failures)
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
