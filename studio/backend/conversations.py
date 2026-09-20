# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Durable chat scoped to one server-owned analysis; never reruns OCR or changes checks."""
import json,time,uuid,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import enrichment
LOCK=threading.RLock();POOL=ThreadPoolExecutor(max_workers=2);ACTIVE={}

def write(folder,messages):
    p=Path(folder)/'conversation.json';temp=p.with_suffix('.tmp')
    temp.write_text(json.dumps(messages,ensure_ascii=False),encoding='utf-8');temp.replace(p)

def history(folder):
    with LOCK:
        p=Path(folder)/'conversation.json';messages=json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
        changed=False
        for m in messages:
            if m['status'] in {'queued','running'} and m['id'] not in ACTIVE:
                m.update(status='failed',error='앱이 종료되어 답변 생성이 중단됐습니다. 다시 질문해 주세요.');changed=True
        if changed:write(folder,messages)
        return messages

def submit(folder,question,transaction_id=None,initial_history=(),view=None):
    folder=Path(folder)
    if not isinstance(question,str) or not 1<=len(question.strip())<=1500:raise ValueError('질문은 1~1500자로 입력하세요.')
    result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    audit=result.get('audit')
    if not audit:raise ValueError('문서 비교가 끝난 뒤 질문할 수 있습니다.')
    if transaction_id and transaction_id not in {t['transaction_id'] for t in audit.get('transactions',[])}:raise ValueError('이 분석에 없는 거래입니다.')
    settings=json.loads((folder/'status.json').read_text(encoding='utf-8')).get('settings',{})
    with LOCK:
        messages=history(folder)
        if any(m['status'] in {'queued','running'} for m in messages):raise ValueError('이 분석의 답변을 생성 중입니다. 완료하거나 중지한 뒤 질문하세요.')
        if len(messages)>=100:raise ValueError('한 분석에서 대화 100회까지 지원합니다.')
        message={'id':uuid.uuid4().hex,'question':question.strip(),'transaction_id':transaction_id,'status':'queued','created':time.time(),'view':'report' if view=='report' else 'results'}
        ACTIVE[message['id']]=threading.Event();messages.append(message);write(folder,messages)
        prior=sorted([m for m in initial_history if m.get('status')=='complete']+messages[:-1],key=lambda m:m.get('created',0))
        watchdog=threading.Timer(60,expire,args=(folder,message['id']));watchdog.daemon=True;watchdog.start()
        POOL.submit(execute,folder,message['id'],audit,prior,settings.get('framework'))
        return message

def cancel(folder,message_id):
    with LOCK:
        messages=history(folder);message=next((m for m in messages if m['id']==message_id),None)
        if not message:raise ValueError('대화를 찾지 못했습니다.')
        event=ACTIVE.get(message_id)
        if event:
            event.set();message.update(status='cancelled',error='답변 생성을 중지했습니다.',finished=time.time());write(folder,messages)
    return {'status':'cancellation_requested'}

def execute(folder,message_id,audit,prior,framework):
    task=None
    def update(**changes):
        with LOCK:
            messages=history(folder);m=next(m for m in messages if m['id']==message_id)
            if m['status'] in {'cancelled','failed'}:return dict(m)
            m.update(changes);write(folder,messages);return dict(m)
    try:
        event=ACTIVE[message_id]
        if event.is_set():raise InterruptedError('답변 생성을 중지했습니다.')
        message=update(status='running')
        import chat_pipeline,chat_events
        from workspace_chat import context_for
        lookup_start=time.perf_counter()
        job=json.loads((Path(folder)/'status.json').read_text('utf-8'))
        context=context_for(job,Path(folder).parent)
        context['view']=message.get('view','results')
        if context['view']=='report':
            from workpapers import read
            draft_path=Path(folder)/'draft.json'
            if draft_path.exists():
                draft=read(draft_path)
                selected_framework=(draft.get('generation') or {}).get('framework')
                if selected_framework in ('K-IFRS','일반기업회계기준'):framework=selected_framework
                context['report_revision']=draft.get('revision')
        from answer_budget import scope
        context['_db_lookup_seconds']=time.perf_counter()-lookup_start
        with scope(event,seconds=max(.01,60-(time.time()-message['created']))):
            response=chat_pipeline.answer(audit,message['question'],prior, message['transaction_id'],framework,cancel=event,platform_context=context,on_token=lambda token:chat_events.publish(message_id,'token',{'text':token}))
        response.setdefault('latency',{})['request_total']=time.time()-message['created']
        if event.is_set():raise InterruptedError('답변 생성을 중지했습니다.')
        update(**response,status='complete',finished=time.time())
    except InterruptedError as exc:update(status='cancelled',error=str(exc))
    except Exception as exc:update(status='failed',error=str(exc))
    finally:
        if task:
            try:enrichment.request('/tasks/'+task+'/cancel',{})
            except Exception:pass
        with LOCK:ACTIVE.pop(message_id,None)

def expire(folder,message_id):
    with LOCK:
        messages=history(folder);m=next((m for m in messages if m['id']==message_id),None)
        if not m or m['status'] not in {'queued','running'}:return
        event=ACTIVE.get(message_id)
        if event:event.set()
        m.update(status='failed',error='답변 준비가 지연되어 중단했습니다. 잠시 후 다시 질문해 주세요.',finished=time.time())
        write(folder,messages)
