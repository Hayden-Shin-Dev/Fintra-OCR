# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Route explicit requests to bounded tools; no report HTML is used as context."""
import re,time
from review_rules import build,summary

def route(question):
    q=re.sub(r'\s+','',question)
    current=bool(re.search(r'TX\d+|관련|현재|이번|이거래|검토항목|이결과|원본|송장|장부|포장명세서|선하증권',q,re.I))
    standards=bool(re.search(r'K-?IFRS|K-?GAAP|회계기준|회계원칙|일반기업회계기준',q,re.I))
    if standards:return 'transaction_standard' if current else 'accounting_standard'
    if not current and re.search(r'매출채권|매입채무|매출인식|재고자산|감모손실|발생주의',q) and re.search(r'뭐|무엇|뜻|개념',q):return 'general_concept'
    if re.search(r'리스크|위험|회계처리|원칙|기준|분개|영향|초안|자료.*요청',q):return 'analysis'
    if current and re.search(r'얼마|어디|누구|언제|왜|정상|문제|일치|결과|보여|알려',q):return 'transaction'
    return None

def respond(question,audit,context,history,model,search):
    mode=route(question)
    if mode is None or mode in ('analysis','transaction_standard'):return None
    started=time.monotonic()
    def reply(text,citations=(),blocks=()):return {'answer':text,'citations':list(citations),'assistance':{'blocks':list(blocks)},'selection':{'intent':mode,'tools':{'transaction':['review_result','evidence_store'],'general_concept':['language_model'],'accounting_standard':['standards_search','language_model']}[mode]},'grounding_status':'retrieved_evidence_with_reviewed_assistance' if blocks else 'extractive_evidence_selection' if citations else 'general_knowledge','seconds':time.monotonic()-started}
    if mode=='general_concept':
        from accounting_glossary import lookup
        entry=lookup(question)
        if entry:return reply('일반 개념 설명\n'+entry)
        value=model('회계 용어의 일반적인 뜻을 한국어 2~3문장으로 설명하세요. 사용자의 거래를 판단하거나 특정 기준서 문단·조항 번호를 만들지 마세요. 일반 개념 설명임을 명시하세요.',{'question':question},{'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False})
        return reply('일반 개념 설명\n'+value['answer'])
    if mode=='accounting_standard':
        from audit_research import retrieve
        from knowledge_answer import compose
        refs,trace=retrieve(question,[],context.get('framework'),search,model)
        if not refs:return reply('질문에 직접 대응하는 기준서 원문을 찾지 못했습니다. 적용 기준(K-IFRS 또는 일반기업회계기준)과 확인할 주제를 구체적으로 알려주세요.')
        result=compose(question,history,refs,model);blocks=result.get('blocks',[])
        if not blocks:return reply('질문에 대한 해설 검증을 완료하지 못했습니다. 검색된 원문을 확인해 주세요.\n\n'+'\n\n'.join(r['title']+'\n'+(r.get('relevant_text') or r['quote']) for r in refs),refs)
        used={k for b in blocks for k in b.get('citation_ids',[])}
        return reply('\n\n'.join(b['text'] for b in blocks),[r for r in refs if r['id'] in used],blocks)
    # The server passes only the selected transaction, never another user's/report's data.
    if context.get('stage') in {'upload','queued','ocr','ocr_mapping','awaiting_review','review','audit','linking'}:return None
    if not audit.get('transactions'):return reply('현재 단계에는 비교 결과가 없습니다. 추출값 확인을 마친 뒤 거래 비교를 시작하면 실제 결과를 설명할 수 있습니다.')
    if context.get('stage') in {'upload','ocr','awaiting_review','review','audit'}:return None
    from grounded_chat import describe
    fields={'금액':{'amount','total_amount'},'총액':{'amount','total_amount'},'거래처':{'buyer','seller','counterparty'},'통화':{'currency'},'선적일':{'shipment_date'},'거래일':{'transaction_date','issue_date'},'수량':{'quantity'}}
    wanted=set().union(*(v for k,v in fields.items() if k in question)) if any(k in question for k in fields) else set()
    review=build(audit)
    if not wanted and re.search(r'정상|문제|결과',question):
        ids={cid for t in review['transactions'] for cid in t['exceptions']}|{cid for t in review['transactions'] for m in t['missing_required'] for cid in m['check_ids']}
        issues=[c for t in audit['transactions'] for c in t.get('checks',[]) if c['check_id'] in ids]
        citations=[{'id':c['check_id'],'kind':'check','title':c.get('title','확인 항목'),'check':c} for c in issues]
        return reply(summary(review)+('\n\n'+'\n\n'.join(dict.fromkeys(describe(c) for c in issues)) if issues else ''),citations)
    if not wanted:return None
    checks=[c for t in audit['transactions'] for c in t.get('checks',[]) if any(e.get('field_name') in wanted for e in c.get('evidence',[]))]
    docnames={'상업송장':'commercial_invoice','송장':'commercial_invoice','포장명세서':'packing_list','선하증권':'bill_of_lading','B/L':'bill_of_lading'}
    target=next((v for k,v in docnames.items() if k in question),None)
    labels={d['id']:{'commercial_invoice':'상업송장','packing_list':'포장명세서','bill_of_lading':'선하증권'}.get(k,k) for t in audit['transactions'] for k,d in t.get('documents',{}).items()}
    if not checks:return reply('현재 거래에서 질문하신 항목의 비교 근거를 찾지 못했습니다. 문서 종류와 항목명을 확인해 주세요.')
    citations=[{'id':c['check_id'],'kind':'check','title':c.get('title','비교 근거'),'check':c} for c in checks]
    return reply('\n\n'.join(dict.fromkeys(describe(c,labels) for c in checks))+'\n\n저장된 값·단위·비교 범위에 대한 결과이며 회계처리 전체의 적정성을 판정한 것은 아닙니다.',citations)
