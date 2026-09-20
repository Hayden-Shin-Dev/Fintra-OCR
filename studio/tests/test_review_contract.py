# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from review_rules import build,normalized_audit,unit_for
from standard_eligibility import mapping,allowed
import audit_research,grounded_chat,workpapers

class ReviewContractTests(unittest.TestCase):
 def check(self,kind='ledger_invoice_currency_comparison',status='pass',field='currency',value='USD'):
  return {'check_id':'c','type':kind,'title':'검사','status':status,'values':{},'evidence':[{'field_name':field,'normalized_value':value,'source':{'entity_id':'invoice'}}]}
 def test_currency_match_never_searches_standards(self):
  for status in ('pass','flag','cannot_evaluate'):
   search=Mock(side_effect=AssertionError('unexpected search'))
   refs,trace=audit_research.retrieve('USD 외화', [self.check(status=status)],'K-IFRS',search,Mock(),purpose='report')
   self.assertEqual(refs,[]);search.assert_not_called()
 def test_special_standards_are_ineligible(self):
  gate=mapping([self.check('item_quantity_comparison','flag','quantity','2')])
  for title in ['K-IFRS 제1007호 현금흐름표','K-IFRS 제2122호 외화 거래와 선지급·선수취 대가','K-IFRS 제1021호 환율변동효과']:
   self.assertFalse(allowed({'title':title},gate))
  self.assertTrue(allowed({'title':'K-IFRS 제1002호 재고자산'},gate))
 def test_unknown_rule_cannot_be_counted_as_pass(self):
  r=build({'transactions':[{'transaction_id':'t','checks':[self.check('future_rule')]}]})
  self.assertEqual(r['transactions'][0]['overall_status'],'REVIEW')
 def test_optional_absence_does_not_erase_required(self):
  required=self.check('item_quantity_comparison','cannot_evaluate','quantity',None);required['reason']='value_or_unit_missing'
  optional=self.check('item_gross_weight_comparison','cannot_evaluate','gross_weight',None);optional.update(check_id='optional',reason='value_or_unit_missing')
  r=build({'transactions':[{'transaction_id':'t','checks':[required,optional]}]})['transactions'][0]
  self.assertEqual(r['overall_status'],'MISSING');self.assertEqual(r['not_applicable'],['optional']);self.assertEqual(len(r['missing_required']),1)
 def test_pair_checks_group_to_one_area(self):
  cs=[dict(self.check('reference_invoice_number'),check_id=str(i)) for i in range(3)]
  r=build({'transactions':[{'transaction_id':'t','checks':cs}]})['transactions'][0]
  self.assertEqual(len(r['review_areas']),1);self.assertEqual(len(r['review_areas'][0]['groups']),1)
 def test_correct_quantity_unit_and_keep_raw_immutable(self):
  c=self.check('item_quantity_comparison','pass','quantity','40');c['context']={'comparison_unit':'CARTON'};c['evidence'].append({'field_name':'unit','normalized_value':'PCS'})
  a={'transactions':[{'transaction_id':'t','checks':[c]}]};raw=copy.deepcopy(a)
  self.assertEqual(normalized_audit(a)['transactions'][0]['checks'][0]['context']['comparison_unit'],'PCS');self.assertEqual(a,raw)
 def test_all_pass_report_does_not_force_search_or_ai(self):
  data={'documents':[],'audit':{'transactions':[{'transaction_id':'t','checks':[self.check()]}]}}
  ask=Mock(side_effect=AssertionError('unnecessary LLM'));search=Mock(side_effect=AssertionError('unnecessary retrieval'))
  r=workpapers.generate(data,{},ask=ask,search=search)
  self.assertEqual(r['facts']['references'],[]);self.assertEqual(r['generation']['status'],'complete');ask.assert_not_called();search.assert_not_called()
 def test_explicit_transaction_facts_bypass_llm(self):
  c=self.check('ledger_invoice_amount_comparison','pass','amount','3325');c['evidence'] += [{'field_name':'total_amount','normalized_value':'3325','source':{'entity_id':'invoice'}}]
  a={'transactions':[{'transaction_id':'t','ledger':{'fields':{'transaction_id':{'value':'TX013'}}},'checks':[c]}]}
  with patch.object(grounded_chat,'model',side_effect=AssertionError('unnecessary LLM')),patch('enrichment.request',side_effect=AssertionError('unnecessary search')):
   r=grounded_chat.answer(a,'TX013 금액은 왜 정상이라고 판단했어?');self.assertIn('3325',r['answer'])
   r=grounded_chat.answer(a,'TX999 금액은 얼마야?');self.assertIn('없습니다',r['answer']);self.assertNotIn('3325',r['answer'])

 def test_general_concept_available_without_transaction_or_search(self):
  with patch.object(grounded_chat,'model',side_effect=AssertionError('unnecessary LLM')),patch('enrichment.request',side_effect=AssertionError('unnecessary retrieval')):
   r=grounded_chat.answer({},'매출채권이 뭐야?',platform_context={'stage':'upload'})
  self.assertIn('받을 권리',r['answer']);self.assertEqual(r['citations'],[])

if __name__=='__main__':unittest.main()
