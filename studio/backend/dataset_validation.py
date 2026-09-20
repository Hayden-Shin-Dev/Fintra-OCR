# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Independent evaluation against authored truth; never changes engine results or truth."""
from decimal import Decimal,InvalidOperation
import re

def equivalent(actual,expected):
    if actual is None or expected is None:return actual is expected
    try:return Decimal(str(actual).replace(',',''))==Decimal(str(expected).replace(',',''))
    except InvalidOperation:pass
    # Case/spacing and common piece notation are presentation differences, not inferred values.
    def norm(x):
        x=re.sub(r'\s+',' ',str(x).strip()).upper()
        return {'PC':'PCS','PIECE':'PCS','PIECES':'PCS','KGS':'KG','CARTON':'CTN','CARTONS':'CTN'}.get(x,x)
    return norm(actual)==norm(expected)

def evaluate(truth,result):
    audit=result.get('audit') or {};transactions=audit.get('transactions',[])
    docs={d['document_type']:d for d in result.get('ocr_documents',[])}
    extraction=[];unannotated=[]
    def field_check(dtype,path,expected,cell):
        correct=equivalent(cell.get('value'),expected) and (expected is None or cell.get('status')=='accepted')
        tokens=docs.get(dtype,{}).get('ocr',{}).get('tokens',[])
        text_present=expected is not None and any(str(expected).casefold() in t.get('text','').casefold() for t in tokens)
        cause=None if correct else 'document_classification_or_execution' if dtype not in docs else 'mapping' if text_present else 'ocr_or_mapping_needs_review'
        extraction.append({'document_type':dtype,'path':path,'expected':expected,'actual':cell.get('value'),'status':cell.get('status'),'correct':correct,'cause':cause,'expected_text_found_in_ocr':text_present,'mapping_null_reason':cell.get('null_reason'),'has_evidence':bool(cell.get('evidence'))})
    for dtype,source in truth['documents'].items():
        actual=docs.get(dtype,{})
        for name,cell in actual.get('fields',{}).items():
            if name not in source['fields'] and cell.get('value') is not None:
                unannotated.append({'document_type':dtype,'field':name,'value':cell['value'],'status':cell.get('status'),'evidence':cell.get('evidence',[]),'note':'Not a declared field in the authored document. Review whether this is a valid schema alias or a wrong semantic assignment; excluded from extraction recall denominator.'})
        for name,value in source['fields'].items():field_check(dtype,'fields.'+name,value,actual.get('fields',{}).get(name,{}))
        for i,row in enumerate(source['items']):
            candidates=[r for r in actual.get('items',[]) if equivalent(r.get('product_code',{}).get('value'),row['product_code'])]
            found=candidates[0] if len(candidates)==1 else {}
            for name,value in row.items():field_check(dtype,f"items[{row['product_code']}].{name}",value,found.get(name,{}))
    types={};codes={}
    for t in transactions:
        for dtype,d in t.get('documents',{}).items():
            types[d['id']]=dtype
            for row in d.get('items',[]):codes[row['id']]=row['fields'].get('product_code',{}).get('value')
        if t.get('ledger'):types[t['ledger']['id']]='ledger'
    for u in audit.get('unmatched_documents',[]):types[u['document']['id']]=u['document']['document_type']
    checks=[c for t in transactions for c in t.get('checks',[])]
    points=[p for t in transactions for p in t.get('audit_points',[])]+audit.get('unmatched_audit_points',[])
    def matches(expected,actual):
        if expected['type']!=actual['type']:return False
        context=actual.get('context',{})
        if expected.get('document_type') and expected['document_type']!=context.get('document_type'):return False
        if expected.get('documents'):
            observed=actual.get('documents') or [types.get(x,x) for x in context.get('documents',[])]
            if set(expected['documents'])!=set(observed):return False
        if expected.get('product_code') and expected['product_code'] not in {codes.get(x) for x in context.get('items',[])}:return False
        return True
    checked=[]
    for expected in truth['expected_checks']:
        candidates=[c for c in checks if matches(expected,c)]
        checked.append({'expected':expected,'actual_statuses':[c['status'] for c in candidates],'correct':bool(candidates) and all(c['status']==expected['status'] for c in candidates)})
    remaining=list(points);matched=[];missing=[]
    for expected in truth['expected_audit_points']:
        p=next((p for p in remaining if matches(expected,p) and p['status']==expected['status']),None)
        if p is None:missing.append(expected)
        else:remaining.remove(p);matched.append(expected)
    linked=any(t.get('ledger') and set(t.get('documents',{}))==set(truth['documents']) for t in transactions) and not audit.get('unmatched_documents')
    matching_correct=linked if truth['expected_matching'] else not linked and any(c['type']=='transaction_link_review' and c['status']=='review' for c in checks)
    measured=[x for x in extraction if x['expected'] is not None]
    tp=len(matched);fp=len(remaining);fn=len(missing)
    return {'transaction_id':truth['transaction_id'],'label':truth['label'],'data_kind':'synthetic_functional_test','expected_matching':truth['expected_matching'],'actual_all_submitted_documents_linked':linked,'matching_correct':matching_correct,
        'metrics':{'extraction_correct':sum(x['correct'] for x in measured),'extraction_total':len(measured),'extraction_success_rate':sum(x['correct'] for x in measured)/len(measured) if measured else None,'checks_correct':sum(x['correct'] for x in checked),'checks_total':len(checked),'check_accuracy':sum(x['correct'] for x in checked)/len(checked) if checked else None,'audit_point_tp':tp,'audit_point_fp':fp,'audit_point_fn':fn,'audit_point_precision':tp/(tp+fp) if tp+fp else None,'audit_point_recall':tp/(tp+fn) if tp+fn else None},
        'evaluation_version':'1.1','unannotated_non_null_fields':unannotated,'expected_audit_points':truth['expected_audit_points'],'missing_audit_points':missing,'unexpected_audit_points':remaining,'check_comparison':checked,'extraction_comparison':extraction,
        'all_declared_expectations_met':matching_correct and all(x['correct'] for x in extraction) and all(x['correct'] for x in checked) and fp==0 and fn==0,
        'failure_attribution':'Inspect extraction_comparison first. Wrong or missing source cells are OCR/mapping failures; checks with correct source cells are matching/comparison failures. Missing optional fields are not treated as successful extraction.'}
