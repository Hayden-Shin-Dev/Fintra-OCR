# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Read-only presentation indexes over engine results. No comparisons or findings."""
import hashlib,json
from comparison_scope import coverage,scope_for
from review_insights import insight
from pathlib import Path

def transaction_state(transaction):
    states={c['status'] for c in transaction.get('checks',[]) if scope_for(c,transaction)!='supplementary'}
    if states & {'flag','review'} or transaction.get('matching',{}).get('status') in {'review','unmatched'}:return 'review'
    if 'cannot_evaluate' in states or not states:return 'cannot_evaluate'
    return 'pass'

def enrich(result,job):
    from review_rules import normalized_audit,build
    if result.get('audit'):
        result['audit']=normalized_audit(result['audit'])
        result['review_result']=build(result['audit'])
    result['documents']=job.get('document_records',[])
    result['failures']=job.get('failures',[])
    result['upload_files']=job.get('files',[])
    review=result.get('standards_review')
    result['extensions']={'standards':{'enabled':review is not None},'explanation':{'enabled':review is not None}}
    result['explanation_llm']=any(f.get('explanation',{}).get('model_called',False) for f in (review or {}).get('findings',[]))
    byfile={name:d for d in result['documents'] for name in (d.get('stored'),d.get('result_file')) if name}
    types={};entity_documents={}
    audit=result.get('audit') or {}
    all_entities=[]
    for t in audit.get('transactions',[]):
        all_entities+=list(t.get('documents',{}).values())
    all_entities+=[u['document'] for u in audit.get('unmatched_documents',[])]
    for entity in all_entities:
        record=byfile.get(Path(entity.get('source',{}).get('file','')).name)
        if record:entity_documents[entity['id']]=record['id'];types[entity['id']]=entity['document_type']
    index={}
    def register(e):
        eid='e-'+hashlib.sha256(json.dumps(e,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        source=e.get('source',{});docid=entity_documents.get(source.get('entity_id'))
        record=next((d for d in result['documents'] if d['id']==docid),None)
        index[eid]={'id':eid,'evidence':e,'document_id':docid,'document_type':types.get(source.get('entity_id'),'ledger' if 'row_index' in source else None),
                    'image_pages':sorted((record or {}).get('images',{}))}
        return eid
    links={}
    for t in audit.get('transactions',[]):
        for c in t.get('checks',[]):links[c['check_id']]=[register(e) for e in c.get('evidence',[])]
        for p in t.get('audit_points',[]):links[p['audit_point_id']]=[register(e) for e in p.get('evidence',[])]
    for p in audit.get('unmatched_audit_points',[]):links[p['audit_point_id']]=[register(e) for e in p.get('evidence',[])]
    states={t['transaction_id']:transaction_state(t) for t in audit.get('transactions',[])}
    result['presentation']={'transaction_states':states,'entity_documents':entity_documents,'evidence_links':links,
                            'coverage':{t['transaction_id']:coverage(t) for t in audit.get('transactions',[])},
                            'insights':{c['check_id']:insight(c) for t in audit.get('transactions',[]) for c in t.get('checks',[]) if c.get('status') in {'flag','review'}},
                            'summary':{s:sum(v==s for v in states.values()) for s in ('pass','review','cannot_evaluate')},
                            'state_basis':'Flags and reviews take priority. Required missing values block coverage. Supplementary absent fields stay visible without marking the transaction incomplete. Individual checks are unchanged.'}
    result['evidence_index']=index
    return result
