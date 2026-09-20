# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Explicit accounting subjects take precedence over the current comparison.

This is a retrieval vocabulary, not a collection of canned accounting answers.
Unknown subjects still use the user's question for semantic retrieval.
"""
import re

DOMAINS = {
    'lease': ('리스', '임대차', '사용권자산', '전대리스'),
    'inventory': ('재고자산', '재고', '감모', '수량'),
    'revenue': ('수익인식', '매출', '수행의무', '거래가격'),
    'fx': ('외화', '환율', '환산', '기능통화'),
    'ppe': ('유형자산', '감가상각', '재평가'),
    'intangible': ('무형자산', '개발비', '연구비'),
    'impairment': ('손상', '회수가능액', '현금창출단위'),
    'financial': ('금융상품', '금융자산', '금융부채', '기대신용손실', '대손', '상각후원가', '파생상품'),
    'provision': ('충당부채', '우발부채', '우발자산'),
    'tax': ('법인세', '이연법인세', '일시적차이'),
    'employee': ('종업원급여', '퇴직급여', '확정급여'),
    'borrowing': ('차입원가', '적격자산'),
    'grant': ('정부보조금', '보조금'),
    'combination': ('사업결합', '영업권', '합병'),
    'consolidation': ('연결재무제표', '종속기업', '관계기업', '지분법'),
    'cashflow': ('현금흐름',),
    'equity': ('자본', '자기주식', '배당', '주식기준보상'),
    'presentation': ('재무제표표시', '시산표', '유동성', '중요성'),
    'policy': ('회계정책', '추정변경', '전기오류'),
    'subsequent': ('보고기간후', '후속사건'),
    'agriculture': ('생물자산', '농림어업'),
    'fairvalue': ('공정가치',),
    'amount': ('금액', '총액', '단가'),
    'date': ('기간귀속', '거래일', '발행일'),
    'logistics_cost': ('운임', '운송비', '보험료', '관세', '통관', '하역', '부대원가', '수입부가세'),
    'delivery': ('인도조건', '인도 조건', '인도일', '선적일', '검수', '미착품', 'fob', 'cif', 'incoterms'),
    'returns': ('반품', '에누리', '리베이트', '매출할인', '매입할인'),
    'transport_service': ('운송용역', '운송 용역', '운송서비스', '운송 서비스', '포워딩'),
}

SEARCH_TERMS = {
    'logistics_cost':('재고자산 매입원가 운송 하역 수입관세 환급 세금','재고자산 보관원가 판매원가 제외'),
    'delivery':('재화 판매 수익 통제 이전 인도','재고자산 권리 미착품'),
    'returns':('수익 반품 할인 변동대가','재고자산 매입원가 할인 에누리'),
    'transport_service':('용역 수익 수행의무 기간에 걸쳐 이행','용역 제공 수익 진행기준'),
    'amount':('수익 거래가격 측정','재고자산 매입원가 할인'),
    'lease':'리스이용자 리스부채 최초 측정 지급되지 않은 리스료 현재가치',
    'tax':'이연법인세자산 차감할 일시적차이 과세소득 발생 가능성',
    'fx':'외화 거래 최초 인식 거래일 현물환율',
    'grant':'정부보조금 인식 합리적인 확신 조건 준수',
    'inventory':'재고자산 측정 원가 순실현가능가치',
    'provision':('충당부채 다음 요건 모두 충족 인식','충당부채 의무 금액 신뢰성 있게 추정'),
    'ppe':'유형자산 인식 측정 감가상각 내용연수',
    'intangible':'무형자산 연구 개발 지출 인식 비용',
    'impairment':'자산손상 회수가능액 장부금액 손상차손',
    'financial':'금융상품 인식 분류 상각후원가 공정가치',
    'employee':'종업원급여 확정급여채무 근무원가',
    'borrowing':'차입원가 자본화 적격자산',
    'combination':'사업결합 취득법 식별가능자산 영업권',
    'consolidation':'연결재무제표 지배력 종속기업',
    'cashflow':'현금흐름표 영업 투자 재무활동 분류',
    'policy':'회계정책 변경 회계추정 오류 소급 전진 적용',
    'subsequent':'보고기간후 사건 수정 공시',
    'fairvalue':'공정가치 측정 시장참여자 주요시장',
}

def subjects(text):
    compact = re.sub(r'\s+', '', str(text)).lower()
    return [key for key, words in DOMAINS.items()
            if any(word.lower() in compact for word in words)]

def resolved_subjects(question,queries=()):
    explicit=subjects(question)
    planned=list(dict.fromkeys(t for q in queries for t in subjects(q)))
    # Generic measurement words do not name an account. Resolve them through
    # conversation context unless the user explicitly points at document values.
    specific=[t for t in explicit if t not in {'amount','date'}]
    anchored=bool(re.search(r'장부|송장|문서|증빙|비교',question))
    return explicit if specific or anchored else (planned or explicit)

def scope(question, checks, topic_for, queries=()):
    explicit = subjects(question)
    # Short contextual follow-ups use comparison facts; explicit topics never do.
    planned=list(dict.fromkeys(t for q in queries for t in subjects(q)))
    resolved=resolved_subjects(question,queries)
    topics = resolved or list(dict.fromkeys(topic_for(c) for c in checks))
    search = [question[:300]]+[str(q)[:300] for q in queries if q]
    if explicit or planned:
        for topic in resolved:
            expansion=SEARCH_TERMS.get(topic,' '.join(DOMAINS[topic][:2]))
            search.extend(expansion if isinstance(expansion,(list,tuple)) else [expansion])
    return topics, list(dict.fromkeys(search))[:4], bool(explicit)

def allows_amount_shortcut(question,queries=()):
    selected=resolved_subjects(question,queries)
    return not (set(selected) - {'amount'})

def followup_queries(question,history,queries):
    """Keep short follow-ups attached to their last explicit accounting subject."""
    specific=set(subjects(question))-{'amount','date'}
    if specific or re.search(r'장부|송장|문서|증빙|비교',question):return list(queries)
    if not re.match(r'\s*(그럼|그러면|그렇다면|그건|그게|왜|그 경우)',question):return list(queries)
    for item in reversed(history[-4:]):
        prior=item.get('question','')
        if set(subjects(prior))-{'amount','date'}:
            return list(dict.fromkeys([prior+' '+question]+list(queries)))[:2]
    return list(queries)
