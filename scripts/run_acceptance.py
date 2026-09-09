"""Run actual OCR or mapping on the preselected batch, preserving all failures."""
import argparse,json,time,hashlib
from pathlib import Path
from scripts.azure_acceptance import ROOT
def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['ocr','map']);p.add_argument('--count',type=int,default=10);p.add_argument('--start-ordinal',type=int,default=1);p.add_argument('--version',default='baseline');p.add_argument('--ocr-version',default='');a=p.parse_args()
 entries=json.loads((ROOT/'data/acceptance/selection.json').read_text(encoding='utf-8'))['entries'];entries=[e for e in entries if a.start_ordinal<=e['ordinal']<=a.count]
 out=ROOT/'outputs/acceptance/runs';out.mkdir(exist_ok=True)
 from datetime import datetime,timezone
 import zipfile
 snapshot=ROOT/'outputs/acceptance/versions'/a.version;snapshot.mkdir(parents=True,exist_ok=True)
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['fintraocr','scripts','tests'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 metadata={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'version':a.version,'ocr_version':a.ocr_version,'arguments':vars(a)}
 if (snapshot/'manifest.json').exists():
  frozen=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
  if frozen['source_sha256']!=hashes:raise RuntimeError('Version source changed; use a new version name')
 else:
  (snapshot/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
  with zipfile.ZipFile(snapshot/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
   for name in hashes:z.write(ROOT/name,name)
 if a.stage=='ocr':
  from fintraocr.ocr import PaddleEngine
  started=time.monotonic();engine=PaddleEngine('en','gpu:0','medium');init=time.monotonic()-started
 else:
  from fintraocr.compact import CompactSelector
  from fintraocr.mapping import MappingEngine
  from fintraocr.models import OCRDocument
 for e in entries:
  dest=out/e['id'];dest.mkdir(exist_ok=True)
  ocr_folder=dest/a.ocr_version if a.ocr_version else dest
  target=ocr_folder/'ocr.json' if a.stage=='ocr' else dest/a.version/'result.json';target.parent.mkdir(exist_ok=True)
  if target.exists():continue
  started=time.monotonic()
  try:
   if a.stage=='ocr':
    image=ROOT/'data/acceptance/documents'/e['id']/'image.png'
    assert hashlib.sha256(image.read_bytes()).hexdigest()==e['image_sha256']
    r=engine.extract([image],max_side=2400,enhance=False)
   else:
    selector=CompactSelector('qwen3.5:4b');selector.trace_path=target.parent/'trace.json'
    r=MappingEngine(selector).map(OCRDocument.model_validate_json((ocr_folder/'ocr.json').read_text(encoding='utf-8')))
   target.write_text(r.model_dump_json(indent=2),encoding='utf-8')
   timing={'seconds':time.monotonic()-started,'initialization_seconds':init if a.stage=='ocr' else 0,'stage':a.stage,'status':'complete'}
   (target.parent/(a.stage+'-timing.json')).write_text(json.dumps(timing),encoding='utf-8');print(e['id'],timing,flush=True)
  except Exception as exc:
   failure={'status':'error','stage':a.stage,'seconds':time.monotonic()-started,'type':type(exc).__name__,'message':str(exc)}
   (target.parent/(a.stage+'-error.json')).write_text(json.dumps(failure),encoding='utf-8');print(e['id'],failure,flush=True)
if __name__=='__main__':main()
