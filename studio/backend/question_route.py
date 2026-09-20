# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Route explicit requests without making an inference call to classify them.

Unknown/ambiguous wording still uses the semantic router. This selects the
requested operation and evidence; it does not generate accounting conclusions.
"""
import re

def route(question,lookup,history=()):
    from audit_research import topic_for
    q=re.sub(r'\s+','',question)
    if re.search(r'정보부족|비교불가|비교하지못|미비교|누락',q) and re.search(r'이유|왜|사유|어디|뭐|무엇|알려|설명',q):intent='status'
    elif re.search(r'자료|증빙|서류',q) and re.search(r'요청|보내|필요',q):intent='documents'
    elif re.search(r'메모|조서|보고서',q) and re.search(r'써|작성|초안|만들',q):intent='draft'
    elif re.search(r'순서|절차',q) and re.search(r'검토|확인|감사',q):intent='procedure'
    elif re.search(r'리스크|위험|회계적영향|회계상영향',q):intent='risk'
    elif re.search(r'기준|원칙|회계처리|인식요건|측정방법',q) and re.search(r'뭐|무엇|설명|알려|어떻게|방법|요건',q):intent='knowledge'
    else:return None
    words={'quantity':r'수량|중량|재고|감모','amount':r'금액|총액|단가','date':r'일자|날짜|기간귀속','currency':r'통화|환율|외화','identity':r'참조번호|문서번호'}
    topics={t for t,pattern in words.items() if re.search(pattern,q)}
    candidates=[k for k,c in lookup.items() if c['status'] in ('flag','review','cannot_evaluate') and (not topics or topic_for(c) in topics)]
    if not candidates and topics:candidates=[k for k,c in lookup.items() if topic_for(c) in topics]
    return {'purpose':question[:80],'intent':intent,'check_ids':candidates[:5],'needs_standards':intent in {'risk','knowledge'},'search_queries':[]}
