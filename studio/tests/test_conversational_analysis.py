# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,json,unittest,copy,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from chat_pipeline import answer
from conversation_plan import ConversationPlan,classify
from finding_context import findings,select
from finding_reasoning import fallback_analysis,validation_errors,guide_for

def audit_for(area,index=0):
 configurations={'amount':('ledger_invoice_amount_comparison','amount','total_amount','currency','EUR','7321.75','7100.25'), 'items':('item_quantity_comparison','quantity','quantity','unit','PCS','81','79'), 'date':('invoice_transaction_date_review','transaction_date','issue_date',None,'','2026-04-30','2026-05-01'), 'shipping':('cross_document_date_review','shipment_date','shipment_date',None,'','2026-06-02','2026-06-03'), 'logistics':('document_gross_weight_comparison','gross_weight','gross_weight','weight_unit','KG','899','901'), 'counterparty':('ledger_invoice_counterparty_comparison','counterparty','buyer',None,'','Example A','Example B'), 'references':('reference_invoice_number','invoice_number','invoice_number',None,'','INV-A','INV-B'), 'documents':('document_presence','presence','presence',None,'',None,'present')}
 kind,lf,rf,uf,unit,left,right=configurations[area]
 if area=='amount':left=str(7000+index*17.5);right=str(6800+index*12.25)
 docs={'commercial_invoice':{'id':'doc-r','document_type':'commercial_invoice'},'packing_list':{'id':'doc-l','document_type':'packing_list'}}
 ledger={'id':'ledger-l','fields':{'transaction_id':{'value':'CASE-'+str(index)}}}
 lid='ledger-l' if area in ('amount','counterparty','date') else 'doc-l'
 def e(entity,field,value):return {'field_name':field,'normalized_value':value,'source':{'entity_id':entity,'json_pointer':'/fields/'+field}}
 evidence=[e(lid,lf,left),e('doc-r',rf,right)]
 if uf:evidence+=[e(lid,uf,unit),e('doc-r',uf,unit)]
 check={'check_id':'check-'+str(index),'type':kind,'title':area,'status':'cannot_evaluate' if area=='documents' else 'flag','reason':'required_value_missing' if area=='documents' else 'values_differ','context':{'document_type':'commercial_invoice'} if area=='documents' else {},'evidence':evidence,'values':{}}
 return {'transactions':[{'transaction_id':'owned-'+str(index),'ledger':ledger,'documents':docs,'checks':[check]}]}

class ConversationTests(unittest.TestCase):
 def model(self,domain,task,areas,follow=False,invalid=False):
  def run(role,system,data,schema):
   if role=='router':return {'domain':domain,'task':task,'areas':areas,'transaction':'','follow_up':follow}
   if role=='reasoning':
    result=fallback_analysis(data['findings']);result.pop('mode',None)
    if invalid:result['impact'][0]['text']='오류가 확정됐습니다. 999999999 USD입니다.'
    return result
   return dict(answers_request=True,grounded=True,reasoning_present=True,no_unsupported_cause=True,feedback='')
  return run
 def test_48_cross_area_intent_evaluations(self):
  tasks={'EXPLAIN_FINDING':'무슨 문제야?','RISK_ANALYSIS':'어떤 리스크야?','ROOT_CAUSE_ANALYSIS':'왜 이런 차이가 생겼어?','RECOMMEND_PROCEDURE':'어떻게 처리해야 해?','ACCOUNTING_IMPLICATION':'회계적으로 어떤 영향이 있어?','EVIDENCE_REQUEST':'뭘 추가로 확인해야 해?'}
  rows=[]
  for i,area in enumerate(('amount','items','date','shipping','logistics','counterparty','references','documents')):
   for task,q in tasks.items():
    with self.subTest(area=area,task=task):
     a=audit_for(area,i+20);before=copy.deepcopy(a)
     r=answer(a,q,platform_context={'view':'results'},model=self.model('TRANSACTION',task,[area]),retrieve=lambda *a:self.fail('ordinary risk/procedure must not retrieve standards'))
     self.assertEqual(r['selection']['task_intent'],task);self.assertEqual(a,before)
     self.assertNotIn('검토 영역:',r['answer']);self.assertFalse(r['answer_validation']['fallback']);self.assertNotIn('K-IFRS',r['answer'])
     self.assertTrue(r['conversation_state']['active_finding']);self.assertGreater(len(r['answer']),150)
     rows.append({'area':area,'task':task,'question':q,'pass':True,'answer':r['answer'],'evaluation':'controlled inference; routing/grounding/strategy contract only'})
  folder=Path(__file__).parent/'conversation-evaluation';folder.mkdir(exist_ok=True);(folder/'controlled-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')
 def test_four_turn_continuity(self):
  a=audit_for('amount',31);a['transactions']+=audit_for('items',32)['transactions'];history=[]
  for task,q in [('RISK_ANALYSIS','금액 차이 위험?'),('ACCOUNTING_IMPLICATION','아니 그래서 무슨 영향?'),('RECOMMEND_PROCEDURE','그럼 어떻게 처리?'),('STANDARD_REQUEST','관련 기준도 있어?')]:
   r=answer(a,q,history,model=self.model('TRANSACTION',task,['amount'] if not history else [],bool(history)),retrieve=lambda *a:{'passages':[]})
   self.assertEqual(r['conversation_state']['active_transaction'],'owned-31');self.assertEqual(r['conversation_state']['active_finding'],['check-31'])
   history.append(dict(r,status='complete',question=q))
 def test_new_selection_does_not_leak_previous_transaction(self):
  a=audit_for('amount',1);a['transactions']+=audit_for('items',2)['transactions']
  p=ConversationPlan('TRANSACTION','RISK_ANALYSIS',follow_up=True)
  h=[{'status':'complete','conversation_state':{'active_transaction':'owned-1','active_finding':['check-1']}}]
  got=select(findings(a),p,h,'owned-2');self.assertEqual(got[0]['transaction_id'],'owned-2')
 def test_different_units_never_subtracted(self):
  a=audit_for('amount');a['transactions'][0]['checks'][0]['evidence'][-1]['normalized_value']='JPY'
  self.assertIsNone(findings(a)[0]['difference'])
 def test_reversed_amount_direction(self):
  a=audit_for('amount');es=a['transactions'][0]['checks'][0]['evidence'];es[0]['normalized_value']='12.25';es[1]['normalized_value']='25.50'
  f=findings(a)[0];self.assertEqual(f['difference'],'-13.25');self.assertIn('과소',guide_for(f)['impact'])
 def test_invalid_answer_regenerated_then_safe_fallback(self):
  r=answer(audit_for('amount'),'리스크?',model=self.model('TRANSACTION','RISK_ANALYSIS',['amount'],invalid=True))
  self.assertEqual(r['answer_validation']['attempts'],2);self.assertTrue(r['answer_validation']['fallback']);self.assertNotIn('999999999',r['answer']);self.assertNotIn('확정됐습니다',r['answer'])
 def test_timeout_still_answers_task(self):
  normal=self.model('TRANSACTION','RECOMMEND_PROCEDURE',['amount'])
  def model(role,*a):
   if role=='reasoning':raise TimeoutError()
   return normal(role,*a)
  r=answer(audit_for('amount'),'어떻게 처리?',model=model);self.assertTrue(r['answer_validation']['fallback']);self.assertIn('차이 조정표',r['answer'])
 def test_unrelated_standard_not_emitted(self):
  def reject(*args):return {'decisions':[]}
  r=answer(audit_for('amount'),'관련 기준?',model=self.model('HYBRID','STANDARD_REQUEST',['amount']),retrieve=lambda *args:{'passages':[{'id':'irrelevant','title':'다른 기준','text':'현재 검토와 전혀 다른 기준의 긴 문단입니다.'}]},assess=reject)
  self.assertFalse(any(c['kind']=='standard' for c in r['citations']));self.assertNotIn('다른 기준',r['answer']);self.assertIn('차이 조정표',r['answer'])
 def test_generated_fake_finding_rejected(self):
  fs=findings(audit_for('amount'));r=fallback_analysis(fs);r['finding_ids']=['foreign'];self.assertIn('finding_reference',validation_errors(r,fs,'RISK_ANALYSIS'))
 def test_explicit_scope_corrects_model_scope_without_replacing_task(self):
  p=classify('장부와 송장 금액 위험?',[],{'view':'results'},['CASE-A'],model=self.model('ACCOUNTING','RISK_ANALYSIS',['references'],True))
  self.assertEqual(p.domain,'TRANSACTION');self.assertEqual(p.areas,('amount',));self.assertEqual(p.task,'RISK_ANALYSIS');self.assertFalse(p.follow_up)
 def test_model_cannot_copy_previous_intent_over_explicit_request(self):
  h=[{'status':'complete','conversation_state':{'active_transaction':'owned-1','active_finding':['check-1'],'current_topic':['amount'],'task_intent':'RISK_ANALYSIS'}}]
  for question,task in [('그럼 어떻게 처리해야 해?','RECOMMEND_PROCEDURE'),('아니 그래서 무슨 영향이 있다는 거야?','ACCOUNTING_IMPLICATION'),('관련 회계기준도 있어?','STANDARD_REQUEST')]:
   p=classify(question,h,{'view':'results'},['CASE-1'],model=self.model('GENERAL','RISK_ANALYSIS',[],False))
   self.assertEqual(p.task,task);self.assertTrue(p.follow_up)
 def test_missing_quantity_is_not_physical_loss(self):
  a=audit_for('items',74);c=a['transactions'][0]['checks'][0];c['status']='cannot_evaluate';c['reason']='required_value_missing';c['evidence'][0]['normalized_value']=None
  r=answer(a,'품목 수량 누락 위험?',model=self.model('TRANSACTION','RISK_ANALYSIS',['items']))
  self.assertIn('필수 정보',r['answer']);self.assertIn('실물 부족의 증거가 아닙니다',r['answer']);self.assertNotIn('감액',r['answer'])
 def test_matching_finding_does_not_invent_mismatch(self):
  f=findings(audit_for('amount'))[0];f['status']='PASS'
  self.assertNotIn('과대',guide_for(f)['impact']);self.assertIn('불일치가 확인되지 않았습니다',guide_for(f)['impact'])
 def test_unowned_transaction_does_not_leak_other_values(self):
  r=answer(audit_for('amount'),'TX999 금액 위험?',model=self.model('TRANSACTION','RISK_ANALYSIS',['amount']))
  self.assertEqual(r['grounding_status'],'no_owned_finding');self.assertFalse(r['citations'])
 def test_evidence_request_is_not_reasoning_or_rag(self):
  p=classify('포장명세서 원본 추출값 보여줘',[],{},['CASE-A'],model=self.model('TRANSACTION','RISK_ANALYSIS',['items']))
  self.assertEqual((p.domain,p.task),('EVIDENCE','EVIDENCE_REQUEST'))
 def test_summary_covers_all_areas_without_llm_analysis(self):
  a={'transactions':[]}
  for i,area in enumerate(('amount','items','date','shipping','logistics','counterparty','references','documents')):a['transactions']+=audit_for(area,i)['transactions']
  normal=self.model('TRANSACTION','SUMMARY',[])
  def model(role,*args):
   self.assertEqual(role,'router');return normal(role,*args)
  r=answer(a,'전체 검토 결과 요약',model=model)
  self.assertEqual(len(r['conversation_state']['active_finding']),8);self.assertIn('물류정보',r['answer'])
 def test_models_are_separate_roles(self):
  from chat_models import role_model
  from unittest.mock import patch
  with patch.dict('os.environ',{'FINTRA_ROUTER_MODEL':'small-classifier','FINTRA_REASONING_MODEL':'strong-reasoner'}):
   self.assertEqual(role_model('router'),'small-classifier');self.assertEqual(role_model('reasoning'),'strong-reasoner')
if __name__=='__main__':unittest.main()
