# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import grounded_chat
from question_route import route
from current_principles import inventory_explanation

class MissingChatTests(unittest.TestCase):
    def setUp(self):
        self.check={'check_id':'missing-quantity','type':'item_quantity_comparison','title':'품목별 상품 수량 비교','status':'cannot_evaluate','evidence':[{'field_name':'quantity','normalized_value':None,'source':{'entity_id':'packing'}}]}
        self.audit={'transactions':[{'transaction_id':'tx','documents':{'packing_list':{'id':'packing','document_type':'packing_list'}},'checks':[self.check]}]}
        self.ref={'id':'standard','kind':'standard','title':'재고자산','source':{'framework':'K-IFRS'},'quote':'감모손실은 발생한 기간에 비용으로 인식한다.'}
    def test_missing_reason_requires_no_model_or_search(self):
        with patch.object(grounded_chat,'model',side_effect=AssertionError('unnecessary inference')),patch('enrichment.request',side_effect=AssertionError('unnecessary retrieval')):
            for q in ['정보 부족으로 남은 이유','왜 정보 부족이야?','어떤 값이 누락됐는지 알려줘']:
                result=grounded_chat.answer(self.audit,q)
                self.assertIn('포장명세서 · 상품 수량',result['answer'])
    def test_principle_selects_missing_evidence(self):
        with patch('audit_research.retrieve',return_value=([self.ref],{})) as retrieve,patch.object(grounded_chat,'model',side_effect=AssertionError('unnecessary inference')):
            result=grounded_chat.answer(self.audit,'현재 검토 항목과 관련된 회계 원칙을 쉽게 설명해줘')
        self.assertEqual(retrieve.call_args.args[1],[self.check])
        self.assertIn('실제로 부족하다고 확인한 상태는 아닙니다',result['answer'])
        self.assertIn('K-IFRS',result['answer'])
        self.assertEqual(len(result['citations']),2)
    def test_general_knowledge_route_includes_missing(self):
        self.assertEqual(route('관련 회계기준 알려줘',{'c0':self.check})['check_ids'],['c0'])
    def test_no_unverified_standard_claim(self):
        self.assertIsNone(inventory_explanation([self.check],[]))
    def test_explicit_other_subject_not_inventory_explanation(self):
        self.assertEqual(route('환율 처리 기준 설명해줘',{'c0':self.check})['check_ids'],[])

if __name__=='__main__':unittest.main()
