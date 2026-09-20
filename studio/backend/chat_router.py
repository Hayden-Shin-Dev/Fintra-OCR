# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Single deterministic query plan. Routing does not call retrieval or inference."""
import re
from kasb_kb import exact_reference
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Plan:
    route: str
    tools: tuple
    question: str
    transaction_name: str | None = None

def route(question, history=(), context=None):
    q=question.strip(); context=context or {}
    if re.fullmatch(r'(왜|왜요|그럼|더 자세히|자세히 설명해줘)[?!. ]*',q) and history:
        previous=next((m.get('question','') for m in reversed(history) if m.get('status')=='complete'), '')
        q=previous[:300]+' / 후속 질문: '+q
    tx=re.search(r'\bTX\d+\b',q,re.I)
    standard=bool(exact_reference(q) or re.search(r'K\s*-?\s*IFRS|K\s*-?\s*GAAP|회계\s*(?:기준|원칙|처리|지식)|제\s*\d{4}\s*호|기준서|분개|수익\s*인식|감모|재고자산',q,re.I))
    case=bool(tx or re.search(r'현재|이번|이\s*거래|이\s*결과|검토\s*항목|불일치|누락|정보\s*부족|차이|장부\s*금액|비교\s*결과|검토\s*(?:순서|메모)|담당자|자료.{0,8}요청',q))
    evidence=bool(re.search(r'원본|증빙.{0,8}(?:값|내용|어디|보여)|추출|OCR|송장.{0,12}(?:얼마|번호|총액|통화)|포장명세.{0,12}(?:수량|중량)|선하증권.{0,12}(?:수량|중량|번호)',q,re.I))
    general=bool(re.search(r'업로드|첨부|사용법|로그인|무슨\s*단계|어느\s*단계|(?:문서|CSV|csv).{0,10}(?:필수|올려|넣어|뭐|무엇)|뜻|정의|개념',q)) and not tx
    risk=bool(re.search(r'리스크|위험|왜|영향',q)) and (case or context.get('comparison_available'))
    if general and not standard:mode='general'
    elif (standard and (case or evidence)) or risk:mode='hybrid'
    elif standard:mode='accounting_standard'
    elif evidence:mode='evidence'
    elif case or re.search(r'거래|금액|거래처|일치|몇\s*건|결과|검토할|순서로\s*검토|메모\s*초안|은행\s*계좌|담당자\s*이름|실제\s*입금|지급\s*완료',q):mode='transaction'
    else:mode='general'
    toolset={'general':(), 'transaction':('transaction',), 'evidence':('evidence',), 'accounting_standard':('accounting_standard',), 'hybrid':('transaction','evidence','accounting_standard')}
    return Plan(mode,toolset[mode],q,tx[0].upper() if tx else None)
