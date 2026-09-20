# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import grounded_chat,report_content,server

class ChatReportTests(unittest.TestCase):
    def setUp(self):
        self.check={'check_id':'check-a','title':'총중량 비교','status':'pass','values':{},'evidence':[{'field_name':'gross_weight','normalized_value':'1500','source':{'entity_id':'doc1','file':'doc.json'},'original':{'raw_text':'1,500 KG','evidence':[{'page':1,'token_id':'t1','start':0,'end':5}]}}]}
        self.audit={'transactions':[{'transaction_id':'tx','documents':{'packing_list':{'id':'doc1','document_type':'packing_list'}},'checks':[self.check]}]}
    def test_chat_renders_owned_value_without_mutating_audit(self):
        before=copy.deepcopy(self.audit)
        with patch.object(grounded_chat,'model',return_value={'check_ids':['c0'],'needs_standards':False,'search_queries':[]}):
            r=grounded_chat.answer(self.audit,'총중량은?')
        self.assertIn('1500',r['answer']);self.assertEqual(r['citations'][0]['check'],self.check);self.assertEqual(self.audit,before)
    def test_greeting_uses_conversation_even_without_documents(self):
        with patch.object(grounded_chat,'model',return_value={'domain':'workspace','answer':'안녕하세요. 무엇을 살펴볼까요?'}):
            r=grounded_chat.answer({},'안녕',platform_context={'stage':'upload'})
        self.assertEqual(r['citations'],[]);self.assertNotIn('업로드',r['answer']);self.assertEqual(r['grounding_status'],'platform_context')
    def test_precomparison_never_enters_empty_check_summary(self):
        with patch.object(grounded_chat,'model',return_value={'domain':'workspace','answer':'추출값 확인 단계입니다.'}) as model:
            r=grounded_chat.answer({},'지금 무슨 단계야?',platform_context={'stage':'awaiting_review'})
        self.assertEqual(model.call_count,0);self.assertNotIn('일치 0',r['answer'])
        self.assertIn('추출값 확인',r['answer'])
    def test_workspace_contains_real_corrected_ocr_values(self):
        from workspace_chat import context_for
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'a';folder.mkdir()
            (folder/'doc.json').write_text(json.dumps({'fields':{'total_amount':{'value':'123.45','status':'accepted','raw_text':'123.45'}},'items':[]}), 'utf-8')
            context=context_for({'id':'a','stage':'awaiting_review','document_records':[{'id':'d','result_file':'doc.json'}]},Path(tmp))
            self.assertEqual(context['documents'][0]['fields']['total_amount']['value'],'123.45')
    def test_ocr_numbers_are_rendered_from_named_source_fields(self):
        from workspace_chat import respond
        context={'stage':'awaiting_review','documents':[{'document_type':'bill_of_lading','fields':{'gross_weight':{'value':'360'},'net_weight':{'value':'320'}}}]}
        r=respond('OCR 결과?',[],context,lambda *args:{'domain':'workspace','topic':'ocr','answer':'총중량 320'})
        self.assertIn('총중량: 360',r['answer']);self.assertIn('순중량: 320',r['answer']);self.assertNotIn('총중량 320',r['answer'])
    def test_product_knowledge_is_available_after_comparison(self):
        with patch.object(grounded_chat,'model',side_effect=[{'intent':'workflow'}, {'domain':'workspace','topic':'product','answer':'장부는 선택사항입니다.'}]) as model:
            r=grounded_chat.answer(self.audit,'장부도 꼭 올려야 해?')
        self.assertEqual(r['answer'],'장부는 선택사항입니다.')
        self.assertIn('product_knowledge',model.call_args.args[1])
    def test_accounting_is_gated_before_comparison_even_with_stale_results(self):
        for stage in ('upload','ocr_mapping','awaiting_review','audit'):
            with self.subTest(stage=stage),patch.object(grounded_chat,'model',return_value={'domain':'accounting','topic':'accounting','answer':'사용되면 안 되는 설명'}) as model,patch.object(grounded_chat.enrichment,'request') as search:
                r=grounded_chat.answer(self.audit,'관련 회계기준 설명해줘',[{'question':'전 거래 회계 설명','answer':'과거 설명'}],platform_context={'stage':stage})
                search.assert_not_called();self.assertEqual(model.call_count,1)
                self.assertEqual(r['citations'],[]);self.assertIn('비교가 끝난 뒤',r['answer'])
                self.assertNotIn('사용되면',r['answer'])
    def test_selected_document_context_limits_ocr_summary(self):
        from workspace_chat import respond
        context={'stage':'awaiting_review','selected_document_id':'pl','documents':[{'id':'ci','document_type':'commercial_invoice','fields':{'total_amount':{'value':'200'}}},{'id':'pl','document_type':'packing_list','fields':{'gross_weight':{'value':'360'}}}]}
        r=respond('이 문서는?',[],context,lambda *args:{'domain':'workspace','topic':'ocr','answer':''})
        self.assertIn('포장명세서',r['answer']);self.assertNotIn('상업송장',r['answer']);self.assertIn('360',r['answer'])
    def test_external_ai_requires_explicit_complete_configuration(self):
        with patch.dict('os.environ',{'FINTRA_CHAT_API_URL':'https://configured.example/api','FINTRA_CHAT_API_KEY':'','FINTRA_CHAT_MODEL':''}):
            with self.assertRaises(ValueError):grounded_chat.model('질문',{}, {})
    def test_support_accepts_null_audit_during_ocr_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'qa';folder.mkdir();(folder/'result.json').write_text('{"audit":null}','utf-8')
            task={'id':'q','owner':'QA','analysis_id':'qa'}
            with patch.object(server.engine,'DATA',Path(tmp)),patch.object(server,'support_history',return_value=[]),patch.object(server,'persist_support'),patch('chat_pipeline.answer',return_value={'answer':'추출값 확인 중'}) as answer:
                server.support_answer(task,'지금 단계?',{'id':'qa','stage':'awaiting_review','status':'awaiting_review'})
            self.assertEqual(task['status'],'complete');self.assertEqual(answer.call_args.args[0],{})
            self.assertEqual(answer.call_args.kwargs['platform_context']['stage'],'awaiting_review')
    def test_missing_status_uses_actual_checks_without_standards(self):
        self.check['status']='cannot_evaluate';self.check['evidence'][0]['normalized_value']=None
        with patch.object(grounded_chat,'model',return_value={'intent':'status'}) as model,patch.object(grounded_chat.enrichment,'request') as search:
            r=grounded_chat.answer(self.audit,'왜 정보 부족이야?')
        self.assertIn('포장명세서 · 총중량',r['answer']);self.assertIn('필수 정보 부족 1개',r['answer']);search.assert_not_called();self.assertEqual(model.call_count,0)
    def test_unknown_check_is_rejected(self):
        with patch.object(grounded_chat,'model',return_value={'check_ids':['invented'],'needs_standards':False}):
            with self.assertRaises(ValueError):grounded_chat.answer(self.audit,'값은?')
    def test_report_preserves_missing_and_source(self):
        self.check['status']='cannot_evaluate';self.check['evidence'][0]['normalized_value']=None
        facts=report_content.facts_for({'audit':self.audit})
        c=facts['transactions'][0]['checks'][0]
        self.assertEqual(c['values'][0]['value'],'정보 없음');self.assertEqual(c['status'],'cannot_evaluate')
        self.assertEqual(c['evidence'][0]['raw_text'],'1,500 KG');self.assertEqual(c['evidence'][0]['tokens'][0]['token_id'],'t1')
    def test_saved_report_notes_survive_generated_appendix(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'a';folder.mkdir()
            (folder/'result.json').write_text(json.dumps({'audit':self.audit}),'utf-8')
            draft={'title':'사용자 제목','sections':[{'heading':'메모','text':'보존할 의견'}],'revision':7}
            (folder/'draft.json').write_text(json.dumps(draft),'utf-8')
            with patch.object(server.engine,'DATA',Path(root)):actual=server.draft_for({'id':'a'})
            self.assertEqual(actual['sections'],draft['sections']);self.assertEqual(actual['revision'],7);self.assertIn('facts',actual)
            self.assertEqual(json.loads((folder/'draft.json').read_text('utf-8')),draft)
    def test_support_history_is_persistent_and_owner_scoped(self):
        with tempfile.TemporaryDirectory() as root,patch.object(server,'DATA',Path(root)):
            server.persist_support({'owner':'A','id':'q','question':'안내','answer':'답변','status':'complete','analysis_id':'tx'})
            self.assertEqual(server.support_history('A')[0]['answer'],'답변');self.assertEqual(server.support_history('B'),[])
    def test_report_rejects_edited_standard_quote(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);(folder/'result.json').write_text(json.dumps({'audit':self.audit}),'utf-8')
            (folder/'conversation.json').write_text(json.dumps([{'status':'complete','grounding_status':'extractive_evidence_selection','citations':[{'id':'s','kind':'standard','quote':'invented','source':{'text':'original','source_type':'회계기준'}}]}]),'utf-8')
            self.assertEqual(report_content.report_facts(folder)['references'],[])

if __name__=='__main__':unittest.main()
