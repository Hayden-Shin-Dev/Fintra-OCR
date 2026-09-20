# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import conversations,grounded_chat,review_actions
from claim_validation import validate

class FeedbackTests(unittest.TestCase):
 def test_deadline_covers_queue_and_preserves_completed_messages(self):
  with tempfile.TemporaryDirectory() as root:
   folder=Path(root);event=threading.Event();conversations.ACTIVE['pending']=event
   try:
    conversations.write(folder,[{'id':'pending','status':'queued'},{'id':'done','status':'complete','answer':'saved'}])
    conversations.expire(folder,'pending');conversations.expire(folder,'done')
    rows=conversations.history(folder)
    self.assertEqual(rows[0]['status'],'failed');self.assertTrue(event.is_set())
    self.assertEqual(rows[1]['answer'],'saved');self.assertEqual(rows[1]['status'],'complete')
   finally:conversations.ACTIVE.pop('pending',None)
 def test_inventory_is_not_cost_of_sales(self):
  self.assertTrue(validate('재고자산은 매출원가로 불리며 물류원가를 포함합니다.',[]))
  self.assertFalse(validate('재고자산을 판매할 때 장부금액을 비용으로 인식합니다.',[]))
 def test_document_request_contains_actual_request_not_only_facts(self):
  tx={'transaction_id':'case','checks':[{'check_id':'weight','title':'순중량','status':'flag','type':'document_net_weight_comparison','evidence':[{'field_name':'net_weight','normalized_value':320}]}]}
  for q in ['담당자에게 요청할 자료와 질문을 작성해줘','담당자에게 어떤 자료를 요청해야 해?']:
   r=review_actions.respond(q,[tx]);self.assertEqual(r['selection']['intent'],'documents')
   self.assertIn('입출고',r['answer']);self.assertIn('담당자에게 보낼 질문',r['answer'])
 def test_timeout_is_not_successful_facts_fallback(self):
  audit={'transactions':[{'transaction_id':'case','checks':[{'check_id':'weight','title':'순중량','status':'flag','type':'document_net_weight_comparison','evidence':[]}]}]}
  plan={'intent':'documents','check_ids':['c0'],'needs_standards':False,'search_queries':[]}
  with patch.object(grounded_chat,'model',return_value=plan),patch('copilot.compose',side_effect=TimeoutError('deadline')):
   with self.assertRaises(TimeoutError):grounded_chat.answer(audit,'검수 기록 요청 이메일을 정중하게 작성해줘')

 def test_inventory_explanation_requires_loss_clause_and_actual_difference(self):
  from current_principles import inventory_explanation
  check={'check_id':'weight','title':'순중량','status':'flag','type':'document_net_weight_comparison','evidence':[{'field_name':'net_weight'}]}
  ref={'id':'standard1','kind':'standard','title':'재고자산','quote':'재고자산의 모든 감모손실은 발생한 기간에 비용으로 인식한다.','source':{'framework':'K-IFRS'}}
  answer=inventory_explanation([check],[ref]);self.assertIn('문서상 차이',answer['answer'])
  self.assertIn('standard1',answer['assistance']['blocks'][0]['citation_ids'])
  self.assertIsNone(inventory_explanation([dict(check,status='pass')],[ref]))
  self.assertIsNone(inventory_explanation([check],[dict(ref,quote='계약이행원가는 조건에 따라 인식한다.')]))
 def test_explicit_requests_preserve_intent_and_field_scope(self):
  from question_route import route
  checks={'c0':{'status':'flag','type':'document_net_weight_comparison','evidence':[{'field_name':'net_weight'}]},'c1':{'status':'flag','type':'ledger_invoice_amount_comparison'}}
  p=route('순중량 관련 증빙 요청 메일을 작성해줘',checks)
  self.assertEqual(p['intent'],'documents');self.assertEqual(p['check_ids'],['c0'])
  self.assertIsNone(route('그게 무슨 뜻이야?',checks))

 def test_recorded_difference_magnitude_is_valid_but_new_amount_is_not(self):
  ref={'kind':'check','check':{'context':{'comparison_unit':'KG'},'values':{'difference':'-10'},'evidence':[{'normalized_value':320},{'normalized_value':330}]}}
  self.assertFalse(validate('320 KG와 330 KG의 차이는 10 KG입니다.',[ref]))
  self.assertTrue(validate('차이는 20 KG입니다.',[ref]))

 def test_gaap_loss_is_not_ifrs_loss_rule(self):
  from current_principles import loss_rule
  text='정상적으로 발생한 감모손실은 매출원가에 가산하고 비정상적으로 발생한 감모손실은 영업외비용으로 분류한다.'
  ref={'id':'gaap','kind':'standard','title':'재고자산','relevant_text':text,'source':{'framework':'일반 기업 회계 기준'}}
  self.assertIn('영업외비용',loss_rule([ref])[1])
  self.assertIsNone(loss_rule([dict(ref,source={'framework':'K-IFRS'})]))
 def test_specific_ocr_question_is_not_overwritten_by_entire_summary(self):
  from workspace_chat import respond
  context={'stage':'awaiting_review','documents':[{'fields':{'currency':{'value':'USD'},'net_weight':{'value':'320'}}}]}
  r=respond('이 문서 통화는 뭐야?',[],context,lambda *a:{'domain':'workspace','topic':'ocr','answer':'추출된 통화는 USD입니다.'})
  self.assertIn('통화: USD',r['answer']);self.assertNotIn('320',r['answer'])
 def test_social_does_not_call_model_after_comparison(self):
  with patch.object(grounded_chat,'model') as model:
   r=grounded_chat.answer({'transactions':[{'transaction_id':'x','checks':[]}]},'고마워')
  model.assert_not_called();self.assertIn('편하게',r['answer'])

 def test_report_framework_cache_preserves_user_edits_and_invalidates_input(self):
  import workpapers,time
  with tempfile.TemporaryDirectory() as root:
   folder=Path(root);result={'audit':{'transactions':[]}}
   workpapers.write(folder/'result.json',result)
   def generate(result,settings,progress):
    return {'title':'generated','generation':{'created_at':time.time(),'status':'complete','input_hash':workpapers.fingerprint(result),'framework':settings['framework']}}
   with patch.object(workpapers,'generate',side_effect=generate) as gen:
    workpapers.execute(folder,{'framework':'K-IFRS'},0,'test')
    edited=workpapers.read(folder/'draft.json');edited['title']='user edit';workpapers.write(folder/'draft.json',edited)
    workpapers.execute(folder,{'framework':'일반기업회계기준'},1,'test')
    workpapers.execute(folder,{'framework':'K-IFRS'},2,'test')
    self.assertEqual(gen.call_count,2)
    self.assertTrue(any(workpapers.read(p).get('title')=='user edit' for p in folder.glob('draft-before-ai-*')))
    result['audit']['changed']=True;workpapers.write(folder/'result.json',result)
    workpapers.execute(folder,{'framework':'K-IFRS'},3,'test');self.assertEqual(gen.call_count,3)

 def test_ocr_value_question_never_calls_classifier(self):
  context={'stage':'awaiting_review','selected_document_id':'a','documents':[{'id':'a','name':'invoice','fields':{'currency':{'value':'USD'},'total_amount':{'value':'3075'}}}]}
  with patch.object(grounded_chat,'model') as model:
   r=grounded_chat.answer({},'선택한 송장의 통화와 총액만 알려줘',platform_context=context)
  model.assert_not_called();self.assertIn('3075',r['answer']);self.assertIn('USD',r['answer'])
