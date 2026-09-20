# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Grounded accounting interpretation shared by chat and workpapers."""
from logistics_scope import AUDIT_SCOPE
from audit_research import standard_body
import re

def logistics_procedure_errors(answer):
    errors=[]
    for step in answer.get('work_program',[]):
        action=step.get('action','')
        if re.search(r'총액.{0,35}(?:할인|반품).{0,20}차감',action) and not re.search(r'이미|반영\s*여부|포함\s*여부|중복',action):
            errors.append('송장 총액의 할인·반품 반영 여부를 확인하지 않고 다시 차감하도록 제안했습니다.')
    conclusion=answer.get('review_conclusion','')
    if re.search(r'(?:할인|반품|부대원가).{0,30}(?:따른|인한).{0,25}차이.{0,15}확인할 수 있',conclusion):
        errors.append('문서 차이만 확인했는데 할인·부대원가를 확인된 원인으로 결론지었습니다.')
    return errors

def interpret(question,checks,refs,ask):
    """Repair rejected drafts using concrete validator feedback, never accept by exhaustion."""
    feedback=[]
    for attempt in range(3):
        def repair_ask(prompt,data,schema):
            if 'implication' in schema.get('properties',{}):
                data=dict(data,corrections=feedback)
                prompt+=' 이전 검증에서 지적된 내용이 있으면 그 주장을 삭제하거나 원문의 조건에 맞춰 수정하세요. 금액 차이만으로 인식 시점 오류나 계약 위반을 추정하지 마세요.'
            return ask(prompt,data,schema)
        text,sources,verdict=_interpret_once(question,checks,refs,repair_ask)
        if text:return text,sources,dict(verdict,attempts=attempt+1)
        feedback.append(verdict.get('reason','원문과 관찰 사실에 맞춰 다시 작성하세요.'))
        if verdict.get('reason')=='관련 기준 원문 없음':break
    return '',[],dict(verdict,attempts=attempt+1,repair_history=feedback)

def _interpret_once(question,checks,refs,ask):
    source_map={'s'+str(i):r for i,r in enumerate(refs) if r.get('kind')=='standard'}
    if not source_map:return '',[],{'reason':'관련 기준 원문 없음'}
    schema={'type':'object','properties':{
      'implication':{'type':'string','maxLength':240},
      'procedures':{'type':'string','maxLength':240},
      'assertions':{'type':'array','minItems':1,'maxItems':4,'uniqueItems':True,'items':{'type':'string','enum':['정확성','완전성','실재성','평가','기간귀속','권리와 의무','분류와 표시']}},
      'work_program':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'object','properties':{
          'document':{'type':'string','maxLength':60},'action':{'type':'string','maxLength':100},'completion_criterion':{'type':'string','maxLength':100}},
          'required':['document','action','completion_criterion'],'additionalProperties':False}},
      'review_conclusion':{'type':'string','maxLength':180},
      'sources':{'type':'array','minItems':1,'maxItems':3,'items':{'type':'string','enum':list(source_map)}}},
      'required':['implication','procedures','assertions','work_program','review_conclusion','sources'],'additionalProperties':False}
    data={'question':question,'observations':[{'title':c.get('title'),'status':c['status'],'fields':list(dict.fromkeys(e.get('field_name') for e in c.get('evidence',[])))} for c in checks],
          'standards':{k:{'title':r['title'],'framework':r['source'].get('framework'),'conditions':r['required_conditions'],'text':r.get('relevant_text') or standard_body(r['quote'])} for k,r in source_map.items()}}
    answer=ask(AUDIT_SCOPE+'\n회계 검토 초안을 한국어로 작성하세요. implication에는 관찰 사항의 가능한 회계 영향, procedures에는 핵심 검토 방향을 쓰세요. assertions에는 현재 발견 사항과 관련된 감사 주장만 선택하세요. 금액 차이는 정확성과 평가를 우선 검토하고, 누락의 증거 없이 완전성 위험이라고 단정하지 마세요. work_program에는 담당자가 수행할 절차를 작성하세요: document는 요청 자료, action은 구체적인 대조 행동, completion_criterion은 어떤 근거를 확보해야 검토를 마칠 수 있는지입니다. 완료 기준은 차이 조정표와 증빙으로 측정 근거를 설명하는 것입니다. 정당한 차이는 남을 수 있으므로 장부와 송장의 금액 자체를 강제로 일치시키거나 오류 수정 완료를 요구하지 마세요. 금액 측정 조항을 인식 시점의 근거로 인용하지 마세요. 각 설명은 두 문장 이하로 쓰세요. 차이의 원인을 추측해 열거하지 마세요. 검색된 기준에 없는 리스료·계약 위반·인식 시점을 새로 끌어오지 마세요. 입력에 없는 원인은 확인되지 않았다고만 쓰세요. 제안 절차는 먼저 송장 총액에 할인·반품·세금·운임 등이 이미 반영되었는지 확인하고 차이 조정표를 작성하는 순서입니다. 총액에서 할인·반품을 다시 차감하도록 지시하지 마세요. 매출·매입 및 용역 제공자 역할은 계약과 장부 계정으로 확인하며 선하증권의 날짜나 인도조건만으로 구분하지 마세요. 예시 값을 만들지 마세요. review_conclusion은 현재 증거로 말할 수 있는 잠정 결론과 미해결 사항을 쓰세요. 적정·부정·중요왜곡을 확정하지 마세요. procedures에서 가산·차감·인식 등 회계처리 규칙을 다시 설명하지 말고, 계약서·분개·송장·입출고 기록 등 어떤 자료를 대조할지 쓰세요. 거래가 매출인지 매입인지 알 수 없으면 조건부로 구분하세요. 문서 불일치는 확인된 회계 오류나 부정과 다릅니다. 제안 절차는 아직 미수행이며 완료했다고 쓰지 마세요. 기준 용어는 원문 그대로 유지하세요. 과대·과소 방향은 현재 확인할 수 없습니다. 본문에는 구체적인 금액·수량을 생성하지 마세요. 내부 키나 작성 지시를 반복하지 마세요. sources에는 사용한 기준 키만 넣으세요.',data,schema)
    program=answer.get('work_program',[])
    procedure_errors=logistics_procedure_errors(answer)
    if procedure_errors:return '',[],{'reason':' / '.join(procedure_errors),'validation':'constraint_rejected'}
    body=' '.join([answer.get('implication',''),answer.get('procedures',''),answer.get('review_conclusion','')]+[str(value) for step in program for value in step.values()])
    if re.search(r'과대|과소|과다|\d[\d,.]*\s*(?:USD|KRW|EUR|원|개|PCS)',re.sub(r'과대\s*(?:또는|/|·)\s*과소','금액 오류',body)):return '',[],{'reason':'미확인 금액 또는 왜곡 방향 생성'}
    selected=[source_map[k] for k in answer.get('sources',[]) if k in source_map]
    if any(len(answer.get(k,''))>650 for k in ('implication','procedures')):return '',[],{'reason':'설명이 과도하게 길어 검토 필요'}
    if any(c['status']=='flag' for c in checks) and any(w in answer.get('implication','') for w in ['불일치가 없','정상 비교만','모두 일치']):return '',[],{'reason':'실제 불일치와 모순된 설명'}
    if not selected:return '',[],{'reason':'출처 연결 실패'}
    from claim_validation import validate
    violations=validate(body,selected+[{'kind':'check','check':c} for c in checks],'risk')
    if violations:return '',[],{'reason':' / '.join(violations),'validation':'constraint_rejected'}
    verdict=ask('총액에서 할인·반품을 차감하라는 절차는 그 총액에 이미 반영되어 있는지 먼저 확인하도록 명시하지 않으면 중복 차감 위험이 있어 거절합니다. 선하증권 날짜만으로 당사자 역할을 판정하는 절차도 거절합니다. 검증 예시: [금액이 다르지만 원인이 미확인되어 회계 오류 여부를 확정할 수 없다]는 승인합니다. [부대원가나 할인 반영 여부를 확인할 필요가 있다]는 미래 확인 제안이므로 승인합니다. [자료를 대조한 뒤 차이의 적정성을 판단한다]도 승인합니다. [차이가 있으므로 회계 오류가 확정되었다] 또는 [실사를 이미 완료했다]는 거절합니다. 검토 초안에 최종 결론이 없다는 이유나 가능성을 조건부로 설명했다는 이유로 거절하지 마세요. 이를 확정 주장으로 재해석하지 마세요. 회계조서 검증입니다. 초안이 실제로 주장한 문장만 제공 기준과 대조하세요. 원문에 없는 규칙을 만들거나, 문서 차이를 확정 오류로 쓰거나, 미실행 절차를 완료했다고 쓰면 false. 조건부 영향과 미래 절차 제안은 허용합니다. proposed_unperformed_work_program은 아직 수행하지 않은 절차이므로 해당 행동을 관찰 증거가 입증하지 않는다는 이유로 거절하지 마세요. 그러나 제안 절차라도 기준 조항의 적용 목적을 잘못 설명하거나 정당한 차이를 무조건 없애도록 요구하면 거절하세요. 초안이 주장하지 않은 세금·관세·예외 등의 설명이 없다는 이유로 거절하지 마세요. 거래 조건이 미확정이라는 사실 자체는 조건부 검토 초안의 오류가 아닙니다. 거절할 때 reason에 문제되는 초안의 정확한 문구와 그것이 원문·관찰 사실에 반하는 이유를 쓰세요. 단순 문체 차이는 거절 사유가 아닙니다. 숫자를 새로 만들어도 false. JSON만 출력합니다.',
       {'draft':{'possible_accounting_effect':answer.get('implication',''),'provisional_conclusion':answer.get('review_conclusion',''),'proposed_unperformed_work_program':program,'assertions':answer.get('assertions',[])},'observations':data['observations'],'standards':[r.get('relevant_text') or standard_body(r['quote']) for r in selected]},
       {'type':'object','properties':{'approved':{'type':'boolean'},'reason':{'type':'string','maxLength':300}},'required':['approved','reason'],'additionalProperties':False})
    if verdict.get('approved') is not True:return '',[],verdict
    answer={k:re.sub(r'\s*\(s\d+\)', '',v) .replace('盘点','실사') if isinstance(v,str) else v for k,v in answer.items()}
    basis=' / '.join(r['title'] for r in selected)
    steps='\n\n'.join(f"{i+1}. 요청 자료: {s['document']}\n수행할 절차: {s['action']}\n완료 판단에 필요한 근거: {s['completion_criterion']}" for i,s in enumerate(program))
    text=('관련 감사 주장\n'+' · '.join(answer.get('assertions',[]))+'\n\n회계적 영향과 검토 방향\n'+answer['implication']+
          '\n\n적용 기준\n'+basis+'\n적용 전제: 거래 성격과 해당 원문의 적용 요건 확인. 원문과 출처는 관련 기준 항목에 수록한다.'+
          '\n\n제안하는 감사 절차 · 미수행\n'+answer['procedures']+'\n\n'+steps+
          '\n\n잠정 검토 결론\n'+answer.get('review_conclusion',''))
    return text,selected,dict(verdict,work_program=program,assertions=answer.get('assertions',[]))
