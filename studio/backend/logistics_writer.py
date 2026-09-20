# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Working papers assembled from owned facts, cited explanation and controlled procedures.

Procedures are future tasks, not generated accounting entries or performed work.
Model rejection cannot erase the facts or the original applicable passages.
"""
from audit_research import topic_for, standard_body
from knowledge_answer import compose
import hashlib,json,time
from pathlib import Path
from atomic_storage import write_json

def explained_principle(question,sources,ask):
    if question==QUESTIONS.get('quantity'):
        from current_principles import loss_rule
        matched=loss_rule(sources)
        if matched:
            source,text=matched
            return {'blocks':[{'kind':'explanation','text':text,'citation_ids':[source['id']],'supporting_quote':source.get('relevant_text') or source.get('quote','')}],'validation':'retrieved_framework_loss_rule'}
    # Only source-bound accounting explanation is cached here. Transaction
    # amounts, conclusions and user edits are always assembled for the current case.
    if getattr(ask,'__module__',None)!='grounded_chat':return compose(question,[],sources,ask)
    from model_config import local_model
    from knowledge_answer import __file__ as validator_path
    import os
    identity={'question':question,'sources':sources,'model':local_model(),
              'endpoint':os.environ.get('FINTRA_CHAT_API_URL','local'),
              'remote_model':os.environ.get('FINTRA_CHAT_MODEL',''),
              'validator':hashlib.sha256(Path(validator_path).read_bytes()).hexdigest()}
    token=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    folder=Path(__file__).resolve().parents[1]/'data/verified-principles'
    path=folder/(token+'.json')
    try:
        cached=json.loads(path.read_text('utf-8'))
        if time.time()-cached['created']<86400 and cached['explanation'].get('validation')=='exact_quote_constraints_and_semantic_review':return cached['explanation']
    except (OSError,ValueError,KeyError):pass
    explanation=compose(question,[],sources,ask)
    if explanation.get('blocks') and explanation.get('validation')=='exact_quote_constraints_and_semantic_review':
        try:
            folder.mkdir(parents=True,exist_ok=True)
            write_json(path,{'created':time.time(),'explanation':explanation})
        except OSError:pass
    return explanation

PROGRAMS = {
 'amount': ('정확성 · 평가', '금액의 측정 범위와 관련 계정', [
  ('계약·발주서, 장부 분개', '매출·매입·운송 용역 중 거래 역할과 계정을 확인하고 같은 거래·통화·금액 범위를 비교했는지 대조한다.', '거래 역할, 계정, 비교 범위를 연결한 기록'),
  ('상업송장, 할인·반품·세금 명세', '총액에 각 항목이 이미 포함되었는지 구성 내역을 확인한다. 차이를 조정표로 설명하며 할인·반품을 중복 차감하지 않는다.', '원본 합계와 장부 금액 사이의 차이 조정표 및 각 조정 근거'),
  ('운임·보험료 청구서, 수입신고 자료', '추가 비용과 세금의 실제 부담자·거래 관련성·환급 여부를 확인하고 적용 기준의 원가 포함 요건과 대조한다.', '비용별 원가 포함·제외 판단과 연결 증빙')]),
 'quantity': ('실재성 · 정확성 · 평가', '재고 기록과 실물 수량의 대응 관계', [
  ('송장, 포장명세서, 선하증권', '품목 코드·단위·포장 환산·문서 범위를 맞추고 분할 선적 및 정정 이력을 확인한다.', '같은 품목·단위·선적 범위로 작성한 수량 대조표'),
  ('입출고·검수·반품 기록, 필요 시 실사 기록', '문서 차이가 실제 인수 수량 차이인지 확인한다. 문서 차이만으로 감모를 확정하지 않는다.', '수량 차이에 대한 인수·출고 기록과 미해결 내역'),
  ('재고 수불부, 원가 명세', '실제 차이가 확인되면 해당 재고의 원가와 기록 영향 및 필요한 회계 검토를 연결한다.', '확인된 실제 수량 차이와 원가·분개 영향의 대응표')]),
 'date': ('기간귀속 · 권리와 의무', '매출·매입 및 재고의 귀속 기간', [
  ('계약·발주서, 인도조건', '거래 역할과 이행 조건을 확인한다. 인도조건 하나만으로 회계 인식 시점을 확정하지 않는다.', '관련 계약 조항과 실제 거래 역할 기록'),
  ('선하증권, 인도·검수·입출고 기록, 장부', '발행일·선적일·인도일·검수일·기장일을 구분하고 적용 기준의 인식 요건을 충족한 증거와 대조한다.', '날짜별 사건과 기간귀속 판단을 연결한 대조표')]),
 'currency': ('정확성 · 평가', '거래 통화와 환산 금액', [
  ('계약, 송장, 장부', '거래 통화와 장부 기록 통화 및 원화 환산 여부를 확인한다. 서로 다른 통화를 단순 차감하지 않는다.', '통화별 원금과 장부 금액 연결표'),
  ('환율 출처, 거래일 및 결산일 자료', '최초 인식·결산·결제 중 해당 검토 시점을 확인하고 적용 기준에 따른 환율 및 환산 내역을 대조한다.', '사용 환율의 출처·기준일 및 재계산 기록')]),
 'identity': ('실재성 · 정확성', '증빙과 거래의 연결', [
  ('계약·발주서, 송장·선하증권 원본', '참조번호, 당사자, 품목, 분할 선적과 정정 이력을 대조하여 동일 거래의 증빙인지 확인한다.', '각 증빙의 거래 연결 근거와 연결되지 않은 문서 목록')]),
 'other': ('정확성', '거래 기록의 증거', [
  ('관련 원본 증빙과 장부', '비교한 항목의 의미·단위·범위를 확인하고 누락값과 차이의 원본 근거를 대조한다.', '검사별 확인 근거와 남은 자료 요청 목록')]),
}

QUESTIONS = {
 'amount':'매출 대가와 재고 매입원가는 각각 어떻게 측정하나요? 제공된 기준의 원칙과 제외 조건을 설명해 주세요.',
 'quantity':'실제 재고 감모손실이 확인된 경우의 회계 원칙을 제공된 기준으로 설명해 주세요.',
 'date':'상품 거래에서 수익을 인식하는 시점과 기간귀속 원칙을 제공된 기준으로 설명해 주세요.',
 'currency':'외화 거래를 인식하고 환산하는 원칙을 제공된 기준으로 설명해 주세요.',
}

def interpret(question, checks, refs, ask):
    topic=topic_for(checks[0]) if checks else 'other'
    assertions,affected,program=PROGRAMS.get(topic,PROGRAMS['other'])
    sources=[r for r in refs if r.get('kind')=='standard']
    explanation={'blocks':[],'validation':'no_standard_passage'}
    if sources:
        try:explanation=explained_principle(QUESTIONS.get(topic,question),sources,ask)
        except Exception as exc:explanation={'blocks':[],'validation':'unavailable','error':type(exc).__name__}
    blocks=explanation.get('blocks',[])
    if blocks:
        principle='\n\n'.join(b['text']+'\n근거: '+' / '.join(r['title'] for r in sources if r['id'] in b['citation_ids']) for b in blocks)
        method='source_bound_ai_explanation'
    elif sources:
        principle='AI 해설 대신 검색된 기준 원문을 수록합니다. 거래의 적용 요건은 아래 절차로 확인합니다.\n\n'+'\n\n'.join(r['title']+'\n'+(r.get('relevant_text') or standard_body(r['quote'])) for r in sources)
        method='original_passages'
    else:
        principle='해당 항목에 연결할 회계기준 원문이 확인되지 않았습니다. 문서 대조 결과와 후속 확인 절차를 기록하며 특정 회계처리의 근거로 확정하지 않습니다.'
        method='evidence_only'
    flagged=any(c.get('status')=='flag' for c in checks)
    impact=('문서 차이가 실제 기록 오류로 확인되는 경우 '+affected+'에 영향이 있는지 검토한다. 원인과 회계 영향은 아직 확정되지 않았다.' if flagged else
            affected+'에 관한 추가 확인 범위이다. 비교값의 일치나 정보 부족만으로 회계처리의 적정성 또는 오류를 확정하지 않는다.')
    steps='\n\n'.join(f'{i+1}. 요청 자료: {doc}\n수행할 절차: {action}\n완료 판단에 필요한 근거: {criterion}' for i,(doc,action,criterion) in enumerate(program))
    conclusion=('확인된 문서 차이는 검토 대상으로 남긴다.' if flagged else '현재 비교 결과에 대한 추가 확인 사항을 위 절차에 기록했다.')+' 증빙과 차이 설명을 확보한 후 조정 필요 여부를 판단한다. 정당한 차이는 남을 수 있으며 금액·수량을 강제로 일치시키지 않는다. 담당자 검토 전에는 회계 오류, 수정 분개 또는 최종 감사 의견을 확정하지 않는다.'
    text='관련 감사 주장\n'+assertions+'\n\n회계적 영향과 검토 범위\n'+impact+'\n\n관련 기준과 적용 검토\n'+principle+'\n\n제안하는 감사 절차 · 미수행\n'+steps+'\n\n잠정 검토 결론\n'+conclusion
    return text,sources,{'method':method,'explanation_validation':explanation.get('validation'),'work_program_source':'versioned_logistics_procedures_v1','assertions':assertions,'procedure_count':len(program),'requires_reviewer':True}
