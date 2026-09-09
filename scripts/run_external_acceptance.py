"""Run publisher examples against frozen OCR and mapping, never against PDF text."""
import argparse,json,time,hashlib
from scripts.azure_acceptance import ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['ocr','map','score']);p.add_argument('--version',default='candidate22-live');p.add_argument('--ocr-version');p.add_argument('--ids',nargs='*');p.add_argument('--model',default='qwen3.5:4b');p.add_argument('--gold-version',choices=['v1','v2'],default='v1');a=p.parse_args()
 base=ROOT/'data/acceptance/external';outputs=ROOT/'outputs/acceptance/external';outputs.mkdir(exist_ok=True)
 if a.stage=='ocr':
  from fintraocr.ocr import PaddleEngine
  start=time.monotonic();engine=PaddleEngine('en','gpu:0','medium');init=time.monotonic()-start
 for name in ['kchain-packing','shipzy-invoice','usda-handbook','hapag-blank']:
  if a.ids and name not in a.ids:continue
  folder=base/name;out=outputs/name/a.version;out.mkdir(parents=True,exist_ok=True)
  image=folder/('page-44.png' if name=='usda-handbook' else 'page-1.png')
  start=time.monotonic()
  try:
   if a.stage=='ocr':
    target=out/'ocr.json'
    if target.exists():continue
    r=engine.extract([image],max_side=2400)
    target.write_text(r.model_dump_json(indent=2),encoding='utf-8')
    (out/'ocr-timing.json').write_text(json.dumps({'seconds':time.monotonic()-start,'initialization_seconds':init}),encoding='utf-8')
   elif a.stage=='map':
    from fintraocr.compact import CompactSelector
    from fintraocr.mapping import MappingEngine
    from fintraocr.models import OCRDocument
    target=out/'result.json'
    if target.exists():continue
    selector=CompactSelector(a.model);selector.trace_path=out/'trace.json'
    ocr_folder=outputs/name/(a.ocr_version or a.version)
    result=MappingEngine(selector).map(OCRDocument.model_validate_json((ocr_folder/'ocr.json').read_text(encoding='utf-8')))
    target.write_text(result.model_dump_json(indent=2),encoding='utf-8')
    (out/'map-timing.json').write_text(json.dumps({'seconds':time.monotonic()-start}),encoding='utf-8')
    (out/'source-hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'fintraocr').glob('*.py')},indent=2),encoding='utf-8')
   else:
    from scripts.score_acceptance import flat,actual,equivalent,bucket,count,rates,audit_result_contract
    from fintraocr.schemas import catalog,ALIASES
    r=json.loads((out/'result.json').read_text(encoding='utf-8'))
    if name=='hapag-blank':
     predicted={path:value for path,value in flat(r).items() if value.get('value') is not None}
     report={'kind':'terms-only negative control, not a completed bill of lading','positive_accuracy':None,'unwarranted_values':predicted,'classification':r['document_type']}
    else:
     gold_path=folder/f'gold-{a.gold_version}.json'
     gold=json.loads(gold_path.read_text(encoding='utf-8'));schema=catalog()[gold['document_type']];metrics=bucket();errors=[]
     for path,want in flat(gold).items():
      key=path.split('.')[-1];scope='items' if path.startswith('items.') else 'fields'
      if scope=='fields' and key in ALIASES[gold['document_type']]:continue
      got=actual(r,path).get('value');ok=equivalent(want,got,schema[scope][key]['kind']);count(metrics,want,got,ok)
      if not ok:errors.append({'field':path,'expected':want,'actual':got})
     for i,row in enumerate(r['items'][len(gold['items']):],len(gold['items'])):
      for key,value in row.items():
       if value['value'] is not None:count(metrics,None,value['value'],False);errors.append({'field':f'items.{i}.{key}','expected':None,'actual':value['value'],'reason':'additional_goods_row'})
     report={'metrics':rates(metrics),'errors':errors,'contract_errors':audit_result_contract(r,gold),'gold_version':a.gold_version,'gold_sha256':hashlib.sha256(gold_path.read_bytes()).hexdigest(),'acceptance_passed':False,'limitations':gold['review_notes'],'reason':gold['ineligibility']}
    (out/('score.json' if a.gold_version=='v1' else f'score-gold-{a.gold_version}.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,json.dumps(report,ensure_ascii=False),flush=True)
   print(name,a.stage,'complete',round(time.monotonic()-start,3),flush=True)
  except Exception as exc:
   error={'stage':a.stage,'type':type(exc).__name__,'message':str(exc),'seconds':time.monotonic()-start}
   (out/(a.stage+'-error.json')).write_text(json.dumps(error),encoding='utf-8');print(name,error,flush=True)

if __name__=='__main__':main()
