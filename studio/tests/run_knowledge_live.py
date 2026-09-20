# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Local integration evaluation; no uploaded transaction data leaves the PC."""
import sys,json,os,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ.setdefault('FINTRA_STANDARDS_URL','http://127.0.0.1:18769')
from audit_research import retrieve
from grounded_chat import model
from enrichment import request
from copilot import compose,render
from model_config import local_model
cases=[('리스부채의 최초 인식 원칙을 설명해줘',['리스부채','리스개시일','인식']),
       ('이연법인세 자산의 인식 요건은 무엇인가요?',['이연법인세','과세소득']),
       ('외화 거래를 최초 인식할 때 적용하는 환율은?',['거래일','현물환율']),
       ('정부보조금의 인식 조건은?',['조건','합리적인 확신']),
       ('재고자산의 기말 측정 원칙은?',['원가','순실현가능']),
       ('충당부채의 인식 조건은?',['의무','유출','추정']),
       ('유형자산의 감가상각 방법은 어떻게 정하나요?',['소비','형태']),
       ('무형자산의 연구 지출은 어떻게 처리하나요?',['비용'])]
output=[]
for question,required in cases:
    start=time.monotonic()
    try:
        refs,trace=retrieve(question,[],'K-IFRS',request,model)
        response=compose(question,[],refs,'knowledge',model)
        text=render(response)
        # Coverage is not a semantic correctness proof; retain quotes for review.
        row={'question':question,'answer':text,'coverage':all(w in text for w in required),'model':local_model(),
             'validation':response,'retrieval':trace,'sources':refs,'seconds':time.monotonic()-start}
    except Exception as exc:row={'question':question,'error':str(exc),'coverage':False}
    output.append(row)
    print(json.dumps({k:v for k,v in row.items() if k in ('question','answer','coverage','error','seconds')},ensure_ascii=False),flush=True)
    Path(__file__).with_name('knowledge-claims-live.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
sys.exit(0 if all(r['coverage'] for r in output) else 1)
