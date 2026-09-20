# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import grounded_chat
from amount_assistance import amount_risk,eligible

class AmountAssistanceTests(unittest.TestCase):
    def check(self,a,b):
        return {'type':'ledger_invoice_amount_comparison','check_id':'unseen','status':'flag','title':'금액 비교','context':{'comparison_unit':'EUR'},'evidence':[{'field_name':'amount','normalized_value':a},{'field_name':'total_amount','normalized_value':b}]}
    def test_unseen_amounts_and_negative_direction(self):
        c=self.check('890.25','901.50');before=json.dumps(c)
        r=amount_risk([c],None,lambda *args:{'results':[]})
        self.assertIn('11.25 EUR',r['answer']);self.assertIn('더 작습니다',r['answer'])
        self.assertIn('매출',r['answer']);self.assertIn('매입',r['answer']);self.assertIn('조건:',r['answer'])
        self.assertEqual(json.dumps(c),before)
    def test_lease_consultation_and_wrong_framework_excluded(self):
        source={'source_type':'회계사상담','framework':'K-IFRS','title':'리스 거래가격','text':'거래가격을 산정할 때 받을 금액'}
        self.assertFalse(eligible(source,'revenue','K-IFRS'))
        source.update(source_type='회계기준',title='KIFRS 제1115호 고객과의 계약에서 생기는 수익')
        self.assertTrue(eligible(source,'revenue','K-IFRS'))
        self.assertFalse(eligible(source,'revenue','일반기업회계기준'))
    def test_real_source_link_and_no_raw_dump(self):
        source={'id':'s','source_type':'회계기준','framework':'K-IFRS','title':'KIFRS 제1115호 고객과의 계약에서 생기는 수익','text':'거래가격을 산정함. 받을 권리가 있는 대가.','source':{'char_start':0,'char_end':30}}
        r=amount_risk([self.check('45','40')], 'K-IFRS',lambda *args:{'results':[source]})
        refs=[c for c in r['citations'] if c['kind']=='standard'];self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]['quote'],source['text']);self.assertEqual(refs[0]['applicability'],'conditional')
        self.assertNotIn(source['text'],r['answer'])
    def test_unrelated_or_matching_check_not_treated_as_amount_risk(self):
        c=self.check('4','4');c['status']='pass'
        self.assertIsNone(amount_risk([c],None,Mock()))
        c.update(status='flag',type='gross_weight_comparison')
        self.assertIsNone(amount_risk([c],None,Mock()))
    def test_service_search_limit_and_stage_guard(self):
        calls=[]
        amount_risk([self.check('10','9')],None,lambda path,data:(calls.append(data) or {'results':[]}))
        self.assertTrue(all(1<=c['top_k']<=20 for c in calls))
        with patch('workspace_chat.respond',return_value={'answer':'자료 준비 단계','domain':'workspace','topic':'stage'}),patch('grounded_chat.enrichment.request') as search:
            audit={'transactions':[{'transaction_id':'x','checks':[self.check('10','9')]}]}
            r=grounded_chat.answer(audit,'리스크가 뭐야',platform_context={'stage':'upload'})
            self.assertEqual(r['answer'],'자료 준비 단계');search.assert_not_called()

    def test_truncated_model_response_retried_once(self):
        first=Mock();first.__enter__=Mock(return_value=first);first.__exit__=Mock(return_value=False)
        second=Mock();second.__enter__=Mock(return_value=second);second.__exit__=Mock(return_value=False)
        with patch.dict('os.environ',{'FINTRA_CHAT_API_URL':''}),patch.object(grounded_chat,'urlopen',side_effect=[first,second]) as call,patch.object(grounded_chat.json,'load',side_effect=[{'done_reason':'length','message':{'content':'{"unfinished'}},{'done_reason':'stop','message':{'content':'{"answer":"완료"}'}}]):
            self.assertEqual(grounded_chat.model('test',{},{}),{'answer':'완료'})
            self.assertEqual(call.call_count,2)
            self.assertGreater(json.loads(call.call_args_list[1].args[0].data)['options']['num_predict'],json.loads(call.call_args_list[0].args[0].data)['options']['num_predict'])

    def test_reasoning_request_reaches_local_provider(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch.dict('os.environ',{'FINTRA_CHAT_API_URL':''}),patch.object(grounded_chat,'urlopen',return_value=response) as call,patch.object(grounded_chat.json,'load',return_value={'done_reason':'stop','message':{'content':'{}'}}):
            grounded_chat.model('test',{}, {},reasoning=True)
            payload=json.loads(call.call_args.args[0].data)
            self.assertIs(payload['think'],True)
            self.assertGreater(payload['options']['num_predict'],2800)

if __name__=='__main__':unittest.main()
