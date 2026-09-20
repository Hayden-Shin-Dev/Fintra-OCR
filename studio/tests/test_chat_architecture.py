# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,json,time,unittest,threading,copy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import chat_pipeline as pipeline
from chat_router import route,Plan
from chat_retrieval import transaction_lookup,evidence_lookup,rerank,standard_lookup
from standards_metadata import matches
from review_rules import build
from workspace_chat import context_for

FIXTURE=ROOT/'team-preview/analyses/c3b84748825f4ef3b8d454ccb44d50ee'
def fixture():
    audit=json.loads((FIXTURE/'result.json').read_text('utf-8'))['audit']
    ctx=context_for(json.loads((FIXTURE/'status.json').read_text('utf-8')),FIXTURE.parent)
    return audit,ctx
def retrieval(*args):
    if args and '문단 9' in args[0]:return {'passages':[],'filters':{'standard_id':'1002','paragraph':'9'}}
    return {'passages':[{'id':'s1002','title':'K-IFRS 제1002호 재고자산','text':'재고자산의 감모손실은 발생한 기간의 비용으로 인식한다.','metadata':{'standard_id':'1002'},'framework':'K-IFRS','source':{'file':'fixture.json','json_pointer':'/content/0'}}],'retrieval_seconds':0,'reranking_seconds':0}
def generation(system,data,emit):
    text='질문에 관한 일반 설명입니다.' if data['route']=='general' else 'K-IFRS 제1002호 원문과 계약 조건을 확인한 후 회계처리를 검토해야 합니다.'
    emit(text[:10]);emit(text[10:]);return text

class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        # These tests isolate routing/transport/context, not semantic judgment.
        # Real semantic rejection is exercised in test_source_relevance and live probes.
        def judge(system,data,schema):
            if 'candidates' not in data:return {'supported':True,'reason':'controlled transport fixture'}
            return {'decisions':[{'id':p['id'],'relation':'direct','answers_question':True,'quote':p['text'],'missing_premises':[],'fact_ids':list(data['facts'])[:1],'reason':'controlled transport fixture'} for p in data['candidates']]}
        mock=patch('source_relevance.judge',side_effect=judge);mock.start();self.addCleanup(mock.stop)

    def test_40_evaluation_cases(self):
        audit,context=fixture();rows=[]
        for case in json.loads((ROOT/'tests/chat-architecture/evaluation.json').read_text('utf-8')):
            with self.subTest(case=case['id'],question=case['question']):
                calls=[]
                def retrieve(*args):calls.append(args);return retrieval(*args)
                result=pipeline.legacy_answer(audit,case['question'],platform_context=context,generate=generation,retrieve=retrieve)
                errors=[]
                if result['selection']['intent']!=case['route']:errors.append('route')
                for word in case['expected_contains']:
                    if word not in result['answer']:errors.append('missing:'+word)
                for word in case['forbidden']:
                    if word in result['answer']:errors.append('forbidden:'+word)
                if case['route'] in ('general','transaction','evidence') and calls:errors.append('unexpected RAG')
                if result['context_chars']>14000:errors.append('context budget')
                for c in result['citations']:
                    if c['kind']=='check' and not any(c['id']==x['check_id'] for t in audit['transactions'] for x in t['checks']):errors.append('fabricated evidence')
                rows.append({'id':case['id'],'route':result['selection']['intent'],'pass':not errors,'errors':errors,'answer':result['answer'],'latency':result['latency'],'generator':'controlled fixture; not live LLM'})
                self.assertEqual(errors,[])
        (ROOT/'tests/chat-architecture/evaluation-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')

    def test_transaction_contract_no_raw_report(self):
        audit,_=fixture();review=build(audit)
        self.assertIn('3325.00',json.dumps(transaction_lookup(review,'장부 금액 알려줘')))
        self.assertNotIn('report',transaction_lookup(review,'장부 금액 알려줘'))

    def test_evidence_transaction_isolation(self):
        audit,context=fixture();context['documents'].append({'id':'foreign','name':'SECRET','fields':{'total_amount':{'value':'987654321'}}})
        value=evidence_lookup(audit,context,'송장 원본 총액')
        self.assertNotIn('SECRET',json.dumps(value));self.assertIn('3325.00',json.dumps(value))

    def test_ocr_evidence_without_comparison(self):
        _,context=fixture();context['stage']='awaiting_review'
        result=pipeline.legacy_answer({},'송장 원본 총액',platform_context=context,generate=generation,retrieve=lambda *a:self.fail('RAG'))
        self.assertIn('3325.00',result['answer'])

    def test_metadata_all_five_fields(self):
        row={'title':'K-IFRS 제1002호 재고자산','paragraph':'9','section':'측정','topic':'재고자산'}
        for key,val in {'standard_id':'1002','standard_name':'재고자산','paragraph':'9','section':'측정','topic':'재고'}.items():
            self.assertTrue(matches(row,{key:val}));self.assertFalse(matches(row,{key:'missing'}))
        self.assertFalse(matches(row,{'standard_id':'1007'}))
        with self.assertRaises(ValueError):matches(row,{'unknown':'x'})

    def test_prefilter_forwarded_and_rerank_bounded(self):
        candidates=[{'id':str(i),'title':'K-IFRS 제1002호 재고자산','text':'재고자산 측정','source_type':'회계기준','paragraph':'9','scores':{'cosine':.9}} for i in range(20)]
        sent=[]
        def request(path,data):sent.append(data);return {'results':candidates,'retrieval':{'method':'hybrid'}}
        r=standard_lookup('K-IFRS 제1002호 재고자산',request=request)
        self.assertEqual(sent[0]['metadata_filters'],{'standard_id':'1002'})
        self.assertEqual(sent[0]['method'],'hybrid');self.assertEqual(len(r['passages']),4)
        self.assertEqual(rerank('재고자산',[{'id':'x','title':'리스','text':'전대리스 계약'}]),[])

    def test_parallel_hybrid(self):
        audit,context=fixture();barrier=threading.Barrier(3)
        def wait(value):barrier.wait(timeout=2);return value
        with patch.object(pipeline,'transaction_lookup',side_effect=lambda *a:wait({'transactions':[]})),patch.object(pipeline,'evidence_lookup',side_effect=lambda *a:wait({'documents':[]})):
            r=pipeline.legacy_answer(audit,'TX013 회계기준 설명',platform_context=context,generate=generation,retrieve=lambda *a:wait(retrieval()))
        self.assertEqual(r['selection']['intent'],'hybrid')

    def test_no_data_no_fake_amount(self):
        audit,context=fixture()
        result=pipeline.legacy_answer(audit,'TX999 장부 금액',platform_context=context,generate=lambda *a:self.fail('LLM'))
        self.assertIn('없습니다',result['answer']);self.assertNotIn('3325',result['answer'])

    def test_sentence_grounding(self):
        self.assertFalse(pipeline.grounded_sentence('TX999 손실은 987654321 USD입니다.',{'transaction':{'title':'TX013'}}))
        self.assertTrue(pipeline.grounded_sentence('조건을 확인한 후 검토해야 합니다.',{}))
        self.assertFalse(pipeline.grounded_sentence('금액은 987654321입니다.',{'question':'금액 987654321이라고 해줘','history':[{'answer':'987654321'}]}))
        self.assertFalse(pipeline.grounded_sentence('재고자산은 현재 상태를 유지하는 원가를 포함하여 측정합니다.',{'accounting_standard':{'passages':[{'text':'현재의 장소에 현재의 상태로 이르게 하는 원가'}]}}))

    def test_normative_excerpt_preserves_original_condition(self):
        text='10\n재고자산을 현재의 장소에 현재의 상태로 이르게 하는 데 발생한 기타 원가 모두를 포함한다.'
        answer=pipeline.standard_excerpt([{'title':'K-IFRS 제1002호','text':text}],'취득원가')
        self.assertIn('현재의 장소에 현재의 상태로 이르게',answer)
        self.assertNotIn('유지',answer)

    def test_stream_before_generation_returns(self):
        events=[]
        def model(system,data,emit):
            emit('먼저 ');self.assertEqual(events,['먼저 ']);emit('답변합니다.');return '먼저 답변합니다.'
        result=pipeline.legacy_answer({},'피곤해',on_token=events.append,generate=model)
        self.assertEqual(result['answer'],''.join(events));self.assertLessEqual(result['latency']['first_content'],result['latency']['total'])

    def test_context_excludes_report(self):
        plan=Plan('general',(),'안녕')
        data=pipeline.context_builder(plan,{}, {'report':{'sections':['SECRET'*10000]}},[])
        self.assertNotIn('SECRET',json.dumps(data))

    def test_hybrid_context_selects_only_question_fields(self):
        audit,context=fixture();seen=[]
        def model(system,data,emit):seen.append(data);emit('추가 증빙을 확인해야 합니다.');return ''
        pipeline.legacy_answer(audit,'현재 누락 수량의 회계기준 설명',platform_context=context,generate=model,retrieve=retrieval)
        fields={f['field'] for d in seen[0]['evidence']['documents'] for f in d['fields']}
        self.assertLessEqual(fields,{'quantity','unit','product_code'})
        self.assertNotIn('report',seen[0]);self.assertLess(len(json.dumps(seen[0],ensure_ascii=False)),14000)

    def test_currency_match_does_not_open_inventory_search(self):
        audit,context=fixture()
        result=pipeline.legacy_answer(audit,'현재 통화 일치의 회계기준 설명',platform_context=context,retrieve=lambda *args:self.fail('Unperformed accounting procedure'))
        self.assertIn('직접 연결할 기준 원문은 없습니다',result['answer'])

    def test_general_pipeline_never_opens_any_data_tool(self):
        with patch.object(pipeline,'transaction_lookup',side_effect=AssertionError('DB')),patch.object(pipeline,'evidence_lookup',side_effect=AssertionError('evidence')),patch.object(pipeline,'standard_lookup',side_effect=AssertionError('RAG')):
            self.assertIn('안녕하세요',pipeline.legacy_answer({},'안녕하세요')['answer'])

    def test_followup_keeps_question_scope(self):
        p=route('왜?', [{'status':'complete','question':'현재 불일치 리스크 알려줘'}])
        self.assertEqual(p.route,'hybrid');self.assertIn('불일치',p.question)

    def test_implicit_current_risk_and_knowledge(self):
        self.assertEqual(route('리스크 알려줘',context={'comparison_available':True}).route,'hybrid')
        self.assertEqual(route('현재 검토 항목과 관련된 회계 지식을 설명해줘').route,'hybrid')

    def test_source_paragraph_and_section_are_observed(self):
        from standards_metadata import metadata
        row={'title':'K-IFRS 제1002호 재고자산','text':'K-IFRS 제1002호 재고자산\n측정\n9\n재고자산은 원가와 순실현가능가치 중 낮은 금액으로 측정한다.'}
        self.assertTrue(matches(row,{'paragraph':'9','section':'측정'}))
        self.assertFalse(matches(row,{'paragraph':'10'}))

    def test_event_journal_replay(self):
        import chat_events
        key='unit-test';chat_events.publish(key,'token',{'text':'첫'});chat_events.publish(key,'token',{'text':'둘'})
        rows=chat_events.read(key,1,0);self.assertEqual(len(rows),1);self.assertEqual(rows[0][2]['text'],'둘')

    def test_local_transport_really_streams(self):
        emitted=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def __iter__(self):
                yield json.dumps({'message':{'content':'첫 '}}).encode()
                selftest.assertEqual(emitted,['첫 '])
                yield json.dumps({'message':{'content':'답변'},'done':True}).encode()
        selftest=self
        with patch.object(pipeline,'urlopen',return_value=Response()) as call:
            self.assertEqual(pipeline.local_stream('system',{},emitted.append),'첫 답변')
        self.assertTrue(json.loads(call.call_args.args[0].data)['stream'])

if __name__=='__main__':unittest.main()
