# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from accounting_scope import subjects,allows_amount_shortcut,scope
from audit_research import retrieve,standard_body,applicable_passage
from claim_validation import validate

class AccountingScopeTests(unittest.TestCase):
    def test_short_followup_keeps_freight_subject_even_if_planner_omits_query(self):
        from accounting_scope import followup_queries
        prior=[{'question':'운임의 회계처리는?'}]
        queries=followup_queries('그럼 이 금액은 어떻게 확인해?',prior,[])
        self.assertIn('운임',queries[0])
        self.assertFalse(allows_amount_shortcut('그럼 이 금액은 어떻게 확인해?',queries))
        self.assertEqual(followup_queries('장부와 송장 차이를 설명해',prior,[]),[])
    def test_logistics_questions_select_relevant_topics_before_amount_shortcut(self):
        for question,topic in [('운임과 보험료도 송장 금액에 더해야 해?','logistics_cost'),('FOB 인도조건이면 언제 매출인가요?','delivery'),('반품이 발생하면?','returns'),('운송 용역의 수익은 언제 인식하나요?','transport_service')]:
            with self.subTest(question=question):
                self.assertIn(topic,scope(question,[],lambda c:'amount')[0])
                self.assertFalse(allows_amount_shortcut(question))
    def test_framework_whitespace_is_not_a_different_framework(self):
        ref={'kind':'standard','quote':'재고자산 매입원가 원칙','source':{'framework':'일반 기업 회계 기준'}}
        self.assertEqual(validate('일반기업회계기준에 따른 원가 검토',[ref]),[])
        self.assertTrue(validate('K-IFRS에 따른 원가 검토',[ref]))
    def test_delivery_search_accepts_normative_control_language(self):
        from audit_research import focused_body
        body='고객에게 약속한 자산의 통제를 이전하여 수행의무를 이행할 때 수익을 인식한다.'
        self.assertEqual(focused_body(body,['delivery'],'FOB 거래의 인도조건은?'),body)
    def test_followup_uses_resolved_conversation_topic_before_screen(self):
        topics,queries,explicit=scope('그럼 추정을 못하면?', [{'title':'금액 비교'}],lambda c:'amount',['충당부채 신뢰성 있는 추정'])
        self.assertEqual(topics,['provision']);self.assertFalse(explicit)
        self.assertFalse(allows_amount_shortcut('그럼 위험은?', ['충당부채 인식']))
        self.assertTrue(allows_amount_shortcut('장부와 송장 금액 차이의 위험은?', ['충당부채 인식']))
        self.assertFalse(allows_amount_shortcut('그럼 금액을 추정하지 못하면?', ['충당부채 신뢰성 있는 추정']))
        self.assertEqual(scope('그럼 금액을 추정하지 못하면?', [],lambda c:'amount',['충당부채 신뢰성 있는 추정'])[0],['provision'])
    def test_explicit_lease_overrides_amount_screen(self):
        calls=[]
        rows=[{'id':'lease','title':'리스','text':'리스이용자는 사용권자산과 리스부채를 인식한다. '+('리스의 적용 조건을 확인한다. '*4),'framework':'K-IFRS','source_type':'회계기준','source':{'char_start':0,'char_end':300}},
              {'id':'amount','title':'수익','text':'판매대가 및 거래가격의 측정에 대한 일반 원칙이다. '*5,'framework':'K-IFRS','source_type':'회계기준','source':{'char_start':0,'char_end':300}}]
        def search(path,payload):calls.append(payload['query']);return {'results':rows}
        def model(prompt,data,schema):
            self.assertEqual([s['title'] for s in data['sources'].values()],['리스'])
            return {'selected':[{'key':'s0','condition':'거래 성격 및 적용 요건 확인'}]}
        refs,trace=retrieve('리스의 최초 인식을 설명해줘',[{'evidence':[{'field_name':'amount'}]}],'K-IFRS',search,model)
        self.assertEqual(refs[0]['id'],'lease');self.assertTrue(trace['explicit_subject'])
        self.assertIn('리스의 최초 인식을 설명해줘',calls)
        self.assertFalse(allows_amount_shortcut('리스부채 금액의 위험은?'))

    def test_accounting_topics_are_not_blanket_excluded(self):
        for question,expected in [('정부보조금은?','grant'),('사업결합의 영업권은?','combination'),('생물자산 측정','agriculture'),('이연법인세','tax'),('외화환산','fx'),('충당부채 인식','provision'),('개발비 처리','intangible'),('현금흐름 분류','cashflow'),('퇴직급여','employee')]:
            with self.subTest(question=question):self.assertIn(expected,subjects(question))

    def test_preserve_normative_bullets_remove_related_links(self):
        body=standard_body('원칙\n- 첫 번째 요건\n- 두 번째 요건\n관련 질의회신\n- 상담 링크')
        self.assertIn('두 번째 요건',body);self.assertNotIn('상담 링크',body)
        self.assertIn('후속 측정 원칙',standard_body('관련 질의회신\n- 상담(2020-01-01)\n\n후속 측정 원칙'))

    def test_transition_exception_is_not_general_initial_recognition(self):
        source={'title':'리스','text':'C8\n최초 적용일에 리스부채를 인식한다.'}
        self.assertFalse(applicable_passage(source,'리스부채의 최초 인식 원칙'))
        self.assertTrue(applicable_passage(source,'리스 최초 적용 전환 규정'))
        self.assertFalse(applicable_passage({'title':'목적','text':'라2 법인세 자산을 인식하지 아니한다.'},'법인세 원칙'))
        self.assertNotIn('질문',standard_body('- 질문(2023-01-01)'))
        self.assertFalse(applicable_passage({'title':'리스','text':'개시일 후에 리스부채를 다시 측정한다.'},'최초 인식'))

    def test_model_approval_cannot_supply_missing_facts(self):
        refs=[{'kind':'standard','quote':'K-IFRS 제1115호의 거래가격 원칙','source':{'framework':'K-IFRS'}}]
        for text in ['차이는 900 USD입니다.','IAS 16에 따라 처리합니다.','일반기업회계기준에 따라 처리합니다.','재고 실사를 완료했습니다.','횡령이 발생했습니다.']:
            with self.subTest(text=text):self.assertTrue(validate(text,refs,'risk'))
        self.assertEqual(validate('K-IFRS 제1115호의 거래가격을 검토하세요.',refs),[])
        titled=[{'kind':'standard','title':'K-IFRS 제1115호 고객과의 계약에서 생기는 수익',
                 'relevant_text':'거래가격을 산정하기 위해서는 계약 조건을 참고한다.',
                 'source':{'framework':'K-IFRS'}}]
        self.assertEqual(validate('K-IFRS 제1115호의 거래가격을 검토하세요.',titled),[])
        self.assertTrue(validate('K-IFRS 제1002호에 따라 처리하세요.',titled))
        self.assertEqual(validate('회계 오류로 확정할 수 없습니다.',refs,'risk'),[])
        self.assertEqual(validate('부정은 입증되지 않았습니다.',refs,'risk'),[])
        self.assertTrue(validate('부정이 입증되었습니다.',refs,'risk'))

if __name__=='__main__':unittest.main()
