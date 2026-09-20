# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from knowledge_answer import compose
from source_context import expand

class KnowledgeAnswerTests(unittest.TestCase):
    def source(self):
        return {'id':'original','kind':'standard','title':'리스','source':{'framework':'K-IFRS'},
                'quote':'리스이용자는 리스개시일에 사용권자산과 리스부채를 인식한다.'}
    def test_hallucinated_quote_never_reaches_semantic_approval(self):
        calls=[]
        def model(prompt,data,schema):
            calls.append(data)
            return {'claims':[{'text':'리스부채를 인식한다.','source':'e0','quote':'계약일에 모든 금액을 즉시 비용으로 처리한다.'}]}
        result=compose('리스부채의 최초 인식',[],[self.source()],model)
        self.assertFalse(result['blocks']);self.assertEqual(len(calls),3)
    def test_other_account_cannot_replace_opening_answer(self):
        def model(prompt,data,schema):
            self.assertIn('passages',data)
            return {'claims':[{'text':'사용권자산을 인식한다.','source':'e0','quote':self.source()['quote']}]}
        self.assertFalse(compose('리스부채의 최초 인식',[],[self.source()],model)['blocks'])
    def test_rejected_primary_answer_does_not_return_side_detail(self):
        def model(prompt,data,schema):
            if 'passages' in data:return {'claims':[{'text':'리스부채를 인식한다.','source':'e0','quote':self.source()['quote']}]}
            return {'approved':[False],'reason':'질문한 시점을 설명해야 합니다.'}
        self.assertFalse(compose('리스부채의 최초 인식',[],[self.source()],model)['blocks'])
    def test_exception_cannot_be_stripped_from_parent_paragraph(self):
        source=self.source();source['quote']+=' 다만, 원문에 정한 예외는 제외한다.'
        def model(prompt,data,schema):
            self.assertIn('passages',data)
            return {'claims':[{'text':'모든 리스부채를 인식한다.','source':'e0','quote':self.source()['quote']}]}
        self.assertFalse(compose('리스부채의 최초 인식',[],[source],model)['blocks'])
    def test_invalid_opening_is_not_replaced_by_valid_secondary_claim(self):
        def model(prompt,data,schema):
            self.assertIn('passages',data)
            return {'claims':[{'text':'리스부채를 인식한다.','source':'missing'},
                              {'text':'리스부채의 보충 설명입니다.','source':'e0'}]}
        self.assertFalse(compose('리스부채의 최초 인식',[],[self.source()],model)['blocks'])
    def test_quote_is_copied_from_source_not_generated(self):
        def model(prompt,data,schema):
            if 'passages' in data:return {'claims':[{'text':self.source()['quote'],'source':'e0'}]}
            return {'approved':[True],'complete':True,'reason':'원문과 일치'}
        result=compose('리스부채의 최초 인식',[],[self.source()],model)
        self.assertEqual(result['blocks'][0]['supporting_quote'],self.source()['quote'])
    def test_true_individual_claims_do_not_hide_missing_conditions(self):
        def model(prompt,data,schema):
            if 'passages' in data:return {'claims':[{'text':self.source()['quote'],'source':'e0'}]}
            return {'approved':[True],'complete':False,'reason':'필수 조건 누락'}
        result=compose('리스부채의 최초 인식',[],[self.source()],model)
        self.assertFalse(result['blocks']);self.assertIn('필수 조건 누락',result['reasons'])
    def test_model_approval_cannot_override_required_source_coverage(self):
        required=dict(self.source(),id='condition',required_for_question=True,
                      quote='신뢰성 있게 추정할 수 없는 때에는 부채로 인식하지 않고 우발부채로 공시한다.')
        def model(prompt,data,schema):
            if 'passages' in data:return {'claims':[{'text':self.source()['quote'],'source':'e0'}]}
            return {'approved':[True],'complete':True,'reason':'승인'}
        result=compose('리스부채의 인식 조건은?',[],[self.source(),required],model)
        self.assertFalse(result['blocks']);self.assertIn('필수 인식 제외 조건',result['reasons'][0])
    def test_required_condition_has_its_own_constrained_output_slot(self):
        required=dict(self.source(),id='condition',required_for_question=True,
                      quote='신뢰성 있게 추정할 수 없는 때에는 부채로 인식하지 않고 우발부채로 공시한다.')
        def model(prompt,data,schema):
            if 'passages' in data:
                self.assertIn('required_conditions',schema['required'])
                slots=schema['properties']['required_conditions']
                self.assertEqual(slots['properties']['condition_0']['properties']['source']['enum'],['e1'])
                return {'claims':[{'text':self.source()['quote'],'source':'e0'}],
                        'required_conditions':{'condition_0':{'text':required['quote'],'source':'e1'}}}
            return {'approved':[True,True],'complete':True,'reason':'원문과 일치'}
        result=compose('리스부채의 인식 조건은?',[],[self.source(),required],model)
        self.assertEqual(len(result['blocks']),2)
    def test_answer_can_name_specific_subtopic_without_repeating_parent(self):
        from knowledge_answer import addresses_target
        self.assertTrue(addresses_target('무형자산의 연구 지출은 어떻게 처리하나요?', '연구 지출은 발생시점에 비용으로 인식한다.', 'K-IFRS 제1038호 무형자산'))
        self.assertFalse(addresses_target('리스부채의 최초 인식', '사용권자산을 인식한다.', 'K-IFRS 제1116호 리스부채'))
    def test_heading_alone_is_not_a_substantive_standard_passage(self):
        from audit_research import focused_body
        self.assertEqual(focused_body('K-IFRS 제2032호 무형자산 웹 사이트 원가', ['intangible'], '무형자산의 연구 지출'), '')
    def test_parent_expansion_restores_truncated_condition_and_offsets(self):
        full='미래 과세소득이 발생할 가능성이 높다면 자산을 인식한다.\n\n다음 문단도 보존한다.'
        start=full.index('능성이');end=full.index('\n\n')
        s={'text':full[start:end],'source':{'record_id':'r','json_pointer':'/document/content/0/content_text','char_start':start,'char_end':end}}
        result=expand(s,lambda *a:{'document':{'content':[{'content_text':full}]}},{})
        self.assertEqual(result['text'],full)
        self.assertEqual(full[result['source']['char_start']:result['source']['char_end']],result['text'])
        with self.assertRaises(ValueError):expand(dict(s,text='변조됨'),lambda *a:{'document':{'content':[{'content_text':full}]}},{})
    def test_case_hidden_outside_search_chunk_is_excluded(self):
        from audit_research import retrieve
        full='K-IFRS 제1037호 충당부채\n\n사례 10 소송사건\n\n충당부채를 인식한다. 실제 사례의 결론이다.'
        start=full.index('충당부채를')
        source={'id':'case','title':'K-IFRS 제1037호','source_type':'회계기준','framework':'K-IFRS',
                'text':full[start:],'source':{'record_id':'r','json_pointer':'/document/content/0/content_text','char_start':start,'char_end':len(full)}}
        def request(path,data):
            if path=='/search':
                self.assertEqual(data['source_types'],['회계기준'])
                return {'results':[source]}
            return {'document':{'content':[{'content_text':full}]}}
        def model(*args):raise AssertionError('A hidden case cannot reach the generator')
        refs,_=retrieve('충당부채의 인식 조건은?',[],'K-IFRS',request,model)
        self.assertEqual(refs,[])
    def test_recognition_exclusion_survives_selector_omission(self):
        from audit_research import retrieve
        texts=['충당부채를 인식하기 위해서는 현재의무가 존재해야 하며 자원 유출 가능성이 높아야 한다.',
               '충당부채 금액을 신뢰성 있게 추정할 수 없는 때에는 부채로 인식하지 않고 우발부채로 공시한다.']
        rows=[{'id':str(i),'title':'K-IFRS 제1037호 충당부채','source_type':'회계기준','framework':'K-IFRS','text':t,
               'source':{'record_id':str(i),'json_pointer':'/document/content/0/content_text','char_start':0,'char_end':len(t)}} for i,t in enumerate(texts)]
        def request(path,data):
            return {'results':rows} if path=='/search' else {'document':{'content':[{'content_text':texts[int(data['record_id'])]}]}}
        refs,_=retrieve('충당부채의 인식 조건은?',[],'K-IFRS',request,lambda *a:{'selected':[{'key':'s0'}]})
        self.assertEqual({r['id'] for r in refs},{'0','1'})
if __name__=='__main__':unittest.main()
