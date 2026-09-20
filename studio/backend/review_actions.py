# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Immediate generic review actions assembled from the current case, not a model guess."""
import re

def respond(question, transactions):
    q=re.sub(r'[\s?!？.!]','',question)
    intent={'어떤순서로검토하면좋을까':'procedure','이거래에서어떤순서로검토하면좋을까':'procedure',
            '이결과로검토메모초안을써줘':'draft','담당자에게요청할자료와질문을작성해줘':'documents','담당자에게어떤자료를요청해야해':'documents'}.get(q)
    if not intent:
        if re.fullmatch(r'(?:이거래|현재결과|이결과|현재거래|담당자|담당자에게|지금|그럼|의|에|에서|는|를|을|관련|추가|필요한|어떤|무슨|확인할|할|좀|먼저|어떻게|어떤순서로|순서|검토|자료|증빙|요청|메모|초안|작성|써|만들어|해|줘|해야|하나요|좋을까|알려|목록|질문|와|과|해줘)+',q):
            if re.search('자료|증빙',q):intent='documents'
            elif re.search('메모|초안',q):intent='draft'
            elif re.search('순서|먼저',q):intent='procedure'
    if not intent:return None
    from comparison_scope import coverage
    from grounded_chat import describe
    from audit_research import topic_for
    from logistics_writer import PROGRAMS
    citations=[];paragraphs=[]
    for tx in transactions:
        required=set(coverage(tx)['required_missing_ids'])
        checks=[c for c in tx.get('checks',[]) if c['status'] in ('flag','review') or c['check_id'] in required]
        title=str(((tx.get('ledger') or {}).get('fields',{}).get('transaction_id') or {}).get('value') or '선택한 거래')
        if not checks:
            paragraphs.append(title+': 현재 필수 비교 범위에서 추가 확인 항목이 발견되지 않았습니다. 원본 진위, 계약 조건, 분개 및 기간귀속의 검토까지 완료됐다는 뜻은 아닙니다.')
            continue
        paragraphs.append(title+' · '+('검토 메모 초안' if intent=='draft' else '우선 검토할 항목'))
        topics={}
        for c in checks:
            citations.append({'id':c['check_id'],'kind':'check','title':c.get('title','검토 항목'),'check':c})

            if intent!='documents':paragraphs.append(describe(c))
            topics.setdefault(topic_for(c),[]).append(c)
        for topic in topics:
            assertions,subject,program=PROGRAMS.get(topic,PROGRAMS['other'])
            if intent=='documents':
                paragraphs.append(subject+' 확인을 위해 담당자에게 아래 자료를 요청해 주세요.\n'+'\n'.join(f'{i+1}. 요청 자료: {document}\n담당자에게 보낼 질문: 이 자료로 문서 차이의 원인을 확인할 수 있도록 정정·분할 처리 내역과 관련 근거를 보내주시겠어요? 확인할 사항: {action}' for i,(document,action,completion) in enumerate(program)))
                continue
            paragraphs.append(subject+' · '+assertions+'\n'+'\n'.join(f'{i+1}. {action} 확인 자료: {document}. 완료 근거: {completion}.' for i,(document,action,completion) in enumerate(program)))
        paragraphs.append('위 절차는 아직 수행하지 않은 검토 계획입니다. 차이 원인과 분개 영향을 확정하지 않았으며, 자료 입수 후 차이 조정 내역과 검토 결론을 기록해야 합니다.')
    text='\n\n'.join(paragraphs)
    block={'kind':'draft' if intent=='draft' else 'request' if intent=='documents' else 'procedure','text':text,'condition':'','citation_ids':[c['id'] for c in citations]}
    return {'answer':text,'citations':citations,'assistance':{'blocks':[block],'validation':'owned_facts_and_versioned_procedures'},'selection':{'intent':intent,'method':'current_case_review_actions'},'grounding_status':'owned_facts_and_versioned_procedures'}
