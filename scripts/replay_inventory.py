"""Isolate resolver changes with frozen model responses; not inference timings."""
import json,argparse
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from fintraocr.compact import CompactSelector
from fintraocr.models import OCRDocument
from fintraocr.mapping import MappingEngine
p=argparse.ArgumentParser();p.add_argument('--source',default='before');p.add_argument('--output',default='replay');args=p.parse_args()
for folder in Path('outputs/inventory').iterdir():
 trace=folder/args.source/'trace.json'
 if not (folder/args.source/'result.json').exists():continue
 data=json.loads(trace.read_text(encoding='utf-8'))
 responses=[BytesIO(json.dumps(t['response']).encode()) for t in data['trace'] if 'response' in t]
 try:
  with patch('fintraocr.compact.urlopen',side_effect=responses):
   r=MappingEngine(CompactSelector('replay')).map(OCRDocument.model_validate_json((folder/'ocr.json').read_text(encoding='utf-8')))
  out=folder/args.output;out.mkdir(exist_ok=True);(out/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
  old=json.loads((folder/'before/result.json').read_text(encoding='utf-8'))
  changes=[]
  for scope,previous,current in [('fields',old['fields'],r.model_dump()['fields'])]+[(f'items.{i}',old['items'][i] if i<len(old['items']) else {},row) for i,row in enumerate(r.model_dump()['items'])]:
   for key,value in current.items():
    before=previous.get(key,{}).get('value')
    if before!=value['value']:changes.append((scope+'.'+key,before,value['value']))
  print(folder.name,changes,flush=True)
 except Exception as exc:print(folder.name,type(exc).__name__,str(exc),flush=True)
