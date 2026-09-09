"""Evaluation-only: avoid asking the model to repeat exact domain captions."""
import json,time,hashlib
from io import BytesIO
from unittest.mock import patch
from urllib.request import Request
from scripts.azure_acceptance import ROOT

def main():
 from fintraocr import compact
 from fintraocr.domain import semantic_label,compound_labels
 from fintraocr.mapping import MappingEngine
 from fintraocr.models import OCRDocument
 real_open=compact.urlopen
 for name in ['kchain-packing','shipzy-invoice','usda-handbook']:
  base=ROOT/'outputs/acceptance/external'/name;out=base/'candidate46-unknown-labels-live';out.mkdir(parents=True,exist_ok=True)
  if (out/'result.json').exists():continue
  selector=compact.CompactSelector('qwen3.5:4b');selector.trace_path=out/'trace.json'
  def unknown_request(req,**kwargs):
   body=json.loads(req.data)
   if 'OCR_context_all_tokens' in body['messages'][-1]['content']:
    content=json.loads(body['messages'][-1]['content']);texts=content['OCR_context_all_tokens']
    kept=[tid for tid in content['classify_only_these_ids'] if not semantic_label(texts[tid]) and not compound_labels(texts[tid])]
    content['classify_only_these_ids']=kept
    content['candidate_positions_page_xyxy']={tid:position for tid,position in content['candidate_positions_page_xyxy'].items() if tid in kept}
    body['format']['properties']={tid:spec for tid,spec in body['format']['properties'].items() if tid in kept}
    body['messages'][-1]['content']=json.dumps(content,ensure_ascii=False,separators=(',',':'))
    selector.metadata['trace'][-1]['request']=body;selector.persist_trace()
    if not kept:return BytesIO(json.dumps({'message':{'content':'{}'},'done_reason':'stop','experiment_no_unknown_candidates':True}).encode())
    req=Request(req.full_url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   return real_open(req,**kwargs)
  start=time.monotonic()
  try:
   ocr=OCRDocument.model_validate_json((base/'candidate22-live/ocr.json').read_text(encoding='utf-8'))
   with patch('fintraocr.compact.urlopen',side_effect=unknown_request):result=MappingEngine(selector).map(ocr)
   (out/'result.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
   (out/'map-timing.json').write_text(json.dumps({'seconds':time.monotonic()-start,'variant':'unknown_labels_only_experiment'}),encoding='utf-8')
   (out/'source-hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'fintraocr').glob('*.py')},indent=2),encoding='utf-8')
   print(name,'complete',round(time.monotonic()-start,3),flush=True)
  except Exception as exc:
   error={'type':type(exc).__name__,'message':str(exc),'seconds':time.monotonic()-start}
   (out/'map-error.json').write_text(json.dumps(error),encoding='utf-8');print(name,error,flush=True)

if __name__=='__main__':main()
