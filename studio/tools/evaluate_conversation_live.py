# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Opt-in live local-model evaluation; never run as a unit test."""
import sys,json,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'tests')]
from chat_pipeline import answer
from test_conversational_analysis import audit_for
from answer_budget import scope
os.environ.setdefault('FINTRA_STANDARDS_URL','http://127.0.0.1:18769')
(ROOT/'tests/conversation-evaluation').mkdir(parents=True,exist_ok=True)
rows=[];history=[]
audit=audit_for('amount',91)
cases=[(audit,'장부와 송장 금액 차이는 어떤 리스크가 있어?','RISK_ANALYSIS',True),(audit,'아니 그래서 무슨 영향이 있다는 거야?','ACCOUNTING_IMPLICATION',True),(audit,'그럼 어떻게 처리해야 해?','RECOMMEND_PROCEDURE',True),(audit,'관련 회계기준도 있어?','STANDARD_REQUEST',True),(audit_for('items',92),'품목 수량이 다른데 어떤 위험이 있어?','RISK_ANALYSIS',False),(audit_for('date',93),'거래일이 송장 날짜와 다른 이유가 뭐야?','ROOT_CAUSE_ANALYSIS',False)]
for a,q,task,follow in cases:
 if not follow:history=[]
 start=time.monotonic()
 try:
  with scope(seconds=51):r=answer(a,q,history,platform_context={'view':'results'})
  history.append(dict(r,status='complete',question=q))
  row={'question':q,'expected_task':task,'task_ok':r['selection'].get('task_intent')==task,'seconds':time.monotonic()-start,'result':r}
 except Exception as e:row={'question':q,'error':repr(e),'seconds':time.monotonic()-start}
 rows.append(row)
 (ROOT/'tests/conversation-evaluation/live-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps({k:v for k,v in row.items() if k!='result'},ensure_ascii=False),flush=True)
 if 'result' in row:print('mode',r.get('analysis',{}).get('mode'),'route',r['selection'],flush=True)
