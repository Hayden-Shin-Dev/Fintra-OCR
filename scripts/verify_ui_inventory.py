"""Exercise real UI endpoints sequentially, including GPU OCR and remapping."""
import json,time
from pathlib import Path
from urllib.request import Request,urlopen
from fintraocr.schemas import catalog
BASE='http://127.0.0.1:8768'
def call(path,body=None):
 req=Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=30) as r:return json.load(r)
def wait(jid):
 started=time.monotonic()
 while time.monotonic()-started<600:
  job=call('/api/jobs/'+jid)
  if job['status'] in ['complete','failed','cancelled']:
   assert job['status']=='complete',job.get('error')
   return job
  time.sleep(.5)
 raise TimeoutError(jid)
assert call('/api/schemas')['documents']==catalog()
sample=next(s for s in call('/api/samples') if s['name']=='IMG_OCR_6_T_NV_004131.png')
settings={'model':'qwen3.5:4b','mapping_strategy':'semantic','mode':'full','device':'gpu:0','profile':'medium'}
out={}
for stage in ['full','remap','ocr_only']:
 if stage=='remap':jid=call('/api/jobs/'+out['full']['id']+'/remap',settings)['id']
 else:jid=call('/api/samples/'+str(sample['id']),{**settings,'mode':'ocr' if stage=='ocr_only' else 'full'})['id']
 job=wait(jid)
 out[stage]={'id':jid,'status':job['status'],'wall_seconds':job['finished']-job['created'],'timings':job['timings']}
 if stage!='ocr_only':
  r=job['result'];assert r['mapping_metadata']['engine']=='compact-semantic-v4'
  assert set(r['fields'])==set(catalog()[r['document_type']]['fields'])
  assert r['fields']['issue_date']['value']=='2004-03-12'
  assert r['items'][0]['quantity']['value']=='76' and r['items'][0]['unit']['value']=='t'
  assert r['items'][0]['package_count']['value']=='67'
  for kind in ['result','mapping-trace']:
   with urlopen(BASE+'/api/jobs/'+jid+'/download/'+kind) as response:
    assert response.status==200 and 'attachment' in response.headers.get('Content-Disposition','')
    out[stage][kind+'_download_bytes']=len(response.read())
 else:assert 'ocr' in job and 'result' not in job
 print(stage,out[stage],flush=True)
out['schema_api_matches']=True
Path('outputs/inventory-regression/ui-verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
