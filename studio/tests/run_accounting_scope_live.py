# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Manual local-only retrieval evaluation; writes the inspected passages."""
import sys,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ.setdefault('FINTRA_STANDARDS_URL','http://127.0.0.1:18769')
from audit_research import retrieve
from grounded_chat import model
from enrichment import request

cases=['리스부채의 최초 인식 원칙을 설명해줘','이연법인세 자산의 인식 요건은 무엇인가요?',
       '정부보조금의 회계처리를 설명해줘','외화 거래를 최초 인식할 때 적용하는 환율은?']
output=[]
for question in cases:
    try:
        refs,trace=retrieve(question,[{'title':'장부와 송장 금액','status':'flag','evidence':[{'field_name':'amount'}]}],'K-IFRS',request,model)
        row={'question':question,'titles':[r['title'] for r in refs],'trace':trace,'passages':[r['relevant_text'] for r in refs]}
    except Exception as exc:row={'question':question,'error':str(exc)}
    output.append(row)
    print(json.dumps({k:v for k,v in row.items() if k!='passages'},ensure_ascii=False),flush=True)
    Path(__file__).with_name('accounting-scope-live.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
