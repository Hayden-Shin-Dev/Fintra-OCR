# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from source_relevance import validate_sources,verify_answer,paragraphs
class RelevanceTests(unittest.TestCase):
 def setUp(self):
  self.p={'id':'new','title':'새로운 기준서','text':'계약에 따라 자산이 이전된 경우 수익을 인식한다.','metadata':{}}
  self.data={'transaction':{'transactions':[{'groups':[{'title':'검토','status':'PASS','values':[{'field':'condition','value':'confirmed'}]}]}]}}
 def assess(self,**changes):
  def call(system,data,schema):
   return {'decisions':[dict(id=p['id'],relation='direct',answers_question=True,quote=p['text'],missing_premises=[],fact_ids=['f0'],reason='검증',**{})|changes for p in data['candidates']]}
  return call
 def test_common_gate_independent_of_standard_number(self):
  for title in ['K-IFRS 제1002호','신규 기준서 제9999호','일반기업회계기준','내부 해석 자료']:
   with self.subTest(title=title):
    p=dict(self.p,title=title)
    self.assertEqual(len(validate_sources('질문',[p],self.data,True,self.assess())['passages']),1)
 def test_no_direct_answer_rejected(self):
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,self.assess(answers_question=False))['passages'])
 def test_conditional_not_used_as_case_source(self):
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,self.assess(relation='conditional',missing_premises=['가격 하락']))['passages'])
 def test_even_direct_requires_premises(self):
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,self.assess(missing_premises=['계약']))['passages'])
 def test_fabricated_quote_rejected(self):
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,self.assess(quote='존재하지 않는 원문을 만들어서 승인합니다.'))['passages'])
 def test_foreign_fact_rejected(self):
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,self.assess(fact_ids=['other']))['passages'])
 def test_missing_fact_case_rejected(self):
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,self.assess(fact_ids=[]))['passages'])
 def test_conceptual_question_can_use_source_without_case(self):
  self.assertTrue(validate_sources('개념',[self.p],{},False,self.assess(fact_ids=[]))['passages'])
 def test_timeout_fails_closed(self):
  def fail(*a):raise TimeoutError()
  self.assertFalse(validate_sources('질문',[self.p],self.data,True,fail)['passages'])
 def test_paragraph_scope(self):
  p=dict(self.p,text='9\n첫번째 문단 내용입니다.\n32\n두번째 다른 주제입니다.')
  result=paragraphs([p]);self.assertEqual([r['metadata']['paragraph'] for r in result],['9','32']);self.assertNotIn('두번째',result[0]['text'])
 def test_unsupported_causal_claim_rejected(self):
  self.assertFalse(verify_answer('누락 위험','수량 누락은 가격 하락 감액의 원인이다.',self.data,lambda *a:{'supported':False,'reason':'unsupported cause'}))
 def test_answer_verifier_error_fails_closed(self):
  self.assertFalse(verify_answer('q','text',{},lambda *a:1/0))
class RelevancePipelineTests(unittest.TestCase):
 def test_rejected_source_never_reaches_output_or_generator(self):
  import json
  import chat_pipeline
  root=Path(__file__).resolve().parents[1]
  audit=json.loads((root/'team-preview/analyses/c3b84748825f4ef3b8d454ccb44d50ee/result.json').read_text('utf-8'))['audit']
  p={'id':'arbitrary','title':'새 기준서','text':'전혀 다른 경제적 사건에 관한 문단 내용입니다.'}
  emitted=[]
  def reject(system,data,schema):return {'decisions':[{'id':c['id'],'relation':'unrelated','answers_question':False,'quote':'','fact_ids':[],'missing_premises':[],'reason':'다른 주제'} for c in data['candidates']]}
  answer=chat_pipeline.answer(audit,'품목정보가 누락된다면 어떤 리스크가 있어?',retrieve=lambda *a:{'passages':[p]},assess=reject,on_token=emitted.append,generate=lambda *a:self.fail('rejected source used for generation'))
  self.assertNotIn('새 기준서',answer['answer']);self.assertNotIn('전혀 다른', ''.join(emitted))
  self.assertFalse(any(c['kind']=='standard' for c in answer['citations']))
  self.assertIn('발견하지 못할 가능성',answer['answer'])
 def test_exact_lookup_does_not_require_case_relevance(self):
  import chat_pipeline
  p={'id':'exact','title':'원문','text':'요청한 문단의 원문','metadata':{'paragraph':'9'}}
  def fail(*a):self.fail('Exact lookup must not call semantic adjudication')
  answer=chat_pipeline.answer({},'1002호 문단 9가 뭐야?',retrieve=lambda *a:{'passages':[p],'method':'exact_metadata_lookup'},assess=fail)
  self.assertIn(p['text'],answer['answer'])
if __name__=='__main__':unittest.main()
