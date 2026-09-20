# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import workpapers,audit_research
class WorkpaperTests(unittest.TestCase):
 def test_logistics_procedure_does_not_double_deduct_invoice_discounts(self):
  from review_writer import logistics_procedure_errors
  self.assertTrue(logistics_procedure_errors({'work_program':[{'action':'송장 총액에서 할인과 반품을 차감한 후 장부와 비교합니다.'}]}))
  self.assertFalse(logistics_procedure_errors({'work_program':[{'action':'총액에 할인과 반품이 이미 반영되었는지 확인하고 차이 조정표를 작성합니다.'}]}))
  self.assertTrue(logistics_procedure_errors({'review_conclusion':'현재 증거로 할인 및 부대원가 처리에 따른 잠정적인 금액 차이를 확인할 수 있습니다.'}))
 def result(self):
  return {'documents':[], 'audit':{'transactions':[{'transaction_id':'unseen','checks':[{'check_id':'a','type':'quantity','title':'수량 비교','status':'flag','evidence':[{'field_name':'quantity','normalized_value':'8','source':{}}],'values':{}}]}]}}
 def test_topics_cover_distinct_domains(self):
  for field,topic in [('quantity','quantity'),('amount','amount'),('invoice_date','date'),('invoice_number','identity')]:
   self.assertEqual(audit_research.topic_for({'evidence':[{'field_name':field}]}),topic)
  self.assertEqual(audit_research.topic_for({'type':'currency_comparison'}),'currency')
 def test_complete_sections_and_failed_ai_not_silently_approved(self):
  with patch.object(workpapers,'retrieve',return_value=([],{})),patch.object(workpapers,'interpret',return_value=('',[],{})):
   r=workpapers.generate(self.result(),{'framework':'일반기업회계기준'})
  self.assertEqual(r['generation']['status'],'partial');self.assertFalse(r['reviewed'])
  text=' '.join(s['text'] for s in r['sections'])
  self.assertIn('미수행',text);self.assertIn('판단 보류',text);self.assertIn('중요성',text)
  self.assertEqual(r['generation']['framework'],'일반기업회계기준')
 def test_framework_filter_and_unrelated_source_exclusion(self):
  sources=[{'id':'x','title':'상담','source_type':'회계사상담','framework':'일반기업회계기준','text':'내용','source':{}}, {'id':'y','title':'원문','source_type':'회계기준','framework':'K-IFRS','text':'내용','source':{}}]
  def fail(*a):raise AssertionError('No eligible sources should reach model')
  refs,trace=audit_research.retrieve('수량',[], '일반기업회계기준',lambda *a:{'results':sources},fail)
  self.assertEqual(refs,[])
 def test_original_passages_without_approved_explanation_are_partial(self):
  with patch.object(workpapers,'retrieve',return_value=([],{})),patch.object(workpapers,'interpret',return_value=('원문과 제안 절차',[],{'method':'original_passages'})):
   result=workpapers.generate(self.result(),{})
  self.assertEqual(result['generation']['status'],'partial')
  self.assertIn('AI 해설 검증',result['generation']['gaps'][0])
 def test_reference_lists_and_special_topics_do_not_enter_quantity_body(self):
  raw='재고자산\n\n34 재고자산의 감모손실은 비용으로 인식한다. '+('관련 원칙 설명. '*5)+'\n\n관련 질의회신요약\n- 에너지 상담\n\n생물자산의 취득원가 원칙은 특수 거래에 적용한다.'
  body=audit_research.focused_body(raw,['quantity'])
  self.assertIn('감모손실',body);self.assertNotIn('에너지',body);self.assertNotIn('생물자산',body)

 def test_atomic_state_replace_retries_windows_sharing_violation(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'state.json';original=Path.replace;attempts=[]
   def replace(path,target):
    attempts.append(1)
    if len(attempts)==1:raise PermissionError('sharing')
    return original(path,target)
   with patch.object(Path,'replace',replace):workpapers.write(p,{'status':'complete'})
   self.assertEqual(workpapers.read(p)['status'],'complete');self.assertEqual(len(attempts),2)

 def test_changed_revision_preserves_user_work(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);workpapers.write(folder/'result.json',self.result());workpapers.write(folder/'draft.json',{'revision':4,'title':'사용자 내용'})
   fake={'generation':{'input_hash':workpapers.fingerprint(self.result())}}
   with patch.object(workpapers,'generate',return_value=fake):workpapers.execute(folder,{},3,'QA')
   self.assertEqual(workpapers.read(folder/'draft.json')['title'],'사용자 내용')
   self.assertEqual(workpapers.state(folder)['status'],'failed')
 def test_generated_program_has_documents_actions_and_completion_evidence(self):
  from review_writer import interpret
  ref={'kind':'standard','title':'재고자산','source':{},'required_conditions':[],
       'quote':'재고자산의 취득원가는 매입원가로 측정한다.'}
  def model(prompt,data,schema):
   if 'implication' not in schema['properties']:return {'approved':True,'reason':'원문과 일치'}
   self.assertIn('work_program',schema['required'])
   return {'implication':'매입 거래라면 취득원가의 측정을 확인해야 한다.',
     'procedures':'계약과 송장의 조건을 대조한다.','assertions':['정확성'],
     'work_program':[{'document':'계약서','action':'송장의 조건과 대조한다.','completion_criterion':'차이의 조정 근거 확보'},
                     {'document':'상세 원장','action':'분개와 송장을 대조한다.','completion_criterion':'분개와 증빙 연결 확인'}],
     'review_conclusion':'추가 증빙을 확인한 뒤 결론을 검토한다.','sources':['s0']}
  text,_,verdict=interpret('금액 차이',[],[ref],model)
  self.assertTrue(verdict['approved']);self.assertIn('제안하는 감사 절차 · 미수행',text)
  self.assertIn('완료 판단에 필요한 근거: 차이의 조정 근거 확보',text)
  self.assertIn('잠정 검토 결론',text)
 def test_resume_only_interrupted_automatic_drafts(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);jobs={}
   for name,status,task,saved in [('interrupted','complete','running',False),('edited','complete','running',True),('finished','complete','complete',False),('ocr','awaiting_review','running',False)]:
    folder=root/name;folder.mkdir();workpapers.write(folder/'workpaper-task.json',{'status':task})
    if saved:workpapers.write(folder/'draft.json',{'revision':4,'title':'User draft'})
    jobs[name]={'id':name,'status':status,'settings':{}}
   with patch.object(workpapers,'start') as start:
    self.assertEqual(workpapers.resume_preparation(jobs,root),['interrupted'])
    start.assert_called_once_with(root/'interrupted',{},0,'Fintra AI')
   self.assertEqual(workpapers.read(root/'edited'/'draft.json')['title'],'User draft')

if __name__=='__main__':unittest.main()
