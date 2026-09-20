# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Conversation orchestration: route -> Finding -> reasoning -> optional standards -> review."""
import json,time,re
from dataclasses import asdict
from conversation_plan import classify,previous_state
from finding_context import findings,select,state_for,fact_sentence,transaction_context
from finding_reasoning import analyze,fallback_analysis,validation_errors,render,review_answer
from chat_models import role_model
from answer_budget import remaining

def answer(audit,question,history=(),transaction_id=None,framework=None,cancel=None,platform_context=None,on_token=None,*,legacy=None,model=None,retrieve=None,assess=None):
 context=platform_context or {};started=time.perf_counter();metrics={'reasoning':0.0,'answer_validation':0.0,'retrieval':0.0,'applicability':0.0};chunks=[]
 def emit(text):
  if cancel and cancel.is_set():raise InterruptedError('답변 생성을 중지했습니다.')
  if not text:return
  if not chunks:metrics['first_content']=time.perf_counter()-started
  chunks.append(text)
  if on_token:on_token(text)
 t=time.perf_counter();all_rows=findings(audit);metrics['DB_lookup']=time.perf_counter()-t
 txs=list({f['transaction_id']:f['transaction_name'] for f in all_rows}.values())
 t=time.perf_counter();plan=classify(question,history,context,txs,model=model);metrics['router']=time.perf_counter()-t
 selected=select(all_rows,plan,history,transaction_id)
 # Service/general and literal evidence/standard tools retain their dedicated behavior.
 from chat_router import Plan
 from kasb_kb import exact_reference
 no_case_domain=plan.domain in ('GENERAL','ACCOUNTING','STANDARD')
 if no_case_domain or plan.domain=='EVIDENCE':
  mode='general' if plan.domain in ('GENERAL','ACCOUNTING') else 'accounting_standard' if plan.domain=='STANDARD' else 'evidence'
  tools={'general':(),'accounting_standard':('accounting_standard',),'evidence':('evidence',)}[mode]
  result=legacy(audit,question,history,transaction_id,framework,cancel,context,on_token,_plan=Plan(mode,tools,question,plan.transaction or None),retrieve=retrieve,assess=assess)
  result['selection'].update(domain=plan.domain,task_intent=plan.task,router_method=plan.method)
  # A general turn does not overwrite a transaction's active Finding.
  result['conversation_state']=previous_state(history)
  result.setdefault('latency',{})['domain_router']=metrics['router'];return result
 if not selected:
  emit('요청한 거래·항목을 현재 분석에서 찾지 못했습니다. 거래를 선택하거나 확인할 항목을 알려주세요.')
  return {'answer':''.join(chunks),'citations':[],'selection':{'intent':'transaction','domain':plan.domain,'task_intent':plan.task},'conversation_state':{},'latency':metrics,'grounding_status':'no_owned_finding'}
 memory=state_for(selected,plan)
 checks={c['check_id']:c for t in audit.get('transactions',[]) for c in t.get('checks',[])}
 citations=[{'id':f['id'],'kind':'check','title':f['title'],'check':checks[f['id']]} for f in selected if f['id'] in checks]
 basic=plan.task in ('FACT_LOOKUP','SUMMARY')
 fallback=fallback_analysis(selected);analysis=fallback;validation={};errors=[];attempts=0
 if basic:
  emit(render(selected,fallback,plan.task))
 else:
  # Verified observed facts appear before slow model analysis. No raw ReviewResult dump.
  emit('\n'.join(fact_sentence(f) for f in selected)+'\n\n')
  early_impact=plan.task in ('RISK_ANALYSIS','ACCOUNTING_IMPLICATION')
  if early_impact:
   emit('\n'.join(x['text'] for x in fallback['impact'])+'\n\n')
  for attempt in range(0 if plan.task=='STANDARD_REQUEST' else 2):
   attempts+=1
   try:
    if remaining(60)<14:raise TimeoutError('insufficient_analysis_budget')
    t=time.perf_counter()
    try:candidate=analyze(question,plan,selected,history,model,errors if attempt else None)
    finally:metrics['reasoning']+=time.perf_counter()-t
    errors=validation_errors(candidate,selected,plan.task)
    if errors:continue
    if early_impact:candidate['impact']=fallback['impact']
    text=render(selected,candidate,plan.task)
    t=time.perf_counter()
    try:validation=review_answer(question,plan.task,text,selected,model)
    finally:metrics['answer_validation']+=time.perf_counter()-t
    if all(validation.get(k) is True for k in ('answers_request','grounded','reasoning_present','no_unsupported_cause')):
     analysis=dict(candidate,mode='local_reasoning');break
    errors=[validation.get('feedback','answer_relevance_failed')]
   except InterruptedError:raise
   except Exception as exc:errors=[type(exc).__name__];break
  final=render(selected,dict(analysis,impact=[]) if early_impact else analysis,plan.task)
  facts='\n'.join(fact_sentence(f) for f in selected)
  body=final[len(facts):].lstrip() if final.startswith(facts) else final
  # Validated sections are streamed without disclosing unverified draft text.
  for paragraph in body.split('\n\n'):emit(paragraph+'\n\n')
 source_audit=[];retrieval_error=None
 if plan.task=='STANDARD_REQUEST':
  try:
   from chat_retrieval import standard_lookup
   from source_relevance import validate_sources
   # Risk analysis above never sees search candidates. Query uses selected review purpose only.
   query=question+' '+ ' '.join(dict.fromkeys(f['title'] for f in selected))
   t=time.perf_counter();search=(retrieve or standard_lookup)(query,framework,{});metrics['retrieval']=time.perf_counter()-t
   if search.get('method')=='exact_metadata_lookup':approved=search.get('passages',[])
   else:
    t=time.perf_counter();v=validate_sources(question,search.get('passages',[]),transaction_context(selected),case=True,assess=assess);metrics['applicability']=time.perf_counter()-t;approved=v['passages'];source_audit=v['decisions']
   if approved:
    # Validate the relevance of the proposed source attachment, not only the prose.
    from source_relevance import verify_answer
    data=transaction_context(selected);data['accounting_standard']={'passages':approved}
    source_text='\n\n'.join(p['title']+'\n'+p['text'] for p in approved)
    if not verify_answer(question,source_text,data,assess=assess):approved=[]
   for p in approved:
    label=p['title']+(' · 문단 '+str(p.get('metadata',{}).get('paragraph')) if p.get('metadata',{}).get('paragraph') else '')
    emit('관련 기준 · 적용 전제 확인 필요\n'+label+'\n'+p['text']+'\n\n')
    citations.append({'id':p['id'],'kind':'standard','title':label,'quote':p['text'],'source':p,'applicability':'conditional','required_conditions':['실제 거래 성격과 해당 기준의 적용 전제 확인']})
   if not approved:emit('이번 검토 목적에 직접 연결되는 기준 문단은 확인하지 못했습니다. 위 내용은 증빙 대조에서 확인할 회계 영향과 업무 절차이며, 특정 기준의 적용을 확정한 결론은 아닙니다.')
  except InterruptedError:raise
  except Exception as exc:
   retrieval_error=type(exc).__name__;emit('기준 원문 검증은 완료하지 못해 인용하지 않았습니다. 위 확인 절차를 먼저 진행하고 실제 분개와 거래 조건을 확보한 뒤 적용 기준을 검토하세요.')
 metrics['total']=time.perf_counter()-started
 result={'answer':''.join(chunks).strip(),'citations':citations,'selection':{'intent':'hybrid' if plan.task=='STANDARD_REQUEST' else 'transaction','domain':plan.domain,'task_intent':plan.task,'router_method':plan.method,'tools':['ReviewResult','finding_reasoner']+(['standards_retrieval','applicability_judge'] if plan.task=='STANDARD_REQUEST' else [])},'conversation_state':memory,'analysis':analysis,'answer_validation':{'verdict':validation,'errors':errors,'attempts':attempts,'fallback':analysis.get('mode')=='typed_guidance'},'relevance_validation':{'decisions':source_audit,'error':retrieval_error},'latency':metrics,'models':{'router':role_model('router'),'reasoning':role_model('reasoning'),'validator':role_model('validator')},'grounding_status':'owned_findings_with_conditional_analysis','context_chars':len(json.dumps(selected,ensure_ascii=False))}
 # Retain editable memo integration without treating generated text as verified evidence.
 if re.search(r'메모|초안',question):result['assistance']={'blocks':[{'kind':'draft','text':result['answer'],'citation_ids':[c['id'] for c in citations]}]}
 from chat_pipeline import LOG_LOCK
 import os,hashlib
 from pathlib import Path
 folder=Path(os.environ.get('FINTRA_WORKSPACE_DATA',Path(__file__).resolve().parents[1]/'data'))/'telemetry';folder.mkdir(parents=True,exist_ok=True)
 with LOG_LOCK:
  with (folder/'conversation-latency.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps({'at':time.time(),'question_hash':hashlib.sha256(question.encode()).hexdigest()[:16],'plan':asdict(plan),'latency':metrics,'models':result['models'],'analysis_mode':analysis.get('mode'),'validation_errors':errors,'source_decisions':source_audit},ensure_ascii=False)+'\n')
 return result
