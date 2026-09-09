"""Evaluation-only OCR profile/preprocessing comparison on publisher examples."""
import json,time,gc,hashlib
from scripts.azure_acceptance import ROOT

def main():
 from fintraocr.ocr import PaddleEngine
 import paddle
 for version,profile,enhance in [('experiment-medium-clahe','medium',True),('experiment-mobile','mobile',False)]:
  start=time.monotonic();engine=PaddleEngine('en','gpu:0',profile);init=time.monotonic()-start
  for name in ['kchain-packing','shipzy-invoice','usda-handbook']:
   folder=ROOT/'data/acceptance/external'/name;image=folder/('page-44.png' if name=='usda-handbook' else 'page-1.png')
   out=ROOT/'outputs/acceptance/external'/name/version;out.mkdir(parents=True,exist_ok=True)
   if (out/'ocr.json').exists():continue
   start=time.monotonic();r=engine.extract([image],max_side=2400,enhance=enhance)
   (out/'ocr.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
   record={'seconds':time.monotonic()-start,'initialization_seconds':init,'profile':profile,'enhance':enhance,'max_side':2400,'source_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'models':engine.model_args}
   (out/'ocr-timing.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
   print(version,name,record['seconds'],len(r.tokens),flush=True)
  del engine;gc.collect();paddle.device.cuda.empty_cache()

if __name__=='__main__':main()
