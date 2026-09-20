# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Single-workspace web application. Bound to loopback until managed identity deployment."""
import json,os,time,secrets,hashlib,hmac,re,threading,mimetypes,copy
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlparse
from urllib.request import urlopen,Request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import engine
from decimal import Decimal,InvalidOperation
from datetime import date

ROOT=Path(__file__).resolve().parent.parent
WEB=ROOT/'web';DATA=Path(os.environ.get('FINTRA_WORKSPACE_DATA',str(ROOT/'data')));DATA.mkdir(parents=True,exist_ok=True)
ACCOUNT=Path(os.environ.get('FINTRA_ACCOUNT_FILE',str(DATA/'account.json')))
from workpapers import LOCK as GUARD
SESSIONS={};ATTEMPTS={}
SUPPORT={};SUPPORT_POOL=ThreadPoolExecutor(max_workers=2)

def support_path(owner):
    return DATA/('support-'+hashlib.sha256(owner.encode()).hexdigest()[:20]+'.json')

def support_history(owner):
    p=support_path(owner)
    rows=json.loads(p.read_text('utf-8')) if p.exists() else []
    for row in rows:
        if row.get('status')=='running' and row['id'] not in SUPPORT:row.update(status='failed',error='앱이 종료되어 답변이 중단되었습니다. 다시 질문해 주세요.')
    return rows

def persist_support(task):
    with GUARD:
        rows=support_history(task['owner']); row={k:v for k,v in task.items() if k!='owner'}
        rows=[r for r in rows if r['id']!=row['id']]+[row];write(support_path(task['owner']),rows[-100:])

def expire_support(task):
    with GUARD:
        if task['status']=='running':
            task.update(status='failed',error='답변 준비가 지연되어 중단했습니다. 다시 질문해 주세요.')
            persist_support(task)

def support_answer(task,question,job):
    from workspace_chat import context_for
    try:
        lookup_start=time.perf_counter()
        context=context_for(job,engine.DATA)
        if task.get('view')=='review' and context.get('documents'):context['stage']='awaiting_review'
        selected=task.get('selected_document_id')
        if selected and any(d['id']==selected for d in context.get('documents',[])):context['selected_document_id']=selected
        import chat_pipeline,chat_events
        previous=[m for m in support_history(task['owner']) if m['id']!=task['id'] and m.get('analysis_id')==task.get('analysis_id') and m.get('status')=='complete']
        audit={}
        if job:
            result_file=engine.DATA/job['id']/'result.json'
            if result_file.exists():audit=json.loads(result_file.read_text('utf-8')).get('audit') or {}
        from answer_budget import scope
        context['_db_lookup_seconds']=time.perf_counter()-lookup_start
        with scope(seconds=max(.01,60-(time.time()-task.get('created',time.time())))):
            response=chat_pipeline.answer(audit,question,previous,framework=(job or {}).get('settings',{}).get('framework'),platform_context=context,on_token=lambda token:chat_events.publish(task['id'],'token',{'text':token}))
        response.setdefault('latency',{})['request_total']=time.time()-task.get('created',time.time())
        with GUARD:
            if task.get('status','running')=='running':task.update(status='complete',**response)
    except Exception as exc:task.update(status='failed',error='답변 처리 중 오류가 발생했습니다. 다시 시도해 주세요.',error_type=type(exc).__name__,error_detail=str(exc))
    finally:persist_support(task)

def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8');temp.replace(path)

def corrections(job,changes,actor):
    if job['status']!='awaiting_review':raise ValueError('추출값 확인 단계에서만 수정할 수 있습니다.')
    if not isinstance(changes,list) or len(changes)>2000:raise ValueError('수정 항목을 확인하세요.')
    folder=engine.DATA/job['id'];objects={};history=[]
    for change in changes:
        record=next((r for r in job['document_records'] if r['id']==change.get('document_id')),None)
        if not record or not record.get('result_file'):raise ValueError('문서를 찾을 수 없습니다.')
        name=record['result_file'];obj=objects.setdefault(name,json.loads((folder/name).read_text('utf-8')))
        group=change.get('group');key=change.get('field');value=change.get('value')
        if group!='fields' and (not str(group).isdigit() or int(group)>=len(obj['items'])):raise ValueError('품목 행을 확인하세요.')
        row=obj['fields'] if group=='fields' else obj['items'][int(group)]
        if key not in row or (value is not None and (not isinstance(value,str) or len(value)>4000)):raise ValueError('유효하지 않은 수정 값입니다.')
        cell=row[key];before=copy.deepcopy(cell)
        value=value.strip() or None if isinstance(value,str) else None
        entered=value
        if value is not None and key in {'amount','total_amount','subtotal','tax','quantity','package_count','total_packages','gross_weight','net_weight','unit_price','volume'}:
            if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',value):raise ValueError('금액과 수량은 숫자로 입력하세요.')
            value=format(Decimal(value.replace(',','')),'f')
        if value is not None and key.endswith('_date'):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('날짜는 YYYY-MM-DD로 입력하세요.')
            try:value=date.fromisoformat(value).isoformat()
            except ValueError:raise ValueError('실제 날짜를 입력하세요.')
        if value is not None and key=='currency':
            value=value.upper()
            if not re.fullmatch('[A-Z]{3}',value):raise ValueError('통화는 USD, KRW 등 3자리 코드로 입력하세요.')
        if value==cell.get('value') and not change.get('confirm'):continue
        cell.update(value=value,status='accepted' if value is not None else 'missing',reason='human_reviewed' if value is not None else 'human_cleared')
        cell['human_review']={'actor':actor,'at':time.time(),'entered_value':entered,'previous_value':before.get('value'),'original_status':before.get('status')}
        history.append({'document_id':record['id'],'group':group,'field':key,'before':before,'after':copy.deepcopy(cell),'actor':actor,'at':time.time()})
    # Validate every change before writing any document; retain untouched original OCR files.
    for obj in objects.values():engine.validate_document(obj)
    for name,obj in objects.items():
        original=folder/(name+'.original.json')
        if not original.exists():original.write_bytes((folder/name).read_bytes())
        write(folder/name,obj)
    hp=folder/'corrections.json';previous=json.loads(hp.read_text('utf-8')) if hp.exists() else []
    write(hp,previous+history)
    result=json.loads((folder/'result.json').read_text('utf-8'))
    result['ocr_documents']=[json.loads((folder/r['result_file']).read_text('utf-8')) for r in job['document_records'] if r.get('result_file')]
    result['corrections']=previous+history;engine.write_result(job,result)
    return {'saved':len(history)}

def draft_for(job):
    with GUARD:return _draft_for(job)

def _draft_for(job):
    folder=engine.DATA/job['id'];p=folder/'draft.json'
    if p.exists():
        saved=json.loads(p.read_text('utf-8'))
        from report_content import report_facts
        fresh=report_facts(folder)
        from standard_eligibility import report_references
        audit=json.loads((folder/'result.json').read_text('utf-8')).get('audit') or {}
        fresh['references']=report_references(saved.get('facts',{}).get('references',[]),audit)
        saved['needs_regeneration']=bool(saved.get('generation') and saved['generation'].get('version',0)<4)
        saved['facts']=fresh
        return saved
    result=json.loads((folder/'result.json').read_text('utf-8'));audit=result.get('audit')
    if not audit:raise ValueError('비교가 끝난 뒤 보고서를 작성할 수 있습니다.')
    sections=[]
    for tx in audit.get('transactions',[]):
        lines=[]
        for c in tx.get('checks',[]):
            if c['status'] not in {'flag','review'}:continue
            values=[str(e.get('normalized_value')) for e in c.get('evidence',[]) if e.get('normalized_value') is not None]
            line=c.get('title',c['type'])+' · '+' / '.join(dict.fromkeys(values))
            if c.get('values',{}).get('difference') is not None:line+=' · 차이 '+str(c['values']['difference'])
            lines.append(line)
        passed=sum(c['status']=='pass' for c in tx.get('checks',[]));missing=sum(c['status']=='cannot_evaluate' for c in tx.get('checks',[]))
        lines.append(f'일치한 항목 {passed}개 · 정보 부족으로 비교하지 못한 항목 {missing}개')
        display_id=((tx.get('ledger') or {}).get('fields',{}).get('transaction_id') or {}).get('value') or '거래 '+str(len(sections)+1)
        sections.append({'heading':display_id,'text':'\n'.join(lines) or '검토 결과와 원본 근거를 확인하세요.'})
    for finding in (result.get('standards_review') or {}).get('findings',[]):
        explanation=finding.get('explanation') or {}
        if explanation.get('text'):sections.append({'heading':finding.get('title','검토 참고'),'text':explanation['text']})
        sources={s['id']:s for s in finding.get('retrieval',{}).get('results',[])}
        for citation in explanation.get('citations',[]):
            src=sources.get(citation.get('source_id'),{});loc=src.get('source',{})
            sections.append({'heading':'참고 근거 · '+str(src.get('title') or src.get('standard') or '원문'),'text':str(citation.get('quote',''))+'\n출처: '+str(loc.get('file',''))+' · '+str(loc.get('json_pointer',''))+'\n자료 유형: '+str(src.get('source_type',''))+' · 실제 적용 여부 확인 필요'})
    from report_content import report_facts
    facts=report_facts(folder)
    return {'title':'거래 검토 보고서','summary':f"증빙 {facts['document_count']}개와 연결된 거래 {len(facts['transactions'])}건을 검토했습니다. 아래 비교 내역과 원본 근거를 확인하세요.",'sections':sections,'conclusion':'','revision':0,'reviewed':False,'facts':facts}

class Handler(engine.Handler):
    def session(self):
        try:c=SimpleCookie(self.headers.get('Cookie',''));token=c['fintra_session'].value
        except Exception:return None
        session=SESSIONS.get(token)
        return session if session and session['expires']>time.time() else None
    def json_body(self):
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<=1024*1024:raise ValueError('요청 크기를 확인하세요.')
        return json.loads(self.rfile.read(size))
    def do_GET(self):
        if not self.valid_host():return self.reply({'error':'Invalid Host'},403)
        path=urlparse(self.path).path
        if path=='/api/public-health':
            body=b'{"service":"fintra","online":true}'
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('Access-Control-Allow-Origin','https://hayden-shin-dev.github.io');self.end_headers();self.wfile.write(body);return
        if path=='/api/session':return self.reply({'authenticated':bool(self.session()),'setup':not ACCOUNT.exists() and not engine.deployment.public_origin(),'name':(self.session() or {}).get('name')})
        if path=='/' or path.startswith('/assets/') or path in {'/app.js','/styles.css'}:
            p=(WEB/('index.html' if path=='/' else path.lstrip('/'))).resolve()
            if not p.is_relative_to(WEB.resolve()) or not p.is_file():return self.reply({'error':'Not found'},404)
            from http_payload import content_etag
            body=p.read_bytes();etag=content_etag(body)
            if etag in self.headers.get('If-None-Match','').split(', '):
                self.send_response(304);self.send_header('ETag',etag);self.send_header('Cache-Control','no-cache');self.send_header('Vary','Accept-Encoding');self.end_headers();return
            return self.reply(body,mime=(mimetypes.guess_type(p.name)[0] or 'application/octet-stream')+('; charset=utf-8' if p.suffix in {'.js','.css','.html'} else ''),cache_control='no-cache',etag=etag)
        if not self.session():return self.reply({'error':'로그인 후 이용할 수 있습니다.'},401)
        stream=re.fullmatch(r'/api/(?:support/([a-f0-9]{32})|analyses/([a-f0-9]{32})/chat/([a-f0-9]{32}))/events',path)
        if stream:
            import chat_events,conversations
            if stream[1]:
                task=SUPPORT.get(stream[1])
                if not task or task['owner']!=self.session()['name']:return self.reply({'error':'대화를 찾을 수 없습니다.'},404)
                return chat_events.serve(self,stream[1],lambda:{k:v for k,v in task.items() if k!='owner'})
            if stream[2] not in engine.JOBS:return self.reply({'error':'분석을 찾을 수 없습니다.'},404)
            def message_state():return next((m for m in conversations.history(engine.DATA/stream[2]) if m['id']==stream[3]),None)
            if not message_state():return self.reply({'error':'대화를 찾을 수 없습니다.'},404)
            return chat_events.serve(self,stream[3],message_state)
        if path=='/api/support/history':return self.reply({'messages':support_history(self.session()['name'])})
        sm=re.fullmatch(r'/api/support/([a-f0-9]{32})',path)
        if sm:
            task=SUPPORT.get(sm[1])
            if not task or task['owner']!=self.session()['name']:return self.reply({'error':'대화를 찾을 수 없습니다.'},404)
            return self.reply({k:v for k,v in task.items() if k!='owner'})
        if path=='/api/readiness':
            try:
                with urlopen('http://127.0.0.1:18773/state',timeout=2) as r:s=json.load(r)
                return self.reply({'ready':s.get('ready',False),'error':s.get('error')})
            except Exception:return self.reply({'ready':False,'error':'문서 서비스를 연결하지 못했습니다.'})
        match=re.fullmatch(r'/api/analyses/([a-f0-9]{32})/(draft|edited-report|workpaper)',path)
        if match:
            job=engine.JOBS.get(match[1])
            if not job:return self.reply({'error':'분석을 찾을 수 없습니다.'},404)
            try:
                if match[2]=='workpaper':
                    from workpapers import state
                    return self.reply(state(engine.DATA/job['id']))
                if match[2]=='draft':return self.reply(draft_for(job))
                from report_export import export_pdf
                p=export_pdf(draft_for(job),engine.DATA/job['id'],job['id'])
                return self.reply(p.read_bytes(),mime='application/pdf',download='Fintra-review.pdf')
            except Exception as e:return self.reply({'error':str(e)},400)
        return super().do_GET()
    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Fintra-Request')!='1':return self.reply({'error':'Invalid request'},403)
        if not engine.deployment.valid_origin(self.headers.get('Origin'),engine.PORT):return self.reply({'error':'Invalid origin'},403)
        path=urlparse(self.path).path
        try:
            if path=='/api/login':
                data=self.json_body();name=str(data.get('name','')).strip();password=data.get('password','')
                if not name or not isinstance(password,str) or not password:raise ValueError('이름과 비밀번호를 입력하세요.')
                if not ACCOUNT.exists() and len(password)<10:raise ValueError('새 계정의 비밀번호는 10자 이상 입력하세요.')
                key=self.client_address[0];attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-300]
                if len(attempts)>=10:return self.reply({'error':'잠시 후 다시 로그인하세요.'},429)
                ATTEMPTS[key]=attempts+[time.time()]
                with GUARD:
                    p=ACCOUNT
                    if not p.exists():
                        if engine.deployment.public_origin():return self.reply({'error':'팀 계정이 준비되지 않았습니다.'},503)
                        salt=secrets.token_hex(16);digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
                        write(p,{'name':name,'salt':salt,'hash':digest})
                    account=json.loads(p.read_text('utf-8'));digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(account['salt']),n=16384,r=8,p=1).hex()
                    if not hmac.compare_digest(digest,account['hash']) or name!=account['name']:return self.reply({'error':'이름 또는 비밀번호가 맞지 않습니다.'},401)
                    token=secrets.token_urlsafe(32);SESSIONS[token]={'name':name,'expires':time.time()+43200};ATTEMPTS[key]=[]
                secure='; Secure' if engine.deployment.public_origin() else ''
                self.send_response(200);self.send_header('Set-Cookie',f'fintra_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}');self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"ok":true}');return
            if not self.session():return self.reply({'error':'로그인 후 이용할 수 있습니다.'},401)
            chat_match=re.fullmatch(r'/api/analyses/([a-f0-9]{32})/chat',path)
            if chat_match:
                import conversations
                jid=chat_match[1]
                if jid not in engine.JOBS:raise ValueError('분석을 찾지 못했습니다.')
                data=self.json_body()
                prior=[m for m in support_history(self.session()['name']) if m.get('analysis_id')==jid]
                return self.reply(conversations.submit(engine.DATA/jid,data.get('question'),data.get('transaction_id'),prior,view=data.get('view')),202)
            if path=='/api/support/bind':
                data=self.json_body();jid=data.get('analysis_id')
                if jid not in engine.JOBS:raise ValueError('분석을 찾지 못했습니다.')
                with GUARD:
                    rows=support_history(self.session()['name'])
                    for row in rows:
                        if not row.get('analysis_id'):
                            row['analysis_id']=jid
                            if row['id'] in SUPPORT:SUPPORT[row['id']]['analysis_id']=jid
                    write(support_path(self.session()['name']),rows)
                return self.reply({'ok':True})
            if path=='/api/support':
                data=self.json_body();question=data.get('question','')
                if not isinstance(question,str) or not 1<=len(question.strip())<=1500:raise ValueError('질문을 1~1500자로 입력하세요.')
                with GUARD:
                    if any(t['status']=='running' and t['owner']==self.session()['name'] for t in SUPPORT.values()):raise ValueError('답변을 생성하고 있습니다. 잠시 후 다시 질문하세요.')
                    if len(SUPPORT)>100:SUPPORT.pop(next(iter(SUPPORT)))
                    tid=secrets.token_hex(16);task={'id':tid,'status':'running','owner':self.session()['name'],'question':question,'analysis_id':data.get('analysis_id'),'selected_document_id':data.get('selected_document_id'),'view':'review' if data.get('view')=='review' else None,'created':time.time()};SUPPORT[tid]=task
                    persist_support(task)
                    watchdog=threading.Timer(60,expire_support,args=(task,));watchdog.daemon=True;watchdog.start()
                    SUPPORT_POOL.submit(support_answer,task,question,engine.JOBS.get(data.get('analysis_id')))
                return self.reply({'id':tid},202)
            if path=='/api/logout':
                for key,session in list(SESSIONS.items()):
                    if session is self.session():SESSIONS.pop(key,None)
                return self.reply({'ok':True})
            match=re.fullmatch(r'/api/analyses/([a-f0-9]{32})/(corrections|compare|draft|workpaper)',path)
            if match:
                job=engine.JOBS.get(match[1])
                if not job:return self.reply({'error':'분석을 찾을 수 없습니다.'},404)
                data=self.json_body()
                with GUARD:
                    if match[2]=='workpaper':
                        from workpapers import start
                        if job['status']!='complete':raise ValueError('비교를 마친 뒤 조서를 작성하세요.')
                        framework=data.get('framework',job.get('settings',{}).get('framework'))
                        if framework not in (None,'','K-IFRS','일반기업회계기준'):raise ValueError('지원하는 회계기준을 선택하세요.')
                        return self.reply(start(engine.DATA/job['id'],dict(job.get('settings',{}),framework=framework or None),data.get('revision',0),self.session()['name']),202)
                    if match[2]=='corrections':return self.reply(corrections(job,data.get('changes'),self.session()['name']))
                    if match[2]=='compare':
                        if job['status']!='awaiting_review':raise ValueError('추출값 확인 단계에서 비교를 시작하세요.')
                        if job['failures']:raise ValueError('읽지 못한 문서가 있습니다. 파일을 확인해 새로 업로드하세요.')
                        engine.save(job,status='queued',stage='audit',comparison_started=time.time());engine.POOL.submit(engine.compare,job);return self.reply({'ok':True},202)
                    previous=draft_for(job)
                    if data.get('revision')!=previous['revision']:return self.reply({'error':'다른 창에서 변경됐습니다. 다시 열어주세요.'},409)
                    if not isinstance(data.get('sections'),list) or len(data['sections'])>200:raise ValueError('보고서 항목을 확인하세요.')
                    clean={'title':str(data.get('title',''))[:200],'summary':str(data.get('summary',''))[:20000],'conclusion':str(data.get('conclusion',''))[:20000],'sections':[{'heading':str(s.get('heading',''))[:200],'text':str(s.get('text',''))[:30000]} for s in data['sections']],'reviewed':bool(data.get('reviewed')),'revision':previous['revision']+1,'editor':self.session()['name'],'saved_at':time.time()}
                    clean['generation']=previous.get('generation')
                    clean['facts']=previous.get('facts',{})
                    if clean['reviewed']:clean['reviewer']=self.session()['name'];clean['reviewed_at']=time.time()
                    write(engine.DATA/job['id']/'draft.json',clean);return self.reply(draft_for(job))
            return super().do_POST()
        except Exception as e:return self.reply({'error':str(e)},400)

def serve():
    from workpapers import resume_preparation
    resume_preparation(engine.JOBS,engine.DATA)
    print(f'Fintra web workspace: http://127.0.0.1:{engine.PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',engine.PORT),Handler).serve_forever()
