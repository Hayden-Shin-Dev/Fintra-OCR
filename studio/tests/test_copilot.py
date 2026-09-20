# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from copilot import compose,currency_consistent,normalize_numbers

class CopilotTests(unittest.TestCase):
    def setUp(self):
        self.c={'id':'check-1','kind':'check','check':{'title':'금액 비교','status':'flag','values':{'difference':'17.00'},'context':{'comparison_unit':'USD'},'evidence':[]}}
    def test_numeric_format_is_equivalent_for_validation(self):
        self.assertEqual(normalize_numbers('3,200.00 USD'),normalize_numbers('3200 USD'))
        self.assertNotEqual(normalize_numbers('3,200 USD'),normalize_numbers('3200 KRW'))
    def test_rejected_generation_is_repaired_once(self):
        b={'kind':'draft','text':'금액 차이는 추가 확인이 필요합니다.','sources':['e0']}
        model=Mock(side_effect=[{'blocks':[b]},{'approved':[False],'reason':'수정 필요'},{'blocks':[b]},{'approved':[True],'reason':'일치'}])
        self.assertEqual(len(compose('메모',[],[self.c],'draft',model)['blocks']),1)
        self.assertEqual(model.call_count,4)
    def test_currency_cannot_change_in_generated_text(self):
        self.assertFalse(currency_consistent('17.00 원 차이',[self.c]))
        self.assertTrue(currency_consistent('17.00 USD 차이',[self.c]))
    def test_accounting_explanation_requires_knowledge_source(self):
        model=Mock(return_value={'blocks':[{'kind':'explanation','text':'수익 원칙은 ...','sources':['e0']}]})
        result=compose('수익 원칙은?',[],[self.c],'knowledge',model)
        self.assertEqual(result['blocks'],[])
    def test_conditional_risk_keeps_source_and_status(self):
        b={'kind':'risk','condition':'실물 차이가 확인된 경우','text':'실물 차이가 확인된다면 재고 금액을 검토해야 합니다.','sources':['e0']}
        model=Mock(side_effect=[{'blocks':[b]},{'approved':[True],'reason':'조건부 검토'}])
        with patch.dict('os.environ',{'FINTRA_CHAT_API_URL':'https://configured.example/api'}):
            result=compose('어떤 위험?',[],[self.c,{'id':'standard','kind':'standard','title':'검토 기준','quote':'조건부 검토','source':{'source_type':'회계기준'}}],'risk',model)
        self.assertEqual(result['blocks'][0]['kind'],'risk');self.assertEqual(self.c['check']['status'],'flag')
    def test_unreliable_local_risk_is_not_presented_as_advice(self):
        b={'kind':'risk','condition':'추가 확인 시','text':'조건부 위험','sources':['e0']}
        model=Mock(side_effect=[{'blocks':[b]},{'approved':[True],'reason':'일치'}])
        with patch.dict('os.environ',{'FINTRA_CHAT_API_URL':''}):
            result=compose('위험?',[],[self.c],'risk',model)
        self.assertEqual(result['blocks'],[])
        self.assertEqual(result['validation'],'risk_interpretation_unverified')
    def test_unknown_citation_rejected(self):
        model=Mock(return_value={'blocks':[{'kind':'draft','text':'메모','sources':['not-present']}]})
        self.assertEqual(compose('메모',[],[self.c],'draft',model)['blocks'],[])
    def test_report_context_only_sent_for_report_questions(self):
        for question,expected in [('필요한 자료는?',False),('보고서 문단을 수정해줘',True)]:
            model=Mock(return_value={'blocks':[]})
            compose(question,[],[self.c],'draft',model,workspace_context={'report':{'text':'REPORT_CONTEXT_MARKER'}})
            self.assertEqual('REPORT_CONTEXT_MARKER' in model.call_args_list[0].args[0],expected)
    def test_verifier_rejects_only_unsupported_block(self):
        model=Mock(side_effect=[{'blocks':[{'kind':'procedure','text':'계약 자료를 확인하세요.','sources':['e0']},{'kind':'procedure','text':'확인을 완료했습니다.','sources':['e0']}]},{'approved':[True,False]}])
        result=compose('다음 절차',[],[self.c],'procedure',model)
        self.assertEqual(len(result['blocks']),1);self.assertEqual(result['blocks'][0]['kind'],'procedure');self.assertEqual(result['blocks'][0]['citation_ids'],['check-1'])

if __name__=='__main__':unittest.main()
