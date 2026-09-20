# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,json,os,time
from pathlib import Path
sys.path.insert(0,'backend');os.environ['FINTRA_STANDARDS_URL']='http://127.0.0.1:18769'
from grounded_chat import answer
p=Path('data/analyses/b265db463172466bb2395b7a98d8464a/result.json');a=json.loads(p.read_text('utf-8'))['audit'];history=[]
for q in ['이 거래에서 어떤 순서로 검토하면 좋을까?','담당자에게 요청할 자료와 질문을 작성해줘','이 결과로 검토 메모 초안을 써줘','매출 거래의 수익 측정 원칙을 쉽게 설명해줘']:
    r=answer(a,q,history);r['question']=q;history.append(r);Path('tests/copilot-live.json').write_text(json.dumps(history,ensure_ascii=False,indent=2),'utf-8');print(q,r['selection'].get('intent'),round(r['seconds'],2),r['assistance'],r['answer'],flush=True)
