# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Rule -> review purpose -> eligible standards, before retrieval and after expansion."""
from review_rules import REVIEW_RULES

def mapping(checks):
    codes=set();topics=set();ids=[]
    for c in checks:
        if c.get('type') not in REVIEW_RULES or c.get('status') not in ('flag','review','cannot_evaluate'):continue
        k=c['type']
        if k=='ledger_invoice_amount_comparison':codes.update(('1002','1115'));topics.update(('재고','수익'))
        elif k in ('item_quantity_comparison','document_gross_weight_comparison','document_net_weight_comparison'):codes.add('1002');topics.add('재고')
        elif k in ('invoice_transaction_date_review','invoice_posting_date_review'):codes.update(('1002','1115'));topics.update(('재고','수익'))
        else:continue
        ids.append(c['check_id'])
    return {'allowed_standard_ids':sorted(codes),'allowed_topics':sorted(topics),'check_ids':ids,'link_role':'followup_reference',
            'reason':'확인된 문서 차이 또는 필수 누락의 후속 검토를 위한 조건부 참고입니다. 기준 적용 요건을 검증 완료했다는 뜻이 아닙니다.',
            'not_performed':['환율 적정성 검증','기능통화 판단','외화환산','선지급·선수취 시점 검토','현금흐름표 검토']}

def allowed(source,gate):
    import re
    if not gate['allowed_standard_ids']:return False
    title=source.get('title','')
    # No currently implemented comparison rule performs these accounting procedures.
    if re.search(r'1021|2122|1007|환율변동|선지급|선수취|현금흐름',title):return False
    ids=re.findall(r'(?<!\d)(?:10|11|21)\d{2}(?!\d)',title)
    if ids:return bool(set(ids)&set(gate['allowed_standard_ids']))
    return any(t in title for t in gate['allowed_topics'])

def report_references(refs,audit):
    checks=[c for t in audit.get('transactions',[]) for c in t.get('checks',[])]
    gate=mapping(checks)
    return [dict(r,link_role=gate['link_role'],link_reason=gate['reason'],check_ids=gate['check_ids']) for r in refs if allowed(r,gate)]
