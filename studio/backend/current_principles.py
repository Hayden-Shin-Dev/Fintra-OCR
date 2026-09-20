# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Explain the current logistics finding using a verified, applicable rule.

This is a constrained explanation of the retrieved inventory clause, not a
substitute for semantic answers to specific accounting questions.
"""
def inventory_explanation(checks,refs):
    from audit_research import topic_for
    if not checks or any(topic_for(c)!='quantity' or c.get('status') not in ('flag','cannot_evaluate') for c in checks):return None
    sources=[r for r in refs if r.get('kind')=='standard' and '재고' in r.get('title','')]
    matched=loss_rule(sources)
    if not matched:return None
    source,principle=matched
    observed=' · '.join(dict.fromkeys(c.get('title','비교 항목').replace('net_weight','순중량').replace('gross_weight','총중량') for c in checks))
    framework=source.get('source',{}).get('framework') or '선택한 회계기준'
    text=(observed+'에서 확인한 것은 문서상 차이입니다. 이 차이가 실제 재고의 감모나 장부 오류인지 아직 확정한 것은 아닙니다.\n\n'
          +principle+' 따라서 원본의 단위·선적 범위를 맞추고 검수 및 입출고 기록으로 실제 차이를 확인한 뒤, 재고 기록과 비용 인식에 영향이 있는지 검토해야 합니다.\n\n'
          '단순 기재 오류라면 증빙 정정과 재대조가 우선이며, 문서 차이만으로 재고손실 분개를 만들면 안 됩니다.')
    if any(c.get('status')=='cannot_evaluate' for c in checks):
        from grounded_chat import FIELDS
        missing=list(dict.fromkeys(FIELDS.get(e.get('field_name'),e.get('field_name','비교값')) for c in checks if c.get('status')=='cannot_evaluate' for e in c.get('evidence',[]) if e.get('normalized_value') is None))
        text=('현재 '+observed+' 검사는 '+', '.join(missing or ['비교에 필요한 값'])+'을 확인하지 못해 비교를 완료하지 못했습니다. 수량이 다르거나 재고가 실제로 부족하다고 확인한 상태는 아닙니다.\n\n'
              '회계 검토에서는 증빙의 수량이 실제 입출고 및 재고 기록과 연결되는지 확인해야 합니다. 원본에 해당 값이 있으면 OCR 추출값을 바로잡고, 원본에도 없으면 품목별 수량이 있는 포장명세서·검수 기록·입출고 내역을 받아 같은 품목과 단위로 재대조하세요. 확인 전에는 누락값을 0으로 처리하거나 손실 분개를 만들지 않습니다.\n\n'
              '추가 확인 결과 실제 재고 감모가 드러난 경우에 적용할 원칙은 다음과 같습니다. '+principle)
    block={'kind':'explanation','text':text,'condition':'실제 감모손실 여부 및 적용 회계기준 확인','citation_ids':[source['id']]+[c['check_id'] for c in checks]}
    return {'answer':text,'citations':[{'id':c['check_id'],'kind':'check','title':c.get('title','검토 항목'),'check':c} for c in checks]+[source],
            'assistance':{'blocks':[block],'validation':'retrieved_inventory_loss_rule'},'grounding_status':'retrieved_rule_and_current_evidence'}


def loss_rule(refs):
    """Framework-specific summaries require every defining term in one passage."""
    import re
    for source in refs:
        if source.get('kind')!='standard' or '재고' not in source.get('title',''):continue
        text=re.sub(r'\s+',' ',source.get('relevant_text') or source.get('quote',''))
        framework=re.sub(r'[\s-]','',source.get('source',{}).get('framework','')).upper()
        if framework=='일반기업회계기준' and all(x in text for x in ('정상적으로 발생한 감모손실은 매출원가에 가산','비정상적으로 발생한 감모손실은 영업외비용으로 분류')):
            return source,'일반기업회계기준은 실제 재고 감모손실 중 정상적으로 발생한 것은 매출원가에 가산하고, 비정상적으로 발생한 것은 영업외비용으로 분류합니다. 정상·비정상 여부를 확인해야 비용 분류를 판단할 수 있습니다.'
        if framework=='KIFRS' and re.search(r'감모손실은.{0,100}발생한\s*기간에\s*비용으로\s*인식',text):
            return source,'K-IFRS는 실제 재고 감모손실을 발생한 기간의 비용으로 인식하도록 설명합니다.'
    return None
