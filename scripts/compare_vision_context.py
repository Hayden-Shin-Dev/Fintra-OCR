"""Evaluation-only vision context; OCR IDs/spans remain the sole value source.

Does not change the default application pipeline or default model.
"""
import argparse,base64,hashlib,json,time
from unittest.mock import patch
from urllib.request import Request
from scripts.azure_acceptance import ROOT

def main():
 from fintraocr import compact
 from fintraocr.mapping import MappingEngine
 from fintraocr.models import OCRDocument
 p=argparse.ArgumentParser();p.add_argument('--version',default='candidate40-vision-live');a=p.parse_args()
 real_open=compact.urlopen
 for name in ['kchain-packing','shipzy-invoice','usda-handbook']:
  base=ROOT/'outputs/acceptance/external'/name;out=base/a.version;out.mkdir(parents=True,exist_ok=True)
  if (out/'result.json').exists():continue
  image=ROOT/'data/acceptance/external'/name/('page-44.png' if name=='usda-handbook' else 'page-1.png')
  encoded=base64.b64encode(image.read_bytes()).decode('ascii')
  selector=compact.CompactSelector('qwen3.5:4b');selector.trace_path=out/'trace.json'
  def with_vision(req,**kwargs):
   body=json.loads(req.data)
   if 'OCR_context_all_tokens' in body['messages'][-1]['content']:
    body['messages'][-1]['images']=[encoded]
    body['messages'][0]['content']+=' Use the source image to distinguish printed captions from values and legal narrative. Still select only provided OCR token IDs; never output text read solely from the image.'
    selector.metadata['trace'][-1]['request']=body;selector.persist_trace()
    req=Request(req.full_url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   return real_open(req,**kwargs)
  started=time.monotonic()
  try:
   ocr=OCRDocument.model_validate_json((base/'candidate22-live/ocr.json').read_text(encoding='utf-8'))
   with patch('fintraocr.compact.urlopen',side_effect=with_vision):r=MappingEngine(selector).map(ocr)
   (out/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
   (out/'map-timing.json').write_text(json.dumps({'seconds':time.monotonic()-started,'variant':'vision_context_experiment','image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}),encoding='utf-8')
   (out/'source-hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'fintraocr').glob('*.py')},indent=2),encoding='utf-8')
   print(name,'complete',round(time.monotonic()-started,3),flush=True)
  except Exception as exc:
   record={'type':type(exc).__name__,'message':str(exc),'seconds':time.monotonic()-started}
   (out/'map-error.json').write_text(json.dumps(record),encoding='utf-8');print(name,record,flush=True)

if __name__=='__main__':main()
