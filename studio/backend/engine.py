# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Loopback-only test backend. Existing engines remain independent and unchanged."""
import json,os,re,sys,time,uuid,threading,subprocess,mimetypes,shutil
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from email.parser import BytesParser
from email.policy import default
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from presentation import enrich
import examples
import verified_sets
import deployment
from atomic_storage import write_json

ROOT=Path(__file__).resolve().parent
HOME=ROOT.parent
DATA=Path(os.environ.get('FINTRA_WEB_DATA',str(ROOT/'jobs')));DATA.mkdir(parents=True,exist_ok=True)
OCR_URL=os.environ.get('FINTRA_OCR_URL','http://127.0.0.1:8768')
PORT=int(os.environ.get('FINTRA_WEB_PORT','8774'))
AUDIT=Path(os.environ.get('FINTRA_AUDIT_HOME',str(HOME/'FintraAudit')))
PYTHON={'audit':Path(os.environ.get('FINTRA_AUDIT_PYTHON',str(AUDIT/'.venv/Scripts/python.exe')))}
PYTHON['report']=Path(os.environ.get('FINTRA_STANDARDS_PYTHON',str(PYTHON['audit'])))
POOL=ThreadPoolExecutor(max_workers=1);JOBS={};LOCK=threading.RLock()

def remote(path,data=None,headers=None):
    try:
        with urlopen(Request(OCR_URL+path,data=data,headers=headers or {}),timeout=15) as r:return json.load(r)
    except HTTPError as e:
        try:detail=json.loads(e.read()).get('detail',str(e))
        except Exception:detail=str(e)
        raise RuntimeError('OCR 서버: '+str(detail)) from e

def save(job,**changes):
    with LOCK:
        job.update(changes)
        clean={k:v for k,v in job.items() if k not in {'cancel','process'}}
        write_json(DATA/job['id']/'status.json',clean)

def cancelled(job):
    if job['cancel'].is_set():raise InterruptedError('사용자가 작업을 중지했습니다.')

def stage(job,name,request):
    cancelled(job);folder=DATA/job['id'];req=folder/(name+'-request.json');out=folder/(name+'.json')
    req.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
    save(job,stage=name);start=time.monotonic()
    env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}
    with (folder/(name+'.log')).open('w',encoding='utf-8') as log:
        p=subprocess.Popen([str(PYTHON[name]),str(ROOT/'worker.py'),name,str(req),str(out)],cwd=str(AUDIT),stdout=log,stderr=log,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        job['process']=p
        try:
            while p.poll() is None:
                cancelled(job)
                if time.monotonic()-start>300:raise TimeoutError(name+' 단계가 300초 제한을 초과했습니다.')
                time.sleep(.2)
            if p.returncode:raise RuntimeError((folder/(name+'.log')).read_text(encoding='utf-8')[-3000:])
        finally:
            if p.poll() is None:p.kill();p.wait()
            job['process']=None
    job['timings'][name]=time.monotonic()-start
    return json.loads(out.read_text(encoding='utf-8'))

def ocr(job,path,record):
    boundary=uuid.uuid4().hex
    settings=json.dumps({'mode':'full','mapping_strategy':'semantic','model':'qwen3.5:4b','lang':job['settings']['lang'],'profile':'medium'})
    import ocr_cache
    cache_root=DATA.parent/'ocr-cache'
    cache_key=ocr_cache.identity(path.read_bytes(),settings)
    cached=ocr_cache.read(cache_root,cache_key)
    if cached:
        try:validate_document(cached)
        except (ValueError,TypeError,KeyError):cached=None
    if cached:
        out=path.with_suffix('.result.json');write_json(out,cached)
        if cached.get('ocr'):
            write_json(path.parent/(record['id']+'.ocr.json'),cached['ocr'])
            record['raw_ocr_file']=record['id']+'.ocr.json'
        record['timings']={'cache_hit':True};record['ocr_stage']='complete'
        job['timings']['ocr:'+path.name]={'cache_hit':True}
        return out
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="settings"\r\n\r\n{settings}\r\n--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="image{path.suffix}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    start=time.monotonic();submitted=remote('/api/jobs',body,{'Content-Type':'multipart/form-data; boundary='+boundary});oid=submitted['id']
    job['ocr_jobs'].append({'input':path.name,'id':oid});record['ocr_job_id']=oid;save(job,stage='ocr_mapping')
    try:
        while True:
            cancelled(job)
            if time.monotonic()-start>900:raise TimeoutError('OCR·매핑이 900초 제한을 초과했습니다.')
            state=remote('/api/jobs/'+oid)
            record['ocr_stage']=state['status'];record['timings']=state.get('timings',{})
            save(job,ocr_status={'file':record['name'],'status':state['status'],'timings':state.get('timings',{})})
            if state.get('ocr'):
                (path.parent/(record['id']+'.ocr.json')).write_text(json.dumps(state['ocr'],ensure_ascii=False),encoding='utf-8')
                record['raw_ocr_file']=record['id']+'.ocr.json'
            if state['status']=='complete':
                validate_document(state['result'])
                try:ocr_cache.store(cache_root,cache_key,state['result'])
                except OSError:pass # A cache failure must not invalidate a successful extraction.
                out=path.with_suffix('.result.json');out.write_text(json.dumps(state['result'],ensure_ascii=False),encoding='utf-8')
                job['timings']['ocr:'+path.name]={'wall_seconds':time.monotonic()-start,**state.get('timings',{})}
                return out
            if state['status'] in {'failed','cancelled'}:raise RuntimeError('OCR: '+str(state.get('error') or state['status']))
            time.sleep(.2)
    except Exception:
        try:remote('/api/jobs/'+oid+'/cancel',b'')
        except Exception:pass
        raise

def write_result(job,result):
    if result.get('audit') and job['settings'].get('verified_set_id'):
        truth=verified_sets.ground_truth(job['settings']['verified_set_id'])
        if truth:
            from dataset_validation import evaluate
            result['ground_truth_validation']=evaluate(truth,result)
    write_json(DATA/job['id']/'result.json',enrich(result,job))

def validate_document(obj):
    # Validate the public JSON contract only; no field extraction or audit rules here.
    if not isinstance(obj,dict) or obj.get('document_type') not in {'commercial_invoice','packing_list','bill_of_lading'}:
        raise ValueError('문서 분류가 지원되지 않거나 unknown입니다.')
    if obj.get('schema_version','2.0')!='2.0':raise ValueError('FintraOCR JSON v2.0이 필요합니다.')
    if not isinstance(obj.get('fields'),dict) or not isinstance(obj.get('items'),list):raise ValueError('매핑된 fields/items가 없는 JSON입니다.')
    for row in [obj['fields'],*obj['items']]:
        if not isinstance(row,dict):raise ValueError('품목 행은 필드 객체여야 합니다.')
        for v in row.values():
            if not isinstance(v,dict) or 'value' not in v or v.get('status') not in {'accepted','missing','review'} or v['value'] is not None and not isinstance(v['value'],str):raise ValueError('필드의 value/status 계약이 잘못되었습니다.')

def run(job):
    result={'audit':None,'ocr_documents':[]};documents=[];seen=set();started=time.monotonic()
    try:
        cancelled(job);save(job,status='running',stage='inputs');write_result(job,result)
        # Bound submissions; the OCR service serializes each individual model.
        # Commit results in upload order so scheduling cannot reorder documents.
        with ThreadPoolExecutor(max_workers=max(1,min(3,int(os.environ.get('FINTRA_DOCUMENT_WORKERS','3'))))) as documents_pool:
            futures=[documents_pool.submit(read_document,job,record) for record in job['document_records']]
            for i,(record,future) in enumerate(zip(job['document_records'],futures)):
                commit_document(job,result,documents,seen,i,record,future)
        save(job,status='awaiting_review',stage='review',current_file=None)
        return
    except InterruptedError as e:
        write_result(job,result);save(job,status='cancelled',error=str(e),finished=time.time())
    except Exception as e:
        job['failures'].append({'document_id':None,'file':job.get('current_file'),'stage':job['stage'],'error':str(e)})
        write_result(job,result);save(job,status='failed',error=str(e),finished=time.time())

def read_document(job,record):
    cancelled(job)
    record.update(status='running',stage='ocr_mapping' if not record['stored'].endswith('.json') else 'json_validation')
    save(job,stage=record['stage'],current_file=record['name'])
    path=DATA/job['id']/record['stored']
    out=path if path.suffix=='.json' else ocr(job,path,record)
    obj=json.loads(out.read_text(encoding='utf-8-sig'));validate_document(obj)
    return out,obj

def commit_document(job,result,documents,seen,i,record,future):
    try:
        cancelled(job)
        out,obj=future.result()
        signature=json.dumps(obj,sort_keys=True,ensure_ascii=False)
        if signature in seen:raise ValueError('동일한 문서 JSON이 중복 제출되었습니다.')
        seen.add(signature);documents.append(str(out));result['ocr_documents'].append(obj)
        record.update(status='complete',stage='complete',result_file=out.name,document_type=obj['document_type'])
    except InterruptedError:record.update(status='cancelled');raise
    except Exception as e:
        record.update(status='failed',error=str(e))
        job['failures'].append({'document_id':record['id'],'file':record['name'],'stage':record['stage'],'error':str(e)})
    save(job,processed_documents=i+1);write_result(job,result)

def compare(job):
    started=time.monotonic()
    result=json.loads((DATA/job['id']/'result.json').read_text(encoding='utf-8'))
    documents=[str(DATA/job['id']/r['result_file']) for r in job['document_records'] if r.get('result_file')]
    try:
        save(job,status='running')
        cancelled(job);save(job,stage='audit',current_file=next((f['name'] for f in job['files'] if f['stored']==job.get('ledger')),None))
        result['audit']=stage(job,'audit',{'ledger':str(DATA/job['id']/job['ledger']) if job.get('ledger') else None,'documents':documents,'config':job['settings']['audit']})
        job['timings']['comparison_ready_seconds']=time.monotonic()-started
        save(job,comparison_ready=True);write_result(job,result)
        if os.environ.get('FINTRA_STANDARDS_URL'):
            try:
                import enrichment
                enrichment.run(job,result,save,write_result,cancelled)
                if result['standards_review']['status']=='partial':
                    job['failures'].append({'document_id':None,'file':None,'stage':'explanation','error':'일부 감사 포인트의 설명 생성에 실패했습니다. 해당 항목을 확인하세요.'})
            except InterruptedError:raise
            except Exception as exc:
                result['standards_review']={'status':'failed','error':str(exc),'findings':result.get('standards_review',{}).get('findings',[])}
                job['failures'].append({'document_id':None,'file':None,'stage':'standards','error':str(exc)})
            cancelled(job);write_result(job,result)
            try:
                result['report']=stage(job,'report',{'result':enrich(result,job),'path':str(DATA/job['id']/'Fintra-review.pdf'),'analysis_id':job['id']})
            except InterruptedError:raise
            except Exception as exc:
                result['report']={'status':'failed','error':str(exc)}
                job['failures'].append({'document_id':None,'file':None,'stage':'report','error':str(exc)})
        cancelled(job);save(job,stage='assembling',current_file=None);write_result(job,result)
        save(job,status='partial' if job['failures'] else 'complete',stage='complete',finished=time.time())
        # Prepare the same verified AI draft while the user reviews results.
        # start() serializes duplicate requests and never overwrites an edited draft.
        try:
            from workpapers import start
            if not (DATA/job['id']/'draft.json').exists():start(DATA/job['id'],job['settings'],0,'Fintra AI')
        except Exception as exc:save(job,draft_preparation_error=str(exc))
    except InterruptedError as e:
        save(job,status='cancelled',error=str(e),finished=time.time())
    except Exception as e:
        save(job,status='failed',error=str(e),finished=time.time())


def new_job(uploads,settings):
    ledgers=[x for x in uploads if x[0]=='ledger'];docs=[x for x in uploads if x[0]=='documents']
    if len(ledgers)>1 or not docs:raise ValueError('증빙 파일과 선택사항인 장부 CSV 최대 1개를 선택하세요.')
    if len(docs)>30:raise ValueError('한 번에 증빙 30개까지 지원합니다.')
    for field,name,blob in ledgers+docs:
        ext=Path(name).suffix.lower()
        if ext not in ({'.csv'} if field=='ledger' else {'.json','.png','.jpg','.jpeg','.webp','.bmp'}):raise ValueError('지원하지 않는 파일 형식: '+ext)
    jid=uuid.uuid4().hex;folder=DATA/jid;folder.mkdir()
    job={'id':jid,'status':'queued','stage':'queued','created':time.time(),'timings':{},'ocr_jobs':[],'settings':settings,'documents':[],'document_records':[],'failures':[],'processed_documents':0,'files':[],'error':None,'cancel':threading.Event(),'process':None}
    for i,(field,name,blob) in enumerate(ledgers+docs):
        filename=str(i)+Path(name).suffix.lower();(folder/filename).write_bytes(blob)
        job['files'].append({'stored':filename,'name':Path(name).name,'bytes':len(blob)})
        if field=='ledger':job['ledger']=filename
        else:
            job['documents'].append(filename)
            record={'id':'document-'+str(i),'stored':filename,'name':Path(name).name,'status':'queued','document_type':None,'images':{}}
            if Path(filename).suffix!='.json':record['images']={'1':filename}
            # Only built-in, server-owned examples can resolve local image paths from JSON.
            if settings.get('_trusted_demo') and filename.endswith('.json'):
                obj=json.loads(blob.decode('utf-8-sig'));allowed=(HOME/'FintraOCR/data').resolve()
                for page in obj.get('ocr',{}).get('pages',[]):
                    source=Path(page.get('source','')).resolve()
                    if source.is_relative_to(allowed) and source.is_file():
                        image=f'{record["id"]}-page-{int(page["page"])}'+source.suffix
                        shutil.copyfile(source,folder/image);record['images'][str(page['page'])]=image
            job['document_records'].append(record)
    JOBS[jid]=job;save(job);POOL.submit(run,job);return jid

class Handler(BaseHTTPRequestHandler):
    def reply(self,data,code=200,mime='application/json',download=None,cache_control='no-store',etag=None):
        from http_payload import encode_payload
        body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        body,encoding=encode_payload(body,mime,self.headers.get('Accept-Encoding',''))
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control',cache_control)
        self.send_header('Vary','Accept-Encoding')
        self.send_header('X-Content-Type-Options','nosniff')
        if etag:self.send_header('ETag',etag)
        if encoding:self.send_header('Content-Encoding',encoding)
        if download:self.send_header('Content-Disposition','attachment; filename="'+download+'"')
        self.end_headers();self.wfile.write(body)
    def valid_host(self):return self.headers.get('Host') in deployment.allowed_hosts(PORT)
    def do_GET(self):
        if not self.valid_host():return self.reply({'error':'Invalid Host'},403)
        path=urlparse(self.path).path.replace('/api/analyses','/api/jobs',1)
        if os.environ.get('FINTRA_NATIVE_ONLY')=='1' and path in {'/','/ui.js','/style.css'}:return self.reply({'error':'Open the Fintra desktop application.'},404)
        if path=='/':return self.reply((ROOT/'index.html').read_bytes(),mime='text/html; charset=utf-8')
        if path in {'/ui.js','/style.css'}:return self.reply((ROOT/path[1:]).read_bytes(),mime='application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css')
        if path=='/api/verified-sets':return self.reply(verified_sets.catalog())
        verified_match=re.fullmatch(r'/api/verified-sets/([A-Za-z0-9_-]+)/(commercial_invoice|packing_list|bill_of_lading)/image',path)
        if verified_match:
            try:
                image_path=verified_sets.image(verified_match[1],verified_match[2])
                return self.reply(image_path.read_bytes(),mime=mimetypes.guess_type(image_path.name)[0] or 'application/octet-stream')
            except (ValueError,KeyError):return self.reply({'error':'Verified image unavailable'},404)
        if path=='/api/samples':return self.reply({'error':'Use verified transaction sets'},410)
        sample_match=re.fullmatch(r'/api/samples/(\d+)/image',path)
        if sample_match:
            try:return self.reply(examples.sample_path(int(sample_match[1])).read_bytes(),mime='image/png')
            except (ValueError,IndexError):return self.reply({'error':'Unknown sample'},404)
        if path=='/api/examples':return self.reply(examples.catalog())
        example_match=re.fullmatch(r'/api/examples/([a-z_]+)/download',path)
        if example_match:
            if example_match[1] not in {c['id'] for c in examples.catalog()}:return self.reply({'error':'Unknown example'},404)
            return self.reply(examples.archive(example_match[1]),mime='application/zip',download='fintra-'+example_match[1]+'.zip')
        if path=='/api/health':
            try:ocr_health=remote('/api/health')
            except Exception as e:ocr_health={'error':str(e)}
            try:
                import enrichment
                standards_health=enrichment.request('/health') if os.environ.get('FINTRA_STANDARDS_URL') else {'ready':False}
            except Exception as exc:standards_health={'ready':False,'error':str(exc)}
            return self.reply({'ocr':ocr_health,'audit':PYTHON['audit'].exists(),'standards':standards_health,'extensions':{'standards':standards_health.get('ready',False),'explanation':bool(os.environ.get('FINTRA_STANDARDS_URL'))}})
        if path=='/api/jobs':
            with LOCK:history=[{k:j.get(k) for k in ('id','status','created','finished','error')} for j in JOBS.values()]
            return self.reply(sorted(history,key=lambda j:j['created'],reverse=True)[:100])
        match=re.fullmatch(r'/api/jobs/([a-f0-9]{32})(?:/(.*))?',path)
        if match and match[1] in JOBS:
            job=JOBS[match[1]];suffix=match[2];folder=DATA/job['id']
            if suffix=='chat':
                import conversations
                return self.reply({'messages':conversations.history(folder)})
            if suffix=='report':
                p=folder/'Fintra-review.pdf'
                if not p.is_file():return self.reply({'error':'검토보고서가 아직 준비되지 않았습니다.'},404)
                return self.reply(p.read_bytes(),mime='application/pdf',download='Fintra-review.pdf')
            if not suffix:
                with LOCK:result=json.loads((folder/'status.json').read_text(encoding='utf-8'))
                return self.reply(result)
            if suffix in {'result','download'}:
                p=folder/'result.json'
                if not p.exists():return self.reply({'error':'결과가 아직 없습니다.'},404)
                result=enrich(json.loads(p.read_text(encoding='utf-8')),job)
                return self.reply(result,download='fintra-analysis.json' if suffix=='download' else None)
            docmatch=re.fullmatch(r'documents/(document-\d+)(?:/(download|image)(?:/(\d+))?)?',suffix)
            if docmatch:
                record=next((d for d in job.get('document_records',[]) if d['id']==docmatch[1]),None)
                if record:
                    if docmatch[2]=='image':
                        name=record.get('images',{}).get(docmatch[3] or '1')
                        if not name:return self.reply({'error':'원본 이미지가 함께 업로드되지 않았습니다.'},404)
                        p=folder/name;return self.reply(p.read_bytes(),mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
                    if record.get('result_file'):
                        return self.reply((folder/record['result_file']).read_bytes(),download=record['id']+'.json' if docmatch[2]=='download' else None)
                    return self.reply({'metadata':record,'error':record.get('error'),'ocr':json.loads((folder/record['raw_ocr_file']).read_text(encoding='utf-8')) if record.get('raw_ocr_file') else None})
            if re.fullmatch(r'evidence/e-[a-f0-9]{24}',suffix) and (folder/'result.json').exists():
                result=enrich(json.loads((folder/'result.json').read_text(encoding='utf-8')),job)
                evidence=result['evidence_index'].get(suffix.split('/')[1])
                if evidence:return self.reply(evidence)
        self.reply({'error':'Not found'},404)
    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Fintra-Request')!='1':return self.reply({'error':'Local requests only'},403)
        origin=self.headers.get('Origin')
        if not deployment.valid_origin(origin,PORT):return self.reply({'error':'Cross-origin request blocked'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<=size<=64*1024*1024:return self.reply({'error':'업로드는 총 64MB 이하로 선택하세요.'},413)
            body=self.rfile.read(size);path=urlparse(self.path).path.replace('/api/analyses','/api/jobs',1)
            chatmatch=re.fullmatch(r'/api/jobs/([a-f0-9]{32})/chat(?:/([a-f0-9]{32})/cancel)?',path)
            if chatmatch:
                if chatmatch[1] not in JOBS:return self.reply({'error':'분석을 찾지 못했습니다.'},404)
                import conversations
                folder=DATA/chatmatch[1]
                if chatmatch[2]:return self.reply(conversations.cancel(folder,chatmatch[2]))
                message=json.loads(body)
                return self.reply(conversations.submit(folder,message.get('question'),message.get('transaction_id')),202)
            if path=='/api/verified-run':
                selection=json.loads(body)
                uploads=verified_sets.uploads(selection.get('set_id'))
                row=verified_sets.selected(selection.get('set_id'))
                settings={'lang':'en','audit':row.get('audit_config',{}),'verified_set_id':selection.get('set_id')}
            elif path=='/api/sample-run':
                return self.reply({'error':'임의 샘플 조합은 중단되었습니다. 검증된 거래 세트를 선택하세요.'},410)
            elif path=='/api/demo':
                uploads,settings=examples.inputs(json.loads(body or b'{}').get('scenario','normal'))
            elif path=='/api/jobs':
                msg=BytesParser(policy=default).parsebytes(('Content-Type: '+self.headers.get('Content-Type','')+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
                if not msg.is_multipart():raise ValueError('multipart/form-data required')
                uploads=[];settings={}
                for part in msg.iter_parts():
                    name=part.get_param('name',header='content-disposition');blob=part.get_payload(decode=True)
                    if name=='settings':settings=json.loads(blob)
                    elif name in {'ledger','documents'}:uploads.append((name,part.get_filename() or '',blob))
                if settings.get('lang','en') not in {'en','korean'}:raise ValueError('Invalid language')
                settings.pop('_trusted_demo',None)
                settings.setdefault('lang','en');settings.setdefault('audit',{})
            else:
                m=re.fullmatch(r'/api/jobs/([a-f0-9]{32})/cancel',path)
                if m and m[1] in JOBS:
                    job=JOBS[m[1]];job['cancel'].set()
                    if job['status']=='queued':
                        write_result(job,{'audit':None,'ocr_documents':[]})
                        save(job,status='cancelled',error='사용자가 대기 작업을 중지했습니다.',finished=time.time())
                    return self.reply({'status':'cancellation_requested'})
                return self.reply({'error':'Not found'},404)
            return self.reply({'id':new_job(uploads,settings)},202)
        except Exception as e:return self.reply({'error':str(e)},400)

for p in DATA.glob('*/status.json'):
    try:
        job=json.loads(p.read_text(encoding='utf-8'));job.update(cancel=threading.Event(),process=None)
        if job['status'] not in {'complete','partial','failed','cancelled','awaiting_review'}:
            for record in job.get('document_records',[]):
                if record['status'] in {'running','queued'}:
                    record.update(status='failed',error='서버 재시작으로 문서 처리가 중단되었습니다.')
                    if record.get('ocr_job_id'):
                        try:remote('/api/jobs/'+record['ocr_job_id']+'/cancel',b'')
                        except Exception:pass
            save(job,status='failed',error='서버 재시작으로 작업이 중단되었습니다.',finished=time.time())
        if 'document_records' not in job:
            job['document_records']=[];job['failures']=[]
            for i,name in enumerate(job.get('documents',[]),1):
                folder=DATA/job['id'];out=name if name.endswith('.json') else str(Path(name).with_suffix('.result.json'))
                record={'id':'document-'+str(i),'name':next((f['name'] for f in job['files'] if f['stored']==name),name),'stored':name,'images':{'1':name} if not name.endswith('.json') else {},'status':'failed'}
                if (folder/out).exists():
                    try:record.update(result_file=out,status='complete',document_type=json.loads((folder/out).read_text(encoding='utf-8-sig')).get('document_type'))
                    except ValueError:pass
                job['document_records'].append(record)
            save(job)
        JOBS[job['id']]=job
    except Exception:pass

if __name__=='__main__':
    print('Fintra test web: http://127.0.0.1:8770',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
