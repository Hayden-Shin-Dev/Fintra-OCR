# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Independent owned-data tools and a bounded, metadata-filtered standards retriever."""
import re,time,math
from collections import Counter
from review_rules import build
from standards_metadata import matches,metadata

ALIASES={'amount':r'금액|총액|얼마|USD|통화','counterparty':r'거래처|구매자|판매자','date':r'거래일|기장일','references':r'번호|참조','shipping':r'선적|출항','logistics':r'중량|포장\s*개수','items':r'수량|품목|제품','documents':r'필수\s*증빙|문서\s*존재'}
FIELDS={'currency':r'통화','total_amount':r'총액|금액','amount':r'장부\s*금액','quantity':r'수량','gross_weight':r'총중량','net_weight':r'순중량','invoice_number':r'송장\s*번호','unit_price':r'단가','shipment_date':r'선적일','buyer':r'구매자','seller':r'판매자','purchase_order_number':r'주문\s*번호'}

def scoped(audit, transaction_id=None, name=None):
    rows=audit.get('transactions',[])
    if transaction_id:rows=[t for t in rows if t['transaction_id']==transaction_id]
    if name:rows=[t for t in rows if str(((t.get('ledger') or {}).get('fields',{}).get('transaction_id') or {}).get('value','')).upper()==name]
    return dict(audit,transactions=rows)

def transaction_lookup(review,question):
    """Only the ReviewResult contract is accepted; no report or raw checks."""
    unsupported=re.search(r'적용\s*환율|기능통화|환차손익|은행\s*계좌|담당자\s*이름|실제\s*입금|지급\s*완료|세금계산서\s*승인',question)
    if unsupported:return {'transactions':[],'unavailable_field':unsupported[0],'source':'ReviewResult'}
    wanted=[key for key,rx in ALIASES.items() if re.search(rx,question,re.I)]
    issue=bool(re.search(r'누락|정보\s*부족|불일치|차이|리스크|위험|자료|메모|순서',question))
    out=[]
    for tx in review.get('transactions',[])[:5]:
        areas=[a for a in tx['review_areas'] if (not wanted or a['area'] in wanted)]
        if issue and not wanted:areas=[a for a in areas if a['status']!='PASS'] or areas
        groups=[]
        for area in areas:
            for group in area['groups']:
                if group['status']=='NOT_APPLICABLE':continue
                if issue and group['status']=='PASS':continue
                rule_rows=[r for r in tx.get('rule_results',[]) if r['check_id'] in group['check_ids'] and (not issue or r['status'] in ('FAIL','MISSING','REVIEW'))]
                source_values=[v for r in rule_rows for v in r.get('values',[])] or group.get('values',[])
                values=[]
                for v in source_values:
                    value={'field':v['field'],'value':v['value'],'source':{'document_type':v.get('document_type'),'entity_id':v.get('entity_id'),'json_pointer':v.get('source',{}).get('json_pointer')}}
                    if value not in values:values.append(value)
                groups.append({'title':group['title'],'status':group['status'],'values':values[:8],'check_ids':[r['check_id'] for r in rule_rows][:3] or group['check_ids'][:3]})
        out.append({'transaction_id':tx['transaction_id'],'title':tx['title'],'overall_status':tx['overall_status'],'no_confirmed_mismatch':bool('불일치' in question and not tx['counts'].get('FAIL')),
            'areas':[{'title':a['title'],'status':a['status']} for a in areas], 'groups':groups[:8],
            'missing_required':tx['missing_required'][:5], 'counts':tx['counts']})
    return {'transactions':out,'truncated':len(review.get('transactions',[]))>5,'source':'ReviewResult'}

def evidence_lookup(audit,context,question):
    from pathlib import Path
    allowed=set()
    for tx in audit.get('transactions',[]):
        for doc in (tx.get('documents') or {}).values():
            if isinstance(doc,dict):allowed.add(doc.get('id'))
        if tx.get('ledger'):allowed.add(tx['ledger'].get('id'))
    docs=context.get('documents',[])
    # In OCR there is no transaction yet; only the current server-owned analysis is read.
    if audit.get('transactions'):
        owned_docs={d['id']:d for tx in audit['transactions'] for d in (tx.get('documents') or {}).values() if isinstance(d,dict)}
        linked=[]
        for doc in owned_docs.values():
            basename=Path((doc.get('source') or {}).get('file','')).name
            ui=next((d for d in docs if d.get('id')==doc['id'] or (basename and d.get('result_file')==basename)),{})
            def cells(row):
                return {k:{'value':c.get('value'),'status':c.get('status'),'raw_text':(c.get('evidence',{}).get('original') or {}).get('raw_text')} for k,c in row.items() if isinstance(c,dict)}
            linked.append({'id':ui.get('id',doc['id']),'name':ui.get('name',doc.get('document_type')),'document_type':doc.get('document_type'),'fields':cells(doc.get('fields',{})),'items':[cells(r.get('fields',r)) for r in doc.get('items',[])]})
        docs=linked
    elif context.get('comparison_available'):docs=[]
    kind=next((k for word,k in [('포장명세','packing_list'),('선하증권','bill_of_lading'),('송장','commercial_invoice'),('장부','ledger')] if word in question),None)
    if kind:docs=[d for d in docs if d.get('document_type')==kind]
    elif context.get('selected_document_id'):docs=[d for d in docs if d['id']==context['selected_document_id']]
    keys=[k for k,rx in FIELDS.items() if re.search(rx,question)]
    if 'quantity' in keys:keys+=['unit','product_code']
    if 'total_amount' in keys:keys+=['currency']
    result=[]
    for doc in docs[:3]:
        cells=[]
        for key,cell in doc.get('fields',{}).items():
            if context.get('_evidence_minimal') and not keys:continue
            if keys and key not in keys:continue
            cells.append({'field':key,'value':cell.get('value'),'raw_text':cell.get('raw_text'),'status':cell.get('status'),'pointer':'/fields/'+key})
        if keys:
            for i,row in enumerate(doc.get('items',[])):
                for key in keys:
                    if key in row:cells.append({'field':key,'value':row[key].get('value'),'raw_text':row[key].get('raw_text'),'status':row[key].get('status'),'pointer':f'/items/{i}/{key}'})
        result.append({'id':doc['id'],'name':doc.get('name'),'type':doc.get('document_type'),'fields':cells[:12],'truncated':len(cells)>12})
    return {'documents':result,'source':'original_document_extraction'}

def tokens(s):
    words=re.findall(r'[a-z0-9]+|[가-힣]+',s.lower())
    return words+[w[i:i+2] for w in words if re.fullmatch('[가-힣]+',w) for i in range(len(w)-1)]

def rerank(query,candidates,limit=4):
    """Second-stage query/heading/passage lexical coverage + dense score, deduplicated."""
    wanted=set(tokens(query));out=[];seen=set()
    for s in candidates:
        identity=s.get('id')
        if identity in seen:continue
        seen.add(identity)
        body=set(tokens(s.get('text','')));heading=set(tokens(s.get('title','')))
        overlap=len(wanted&body)/max(1,len(wanted));title=len(wanted&heading)/max(1,len(wanted))
        cosine=float((s.get('scores') or {}).get('cosine') or 0)
        score=overlap*.6+title*.3+cosine*.1
        if not wanted&body and not wanted&heading:continue
        out.append(dict(s,rerank_score=score))
    return sorted(out,key=lambda s:(-s['rerank_score'],s.get('id','')))[:min(5,max(1,limit))]

def standard_lookup(question,framework=None,filters=None,request=None):
    from kasb_kb import exact_lookup
    exact=exact_lookup(question)
    if exact is not None:return exact
    if request is None:
        from enrichment import request
    t=time.perf_counter();filters=dict(filters or {})
    if re.search(r'K\s*-?\s*IFRS',question,re.I):framework='K-IFRS'
    elif re.search(r'K\s*-?\s*GAAP|일반기업회계기준',question,re.I):framework='일반기업회계기준'
    code=re.search(r'(?:제\s*|IFRS\s*[- ]?)(\d{4})',question,re.I)
    if code:filters['standard_id']=code[1]
    elif 'standard_id' not in filters and (framework or 'K-IFRS')=='K-IFRS':
        topics=[(r'재고|감모|취득원가','1002'),(r'수익|매출\s*인식','1115'),(r'현금흐름','1007'),(r'선지급|선수취','2122'),(r'환율|외화환산','1021')]
        ids=[code for pattern,code in topics if re.search(pattern,question)]
        if ids:filters['standard_id']=ids
    para=re.search(r'문단\s*(\d+[A-Za-z]?)',question)
    if para:filters['paragraph']=para[1]
    if (framework or 'K-IFRS')=='K-IFRS':
        from kasb_search import search as official_search
        official=official_search(question,filters)
        if official['passages']:return official
    data=request('/search',{'query':question[:700],'top_k':20,'framework':framework or 'K-IFRS','source_types':['회계기준'],'method':'hybrid','metadata_filters':filters,'policy_version':'chat-v2.2'})
    candidates=[s for s in data.get('results',[]) if s.get('source_type')=='회계기준' and matches(s,filters) and re.match(r'^(?:K\s*-?\s*IFRS|일반\s*기업\s*회계\s*기준|중소\s*기업\s*회계\s*기준)',s.get('title',''),re.I)]
    retrieval=time.perf_counter()-t;t=time.perf_counter();ranked=rerank(question,candidates)
    elapsed=time.perf_counter()-t
    # Preserve provenance and actual paragraph text; never invent a paragraph number.
    def passage(s):
        text=s.get('text','')
        text=re.sub(r'관련 질의회신요약.*?(?=\n\s*\d{1,3}[A-Z]?\s*\n|\Z)','',text,flags=re.S)
        if para:
            match=re.search(r'(?:^|\n)\s*'+re.escape(para[1])+r'\s*\n(.*?)(?=\n\s*(?:[A-Z]{1,3})?\d{1,3}[A-Z]?\s*\n|\Z)',text,re.S)
            if match:text='문단 '+para[1]+'\n'+match[1]
        return text[:1800]
    passages=[{'id':s['id'],'title':s.get('title'),'text':passage(s), 'metadata':metadata(s),'source':s.get('source'), 'source_type':'internal_accounting_case','framework':s.get('framework'),'score':s['rerank_score']} for s in ranked]
    return {'passages':passages,'retrieval_seconds':retrieval,'reranking_seconds':elapsed,'candidate_count':len(candidates),'filters':filters,'method':data.get('retrieval',{}).get('method')}
