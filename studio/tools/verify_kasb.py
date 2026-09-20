# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Real corpus acceptance gate. Missing official paragraphs cause a nonzero exit."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from kasb_kb import Store

store=Store();checks=[]
for number,paragraph in [('1002','9'),('1002','34'),('1115','31')]:
    found=store.exact(number,paragraph)
    checks.append({'standard_number':number,'paragraph':paragraph,'exists':bool(found),
        'status':'PASS' if found else 'FAIL_NOT_INGESTED','source_type':'kifrs_standard'})
result={'counts':store.counts(),'exact_lookup':checks,'passed':all(r['exists'] for r in checks),
        'note':'질의회신 인용이나 합성 테스트를 공식 기준서 DB 존재 검증으로 대체하지 않습니다.'}
path=ROOT/'tests/kasb/acceptance.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed'] else 1)
