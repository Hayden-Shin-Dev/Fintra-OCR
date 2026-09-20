# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Versioned review contract shared by reports and chat; raw evidence is retained."""
from collections import Counter
from copy import deepcopy
from comparison_scope import scope_for
VERSION=2
AREAS={'documents':'필수 증빙','amount':'거래 금액·통화','counterparty':'거래처','date':'거래일','references':'참조번호','shipping':'선적정보','logistics':'물류정보','items':'품목정보'}
REVIEW_RULES={
 'document_presence':('documents','필수 증빙 존재'),
 'ledger_invoice_amount_comparison':('amount','장부와 송장 금액'),
 'ledger_invoice_currency_comparison':('amount','통화 코드 일치'),
 'ledger_invoice_counterparty_comparison':('counterparty','거래처 대응'),
 'invoice_transaction_date_review':('date','거래일 대응'),
 'invoice_posting_date_review':('date','기장일 대응'),
 'cross_document_date_review':('shipping','선적 사건별 날짜'),
 'document_gross_weight_comparison':('logistics','총중량'),
 'document_net_weight_comparison':('logistics','순중량'),
 'document_package_count_comparison':('logistics','포장 개수'),
 'item_table_unavailable':('items','품목 테이블'),
 'unmatched_item':('items','대응 품목 확인'),
 **{'reference_'+k:('references',v) for k,v in {'invoice_number':'송장 번호','bill_of_lading_number':'B/L 번호','purchase_order_number':'주문 번호','packing_list_number':'포장명세서 번호','buyer_reference':'구매자 참조번호','document_reference':'문서 참조번호','booking_number':'예약 번호'}.items()},
 **{'item_'+k+'_comparison':('items',v) for k,v in {'product_code':'제품 코드','description':'품명','unit':'상품 단위','quantity':'상품 수량','package_count':'품목 포장 개수','gross_weight':'품목 총중량','net_weight':'품목 순중량'}.items()}}
# Explicit scope metadata is a contract, not a model-generated set of comparisons.
RULE_CONTRACTS={kind:{'rule_id':kind,'category':area,'title':title,
 'documents':(['ledger','commercial_invoice'] if kind.startswith('ledger_') or kind in ('invoice_transaction_date_review','invoice_posting_date_review') else ['packing_list','bill_of_lading'] if kind.startswith('document_') and kind!='document_presence' else ['commercial_invoice','packing_list','bill_of_lading']),
 'fields':([kind.removeprefix('reference_')] if kind.startswith('reference_') else ['amount','total_amount','currency'] if kind=='ledger_invoice_amount_comparison' else ['currency'] if kind=='ledger_invoice_currency_comparison' else ['quantity','unit'] if kind=='item_quantity_comparison' else ['counterparty','buyer','seller'] if kind=='ledger_invoice_counterparty_comparison' else ['issue_date','transaction_date'] if kind=='invoice_transaction_date_review' else ['issue_date','posting_date'] if kind=='invoice_posting_date_review' else ['shipment_date','on_board_date','departure_date'] if kind=='cross_document_date_review' else [] if kind in ('document_presence','unmatched_item','item_table_unavailable') else ['total_packages'] if kind=='document_package_count_comparison' else [kind.removeprefix('item_').removeprefix('document_').removesuffix('_comparison')]),
 'required_policy':'required_unless_documented_supplementary_absence','aggregation':'area_then_rule','unknown_rule_policy':'REVIEW'} for kind,(area,title) in REVIEW_RULES.items()}

STATUS={'pass':'PASS','flag':'FAIL','review':'REVIEW','cannot_evaluate':'MISSING'}
LABELS={'PASS':'비교 범위 내 일치','FAIL':'불일치','REVIEW':'판단 필요','MISSING':'필수정보 누락','NOT_APPLICABLE':'검토 대상 아님'}

def unit_for(check):
    kind=check.get('type','')
    fields=('unit',) if kind=='item_quantity_comparison' else ('package_type',) if kind=='item_package_count_comparison' else ('gross_weight_unit','weight_unit') if 'gross_weight' in kind else ('net_weight_unit','weight_unit') if 'net_weight' in kind else ('currency',) if kind=='ledger_invoice_amount_comparison' else ()
    if not fields:return ''
    units={str(e['normalized_value']) for e in check.get('evidence',[]) if e.get('field_name') in fields and e.get('normalized_value') is not None}
    return next(iter(units)) if len(units)==1 else ''

def normalized_audit(audit):
    audit=deepcopy(audit)
    for tx in audit.get('transactions',[]):
        for c in tx.get('checks',[]):
            unit=unit_for(c)
            if unit or 'comparison_unit' in c.get('context',{}):
                c['context']=dict(c.get('context') or {})
                c['context']['comparison_unit']=unit
    return audit

def rule_status(c,tx):
    if c.get('reason')=='required_document_not_linked':return 'MISSING'
    if scope_for(c,tx)=='supplementary':return 'NOT_APPLICABLE'
    if c.get('type') not in REVIEW_RULES:return 'REVIEW'
    return STATUS.get(c.get('status'),'REVIEW')

def combined(statuses):
    statuses=set(statuses)
    return next((s for s in ('FAIL','MISSING','REVIEW','PASS') if s in statuses),'NOT_APPLICABLE')

def build(audit):
    transactions=[]
    for i,tx in enumerate(audit.get('transactions',[]),1):
        entity_types={d.get('id'):kind for kind,d in (tx.get('documents') or {}).items() if isinstance(d,dict)}
        if tx.get('ledger'):entity_types[tx['ledger'].get('id')]='ledger'
        def values_for(c):
            return [{'entity_id':e.get('source',{}).get('entity_id'),'document_type':entity_types.get(e.get('source',{}).get('entity_id')),'field':e.get('field_name'),'value':e.get('normalized_value'),'source':e.get('source',{})} for e in c.get('evidence',[])]
        buckets={k:[] for k in AREAS};outside=[]
        for c in tx.get('checks',[]):
            definition=REVIEW_RULES.get(c.get('type'))
            row={'rule_id':c.get('type','unknown'),'status':rule_status(c,tx),'check_id':c['check_id'],'check':c}
            if definition:buckets[definition[0]].append(row)
            else:outside.append(row)
        areas=[]
        for key,title in AREAS.items():
            rows=buckets[key];groups={}
            for row in rows:
                c=row['check'];field=c.get('context',{}).get('event') or c.get('context',{}).get('document_type') or ''
                group=groups.setdefault(row['rule_id']+':'+field,{'title':REVIEW_RULES[row['rule_id']][1]+(' · '+field if field else ''),'check_ids':[],'statuses':[],'values':[]})
                group['check_ids'].append(c['check_id']);group['statuses'].append(row['status'])
                for value in values_for(c):
                    if value not in group['values']:group['values'].append(value)
            for group in groups.values():group['status']=combined(group.pop('statuses'))
            areas.append({'area':key,'title':title,'status':combined(r['status'] for r in rows),'groups':list(groups.values()),'check_ids':[r['check_id'] for r in rows if r['status']!='NOT_APPLICABLE']})
        if outside:areas.append({'area':'unmapped','title':'정의되지 않은 규칙 확인','status':'REVIEW','groups':[],'check_ids':[r['check_id'] for r in outside]})
        areas=[a for a in areas if a['status']!='NOT_APPLICABLE']
        counts=dict(Counter(a['status'] for a in areas));status=combined(a['status'] for a in areas)
        name=((tx.get('ledger') or {}).get('fields',{}).get('transaction_id') or {}).get('value') or '거래 '+str(i)
        allrows=[r for rows in buckets.values() for r in rows]+outside
        missing={}
        for r in allrows:
            if r['status']!='MISSING':continue
            c=r['check'];absent=[e for e in c.get('evidence',[]) if e.get('normalized_value') is None]
            for e in absent:
                source=e.get('source',{});identity=(str(source.get('entity_id')),e.get('field_name'),source.get('json_pointer',''))
                missing.setdefault(identity,{'field':e.get('field_name'),'source':source,'check_ids':[]})['check_ids'].append(c['check_id'])
            if not absent:missing[(c['check_id'],'','')]={'field':c.get('title'),'source':{},'check_ids':[c['check_id']]}
        transactions.append({'transaction_id':tx['transaction_id'],'title':name,'overall_status':status,'review_areas':areas,'counts':counts,'exceptions':[r['check_id'] for r in allrows if r['status'] in ('FAIL','REVIEW')],'missing_required':list(missing.values()),'not_applicable':[r['check_id'] for r in allrows if r['status']=='NOT_APPLICABLE'],'rule_results':[dict({k:v for k,v in r.items() if k!='check'},values=values_for(r['check'])) for r in allrows]})
    return {'version':VERSION,'transactions':transactions,'counts':dict(Counter(a['status'] for t in transactions for a in t['review_areas']))}

def summary(review):
    return '\n'.join(t['title']+' — '+LABELS[t['overall_status']]+'. 핵심 검토 영역 '+str(len(t['review_areas']))+'개: '+', '.join(LABELS[k]+' '+str(v) for k,v in t['counts'].items())+'.'+(' 필수 누락값 '+str(len(t['missing_required']))+'건은 추가 확인이 필요합니다.' if t['missing_required'] else '') for t in review['transactions'])
