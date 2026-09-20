# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Read-only report appendix built from the saved audit, never from model prose."""
from pathlib import Path
from collections import Counter
from grounded_chat import STATUS, FIELDS
from comparison_scope import scope_for

KINDS={'commercial_invoice':'상업송장','packing_list':'포장명세서','bill_of_lading':'선하증권','ledger':'장부'}

def display_title(text):
    for key,label in sorted({**FIELDS,**KINDS}.items(),key=lambda x:-len(x[0])):text=text.replace(key,label)
    return text

def format_value(value):
    import re
    text=str(value)
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?',text):
        integer,dot,fraction=text.partition('.')
        return format(int(integer),',')+(dot+fraction if dot else '')
    return text

def facts_for(result):
    from review_rules import normalized_audit,build,rule_status
    audit=normalized_audit(result.get('audit') or {}); review=build(audit); transactions=[]
    records={r.get('result_file'):r for r in result.get('documents',[])}
    for number,tx in enumerate(audit.get('transactions',[]),1):
        entities={d['id']:d.get('document_type') for d in tx.get('documents',{}).values()}
        checks=[]
        for check in tx.get('checks',[]):
            values=[];evidence=[]
            for e in check.get('evidence',[]):
                src=e.get('source') or {};original=e.get('original');obj=original if isinstance(original,dict) else {}
                kind='ledger' if 'row_index' in src else entities.get(src.get('entity_id'))
                label=KINDS.get(kind,kind or '증빙')+' · '+FIELDS.get(e.get('field_name'),e.get('field_name','항목'))
                value=e.get('normalized_value');values.append({'label':label,'value':format_value(value) if value is not None else '정보 없음'})
                record=records.get(Path(src.get('file','')).name,{})
                location='행 '+str(src['row_index'])+' · 열 '+str(src.get('original_column','')) if 'row_index' in src else src.get('json_pointer','')
                evidence.append({'label':label,'file':record.get('name') or record.get('original_name') or Path(src.get('file','')).name,'location':location,'raw_text':str(obj.get('raw_text') or (original if not isinstance(original,dict) and original is not None else '')),'tokens':obj.get('evidence',[]),'human_reviewed':bool(obj.get('human_review'))})
            checks.append({'id':check['check_id'],'title':display_title(check.get('title',check.get('type',''))),'status':check['status'],'reason':check.get('reason',''),'reason_text':{'required_value_missing':'비교에 필요한 값이 문서에서 확인되지 않았습니다.','different_values':'비교한 값이 서로 다릅니다.'}.get(check.get('reason'),'') ,'values':values,'difference':check.get('values',{}).get('difference'),'unit':check.get('context',{}).get('comparison_unit') or '', 'evidence':evidence})
        for check,source_check in zip(checks,tx.get('checks',[])):
            check['coverage_scope']=scope_for(source_check,tx)
            check['review_status']=rule_status(source_check,tx)
        display=((tx.get('ledger') or {}).get('fields',{}).get('transaction_id') or {}).get('value') or '거래 '+str(number)
        transactions.append({'title':display,'checks':checks,'counts':dict(Counter(c['status'] for c in checks))})
    return {'review_result':review,'transactions':transactions,'document_count':len(result.get('documents',[])),'unmatched_count':len(audit.get('unmatched_documents',[])),'counts':dict(Counter(c['status'] for t in transactions for c in t['checks']))}


def report_facts(folder):
    import json
    folder=Path(folder)
    facts=facts_for(json.loads((folder/'result.json').read_text('utf-8')))
    facts['references']=[]
    return facts
