"""Evaluation-only recognition model comparison, with the same medium detector."""
import json,time,hashlib
from scripts.azure_acceptance import ROOT

def main():
 from paddleocr import PaddleOCR
 from fintraocr.ocr import PaddleEngine
 start=time.monotonic()
 engine=object.__new__(PaddleEngine)
 engine.profile='experiment-v5-server-rec';engine.device='gpu:0'
 engine.model_args={'text_detection_model_name':'PP-OCRv6_medium_det','text_recognition_model_name':'PP-OCRv5_server_rec'}
 engine.model=PaddleOCR(**engine.model_args,device='gpu:0',cpu_threads=4,enable_mkldnn=False,use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=True,text_rec_score_thresh=0.0)
 init=time.monotonic()-start
 for name in ['kchain-packing','shipzy-invoice','usda-handbook']:
  image=ROOT/'data/acceptance/external'/name/('page-44.png' if name=='usda-handbook' else 'page-1.png')
  out=ROOT/'outputs/acceptance/external'/name/'experiment-v5-server-rec';out.mkdir(parents=True,exist_ok=True)
  if (out/'ocr.json').exists():continue
  start=time.monotonic();r=engine.extract([image],max_side=2400)
  (out/'ocr.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
  (out/'ocr-timing.json').write_text(json.dumps({'seconds':time.monotonic()-start,'initialization_seconds_including_download':init,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'models':engine.model_args}),encoding='utf-8')
  print(name,round(time.monotonic()-start,3),len(r.tokens),flush=True)

if __name__=='__main__':main()
