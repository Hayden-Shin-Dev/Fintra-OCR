# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Reproducible live-model evaluation; emits incremental results and records failures."""
import sys,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
os.environ.setdefault('FINTRA_STANDARDS_URL','http://127.0.0.1:18769')
from chat_pipeline import answer
from workspace_chat import context_for
from answer_budget import scope
folder=ROOT/'team-preview/analyses/c3b84748825f4ef3b8d454ccb44d50ee'
audit=json.loads((folder/'result.json').read_text('utf-8'))['audit']
context=context_for(json.loads((folder/'status.json').read_text('utf-8')),folder.parent)
target=ROOT/'tests/chat-architecture/live-results.json'
only=set(sys.argv[1:])
rows=json.loads(target.read_text('utf-8')) if only and target.exists() else []
for case in json.loads((ROOT/'tests/chat-architecture/evaluation.json').read_text('utf-8')):
    if only and case['id'] not in only:continue
    rows=[r for r in rows if r['id']!=case['id']]
    start=time.perf_counter();events=[]
    try:
        with scope(seconds=55):r=answer(audit,case['question'],platform_context=context,on_token=lambda t:events.append((time.perf_counter()-start,t)))
        errors=[]
        if r['selection']['intent']!=case['route']:errors.append('route')
        for word in case['expected_contains']:
            if word not in r['answer']:errors.append('missing:'+word)
        for word in case['forbidden']:
            if word in r['answer']:errors.append('forbidden:'+word)
        rows.append({'id':case['id'],'question':case['question'],'automated_pass':not errors,'errors':errors,'answer':r['answer'],'route':r['selection']['intent'],'latency':r['latency'],'citations':[{'id':c['id'],'kind':c['kind'],'title':c.get('title'),'quote':c.get('quote')} for c in r['citations']],'events':len(events),'human_review_required':case['route'] in ('general','accounting_standard','hybrid')})
    except Exception as e:rows.append({'id':case['id'],'question':case['question'],'automated_pass':False,'errors':[type(e).__name__+': '+str(e)],'seconds':time.perf_counter()-start,'events':len(events)})
    target.write_text(json.dumps(sorted(rows,key=lambda r:r['id']),ensure_ascii=False,indent=2),'utf-8')
    print(case['id'],rows[-1]['automated_pass'],round(time.perf_counter()-start,3),flush=True)
