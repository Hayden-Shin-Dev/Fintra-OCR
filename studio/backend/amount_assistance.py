# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Amount-comparison interpretation with deterministic facts and scoped retrieval.

Rules apply to check semantics, never demo transaction IDs or sample amounts.
No ledger entry or Audit decision is changed.
"""
from decimal import Decimal, InvalidOperation
import re

AMOUNT_TYPE='ledger_invoice_amount_comparison'

def citation(c):
    return {'id':c['check_id'],'kind':'check','title':c.get('title','금액 비교'),'check':c}

def explain_basis(checks,plan,seconds):
    related=[c for c in checks if c.get('type')==AMOUNT_TYPE or 'amount_basis' in c.get('type','')]
    text=('“장부 금액이 송장 최종 총액”이라는 선택은 CSV의 금액 칸이 송장의 최종 청구액과 같은 범위의 금액이라는 뜻입니다. '
          '금액이 같다고 입력하는 설정이 아니라, 서로 비교해도 되는 금액인지 확인하는 설정입니다.\n\n'
          '장부에는 공급가액만 있고 송장에는 세금·운임 등이 포함되어 있거나, 장부가 원화 환산액·일부 결제액이면 바로 같은 금액으로 비교할 수 없습니다. '
          '송장 합계와 장부 금액의 세금·비용 포함 범위, 통화, 거래 범위를 먼저 확인하세요.\n\n'
          '숫자가 같아도 이 비교 기준을 확인하지 않았다면 검토 필요로 남을 수 있습니다. '
          '실제로 같은 범위의 최종 총액인 경우에만 해당 설정을 선택하세요. 이는 거래의 회계처리가 적정하다는 확인은 아닙니다.')
    return {'answer':text,'citations':[citation(c) for c in related[:2]],'assistance':{'blocks':[]},'selection':plan,'seconds':seconds,'grounding_status':'platform_context'}

def eligible(source,topic,framework):
    if source.get('source_type')!='회계기준':return False
    normalize=lambda v:re.sub(r'[\s-]','',str(v)).upper()
    if normalize(source.get('framework'))!=normalize(framework):return False
    title=source.get('title','');body=source.get('text','')
    if topic=='revenue':
        return ('1115' in title or '제16장 수익' in title) and ('거래가격을 산정' in body or '수익의 측정' in body) and ('받을' in body or '권리' in body)
    return ('재고자산' in title) and '매입원가' in body and ('할인' in body or '매입금액' in body or '매입가격' in body)

def retrieve_principles(framework,request):
    chosen=framework or 'K-IFRS';citations=[];failures=[]
    for topic,query in [('revenue','수익 거래가격 측정'),('inventory','재고자산 매입원가 할인')]:
        try:rows=request('/search',{'query':query,'top_k':20,'framework':chosen}).get('results',[])
        except Exception as exc:
            failures.append(type(exc).__name__);continue
        source=next((s for s in rows if eligible(s,topic,chosen)),None)
        if source:
            citations.append({'id':source['id'],'kind':'standard','title':source['title'],'source':source,'quote':source['text'],
                              'source_char_start':source['source']['char_start'],'source_char_end':source['source']['char_end'],
                              'applicability':'conditional','required_conditions':['적용 회계기준 확인','매출 거래 여부 확인' if topic=='revenue' else '재고 매입 거래 여부 확인'],'topic':topic})
    return chosen,citations,failures

def amount_risk(checks,framework,request):
    relevant=[c for c in checks if c.get('type')==AMOUNT_TYPE and c.get('status')=='flag']
    if not relevant:return None
    chosen,standards,failures=retrieve_principles(framework,request)
    blocks=[];refs=[citation(c) for c in relevant]+standards
    for c in relevant:
        values={e.get('field_name'):e.get('normalized_value') for e in c.get('evidence',[])}
        try:ledger=Decimal(str(values['amount']));invoice=Decimal(str(values['total_amount']))
        except (KeyError,InvalidOperation):continue
        if not ledger.is_finite() or not invoice.is_finite():continue
        delta=ledger-invoice;unit=c.get('context',{}).get('comparison_unit') or values.get('currency') or ''
        direction='크게' if delta>0 else '작게'
        blocks.append({'kind':'explanation','text':f'장부 {ledger:,.2f} {unit}, 송장 {invoice:,.2f} {unit}로, 장부가 {abs(delta):,.2f} {unit} 더 {"큽니다" if delta>0 else "작습니다"}. 핵심 위험은 이 차이가 실제 장부 오류라면 거래 금액과 관련 계정이 잘못 표시될 수 있다는 점입니다.','citation_ids':[c['check_id']]})
        blocks.append({'kind':'risk','condition':'같은 거래·통화·세금 및 비용 범위이고, 송장이 올바른 금액이며 장부 기록이 잘못된 경우',
                       'text':f'매출 거래라면 매출·매출채권 등 관련 계정이 실제보다 {direction} 기록됐을 가능성을 검토합니다. 재고 매입 거래라면 재고자산·매입채무 등의 금액이 잘못 기록됐을 가능성을 검토합니다. 어떤 계정과 손익에 영향이 있는지는 실제 분개와 재고 판매 여부를 확인해야 합니다. 문서 차이만으로 손실이나 부정을 확정할 수는 없습니다.',
                       'citation_ids':[c['check_id']]})
    if not blocks:return None
    for s in standards:
        text=('계약상 받을 대가와 거래가격을 확인하는 데 사용하는 기준입니다. 송장의 청구 총액을 그대로 매출액이라고 단정하지 않고 계약 조건과 세금 등 포함 항목을 대조해야 합니다.' if s['topic']=='revenue' else
              '재고 매입원가에 포함할 원가와 차감할 할인 등을 확인하는 데 사용하는 기준입니다. 운임이나 할인 때문에 생긴 합리적인 차이인지, 장부 입력 오류인지 구분하는 데 연결합니다.')
        blocks.append({'kind':'explanation','text':s['title']+' — '+text,'citation_ids':[s['id']]})
    blocks.append({'kind':'procedure','text':'원본 송장과 장부 분개를 대조하고, 계약·발주서·정정 송장·할인 내역·세금 및 운임 명세로 차이를 조정해 보세요. 송장이 잘못됐으면 송장 정정이 먼저일 수 있으므로 차이만 보고 장부를 바로 수정하지 마세요. 거래가 매출인지 매입인지와 실제 계정을 알려주시면 적용 범위를 좁힐 수 있습니다.','citation_ids':[c['check_id'] for c in relevant]})
    prefix=('적용 회계기준이 선택되지 않아 아래 기준은 K-IFRS를 적용하는 경우의 조건부 참고입니다.' if not framework else '선택한 회계기준의 관련 원문을 연결했습니다.') if standards else '관련 원문을 확인하지 못해 특정 회계기준이 적용된다고 단정하지 않습니다.'
    answer=[]
    for b in blocks:
        if b['kind']=='risk':answer.append('조건: '+b['condition']+'\n'+b['text'])
        else:answer.append(b['text'])
    answer.insert(2,prefix)
    return {'answer':'\n\n'.join(answer),'citations':refs,'assistance':{'blocks':blocks,'validation':'typed_amount_comparison_rules'},'grounding_status':'retrieved_evidence_with_reviewed_assistance','retrieval_errors':failures}
