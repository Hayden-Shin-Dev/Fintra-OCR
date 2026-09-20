# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from logistics_writer import interpret

class LogisticsWriterTests(unittest.TestCase):
 def test_model_cannot_author_an_unsafe_procedure_or_finished_audit(self):
  ref={'id':'r','kind':'standard','title':'매입원가','quote':'할인은 매입원가에서 차감한다.'}
  check={'status':'flag','evidence':[{'field_name':'amount'}]}
  with patch('logistics_writer.compose',return_value={'blocks':[],'validation':'rejected'}):
   text,refs,verdict=interpret('금액',[check],[ref],None)
  self.assertIn('이미 포함',text);self.assertIn('중복 차감하지 않는다',text)
  self.assertIn('AI 해설 대신',text);self.assertIn(ref['quote'],text)
  self.assertEqual(verdict['method'],'original_passages');self.assertTrue(verdict['requires_reviewer'])
 def test_quantity_program_does_not_treat_document_difference_as_stock_loss(self):
  text,_,v=interpret('수량',[{'status':'flag','evidence':[{'field_name':'quantity'}]}],[],None)
  self.assertIn('문서 차이만으로 감모를 확정하지 않는다',text)
  self.assertIn('품목 코드·단위·포장 환산',text)
  self.assertEqual(v['method'],'evidence_only')
 def test_matching_values_do_not_produce_clean_opinion(self):
  text,_,_=interpret('날짜',[{'status':'pass','evidence':[{'field_name':'invoice_date'}]}],[],None)
  self.assertIn('인도조건 하나만으로',text)
  self.assertIn('적정성 또는 오류를 확정하지 않는다',text)
 def test_ai_explanation_preserves_citation(self):
  ref={'id':'r','kind':'standard','title':'관련 기준','quote':'원문'}
  with patch('logistics_writer.compose',return_value={'blocks':[{'text':'검증된 설명','citation_ids':['r']}],'validation':'verified'}):
   text,_,v=interpret('금액',[{'status':'review','evidence':[{'field_name':'amount'}]}],[ref],None)
  self.assertIn('검증된 설명\n근거: 관련 기준',text)
  self.assertEqual(v['method'],'source_bound_ai_explanation')

if __name__=='__main__':unittest.main()
