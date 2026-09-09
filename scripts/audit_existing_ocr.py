"""Actual OCR regression against the immutable 31-document baseline."""
import argparse,json,time,hashlib
from pathlib import Path
from fintraocr.ocr import PaddleEngine
from scripts.azure_acceptance import ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--version',default='candidate19');p.add_argument('--ids',nargs='*');a=p.parse_args()
 out=ROOT/('outputs/acceptance/existing-ocr-'+a.version);out.mkdir(exist_ok=True)
 engines={}
 changes=[]
 for folder in sorted((ROOT/'outputs/acceptance/baseline-20260909/documents').iterdir()):
  if a.ids and folder.name not in a.ids:continue
  old=json.loads((folder/'ocr.json').read_text(encoding='utf-8'));dest=out/folder.name;dest.mkdir(exist_ok=True)
  profile=old['engine'].split('/')[1]
  if profile not in engines:
   start=time.monotonic();engine=PaddleEngine('en','gpu:0',profile);engines[profile]=(engine,time.monotonic()-start)
  engine,initialization=engines[profile]
  start=time.monotonic()
  if not (dest/'ocr.json').exists():
   result=engine.extract([Path(p['source']) for p in old['pages']],max_side=2400)
   (dest/'ocr.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
   (dest/'timing.json').write_text(json.dumps({'profile':profile,'baseline_sha256':hashlib.sha256((folder/'ocr.json').read_bytes()).hexdigest(),'initialization_seconds':initialization,'ocr_seconds':time.monotonic()-start}),encoding='utf-8')
  new=json.loads((dest/'ocr.json').read_text(encoding='utf-8'))
  if new['engine'].split('/')[1]!=profile:raise RuntimeError('OCR profile mismatch; use a new version directory')
  before={t['id']:t for t in old['tokens']};after={t['id']:t for t in new['tokens']}
  changed=[{'id':key,'before':before.get(key,{}).get('text'),'after':after.get(key,{}).get('text'),'bbox_changed':before.get(key,{}).get('bbox')!=after.get(key,{}).get('bbox')} for key in sorted(before.keys()|after.keys()) if before.get(key,{}).get('text')!=after.get(key,{}).get('text') or before.get(key,{}).get('bbox')!=after.get(key,{}).get('bbox')]
  changes.append({'id':folder.name,'profile':profile,'before_count':len(old['tokens']),'after_count':len(new['tokens']),'changed':changed})
  print(folder.name,len(changed),flush=True)
 (out/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
