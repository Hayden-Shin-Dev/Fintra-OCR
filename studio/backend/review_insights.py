# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Immediate conditional audit guidance, tied to actual check types and evidence."""
from audit_research import topic_for
GUIDANCE={
 'amount':('정확성·평가','실제 장부 오류라면 매출·채권 또는 재고·채무의 금액이 잘못 표시될 수 있습니다.','송장 합계와 장부의 세금·운임·할인 포함 범위를 맞추고 차이 조정표를 확인하세요.'),
 'quantity':('실재성·정확성','실제 인수 수량과 기록이 다르면 재고와 매출원가의 검토가 필요합니다. 문서 차이가 곧 실물 부족은 아닙니다.','같은 품목·단위·선적 범위인지 확인하고 입출고·검수·반품 기록과 대조하세요.'),
 'date':('기간귀속','인도·이행 시점과 기장 기간이 다르면 매출·매입 또는 재고의 기간귀속을 검토해야 합니다.','발행일·선적일·검수일을 구분하고 계약의 인도 조건 및 실제 이행 증빙을 확인하세요.'),
 'currency':('정확성·평가','거래 통화와 기록 통화 또는 환산 기준이 다르면 관련 계정의 평가를 검토해야 합니다.','통화·거래일·환율 출처와 환산 내역을 확인하세요. 다른 통화끼리 차감하지 않습니다.'),
 'identity':('실재성·거래 연결','다른 거래의 증빙이 연결됐다면 현재 비교 결과를 해당 거래의 근거로 사용할 수 없습니다.','계약·발주서와 공통 참조번호, 분할 선적·정정 이력으로 연결 관계를 확인하세요.'),
 'other':('증거의 적합성','문서 차이가 거래의 실제 내용에 영향을 주는지 확인해야 합니다.','원본 항목의 의미와 비교 범위, 관련 계약·증빙을 먼저 대조하세요.')}

def insight(check):
    if check.get('status') not in {'flag','review'}:return None
    topic=topic_for(check);assertion,impact,action=GUIDANCE[topic]
    return {'topic':topic,'assertion':assertion,'impact':impact,'action':action,
            'basis':'conditional_audit_guidance','check_id':check['check_id']}

def quick_risk(question,checks,framework,request):
    import re
    # Only unambiguous general risk questions bypass semantic routing. Specific
    # concepts and follow-ups still use the full conversational RAG pipeline.
    q=re.sub(r'[\s?!.,]','',question)
    if not re.fullmatch(r'(?:지금|현재|이|해당|거래|불일치|부분|건|결과|의|에|대해|대한|에서|대한|어떤|무슨)*(?:리스크|위험)(?:가|이|는|을|를|뭐야|무엇이야|있어|있나요|알려줘|알려주세요|설명해줘|설명해주세요|설명|해줘)*',q):return None
    selected=[c for c in checks if c.get('status') in {'flag','review'}]
    if not selected:return None
    from amount_assistance import amount_risk
    if all(topic_for(c)=='amount' for c in selected):
        answer=amount_risk(selected,framework,request)
        if answer:return answer
    from grounded_chat import describe
    blocks=[];citations=[]
    for c in selected:
        row=insight(c)
        text=describe(c)+'\n\n검토할 위험 · '+row['assertion']+'\n'+row['impact']+'\n\n다음 확인\n'+row['action']
        blocks.append({'kind':'risk','text':text,'citation_ids':[c['check_id']]})
        citations.append({'id':c['check_id'],'kind':'check','title':c['title'],'check':c})
    return {'answer':'\n\n'.join(b['text'] for b in blocks),'citations':citations,'assistance':{'blocks':blocks,'validation':'typed_conditional_review_guidance'},'grounding_status':'conditional_audit_guidance'}
