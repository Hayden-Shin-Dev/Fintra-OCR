# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from kasb_kb import Store,exact_reference,exact_lookup,split_paragraphs
from kasb_sync import catalogue,sync_documents,qna_catalogue,parse_qna
from chat_retrieval import standard_lookup
from chat_router import route

class KASBTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'kb.sqlite')
        self.doc={'id':'kasb:standard:1002','source_type':'kifrs_standard','standard_number':'1002','standard_name':'TEST ONLY',
            'version':'v1','source_url':'https://www.kasb.or.kr/','authority':'KASB','download_url':'https://www.kasb.or.kr/',
            'download_parameters':{},'format':'pdf'}
        self.grants={'kifrs_standard':{'reference':'synthetic-test-only','automated_download':True,'indexing':True,'service_use':True}}
    def test_real_catalogue_contract(self):
        rows=catalogue((ROOT/'tests/kasb/listing.html').read_text('utf-8'),(ROOT/'tests/kasb/download.js').read_text('utf-8'))
        self.assertEqual(len(rows),60)
        for number in ('1002','1115','1021'):
            row=next(r for r in rows if r['standard_number']==number)
            self.assertEqual(row['format'],'pdf');self.assertEqual(row['download_method'],'POST')
            self.assertEqual(row['download_url'],'https://www.kasb.or.kr/commonFile/fileDownload.do')
    def test_reference_forms(self):
        for q,ref in [('1002호 문단 9가 뭐야?',('1002','9')),('1115호 31',('1115','31')),('1021 문단 21',('1021','21'))]:
            self.assertEqual(exact_reference(q),ref);self.assertEqual(route(q).route,'accounting_standard')
        self.assertIsNone(exact_reference('금액 1002000'))
    def test_exact_never_semantic(self):
        with patch.dict(os.environ,FINTRA_KASB_DB=str(self.store.path)):
            result=standard_lookup('1002호 문단 9',request=lambda *a:self.fail('semantic retrieval called'))
        self.assertTrue(result['retrieval_failure']);self.assertEqual(result['passages'],[])
    def test_preserves_paragraph_on_subchunks(self):
        rows=split_paragraphs('측정\n9  '+('synthetic content '*100)+'\n34  another synthetic paragraph',max_chars=100)
        self.assertGreater(len(rows),2);self.assertEqual(rows[0]['paragraph'],'9');self.assertEqual(rows[1]['paragraph'],'9')
        self.assertEqual(rows[-1]['paragraph'],'34');self.assertEqual(rows[0]['section'],'측정')
    def test_ambiguous_number_fails(self):
        with self.assertRaises(ValueError):split_paragraphs('9  first\n9  repeated TOC or body')
    def test_source_isolation(self):
        p=[{'paragraph':'9','chunk_index':0,'content':'synthetic text','section':'test'}]
        self.store.replace(dict(self.doc,id='qna',source_type='kasb_qna'),p,'hash')
        self.assertEqual(self.store.exact('1002','9'),[])
        self.store.replace(self.doc,p,'hash')
        self.assertEqual(self.store.exact('1002','9')[0]['content'],'synthetic text')
    def test_failed_replace_atomic(self):
        p={'paragraph':'9','content':'old','chunk_index':0};self.store.replace(self.doc,[p],'old')
        with self.assertRaises(Exception):self.store.replace(self.doc,[p,p],'new')
        self.assertEqual(self.store.document(self.doc['id'])['content_hash'],'old')
        self.assertEqual(self.store.exact('1002','9')[0]['content'],'old')
    def test_unchanged_skips_parse(self):
        raw=b'synthetic';h=hashlib.sha256(raw).hexdigest()
        self.store.replace(self.doc,[{'paragraph':'9','content':'old'}],h)
        out=sync_documents([self.doc],self.store,self.grants,lambda _:self.fail('reparsed unchanged'),lambda *a:raw)
        self.assertEqual(out['skipped'],[self.doc['id']])
    def test_missing_license_no_download(self):
        result=sync_documents([self.doc],self.store,{},lambda _:None,lambda *a:self.fail('downloaded without rights'))
        self.assertIn('source_license_not_confirmed',result['failed'][0]['reason'])
    def test_parse_failure_preserves_old(self):
        self.store.replace(self.doc,[{'paragraph':'9','content':'old'}],'old')
        result=sync_documents([self.doc],self.store,self.grants,lambda _: 'unparseable',lambda *a:b'changed')
        self.assertEqual(len(result['failed']),1);self.assertEqual(self.store.exact('1002','9')[0]['content'],'old')
    def test_qna_actual_source_type_and_warning(self):
        rows=qna_catalogue((ROOT/'tests/kasb/qna-list.html').read_text('utf-8'))
        self.assertEqual(len(rows),10);self.assertEqual(rows[0]['source_type'],'kasb_qna')
        self.assertIn('공식 의견과 일치하지',rows[0]['notice'])
        paragraphs=parse_qna((ROOT/'tests/kasb/qna-verification.html').read_text('utf-8'),rows[0])
        self.assertEqual(paragraphs[0]['paragraph'],'qna')
        self.assertIn('취득원가와 순실현가능가치 중 낮은 금액',paragraphs[0]['content'])
    def test_hybrid_metadata_vector_keyword_and_rerank(self):
        from kasb_search import search
        rows=[{'paragraph':'9','content':'재고자산 측정 테스트','chunk_index':0,'vector':[1.,0.]},
              {'paragraph':'34','content':'재고자산 손실 테스트','chunk_index':0,'vector':[.9,.1]}]
        self.store.replace(self.doc,rows,'h')
        result=search('재고자산 측정',{'standard_id':'1002'},self.store,embed=lambda q:[1.,0.])
        self.assertTrue(result['passages']);self.assertLessEqual(len(result['passages']),5)
        self.assertEqual(result['method'],'official_hybrid')
        self.assertFalse(search('재고자산',{'standard_id':'1115'},self.store,embed=lambda q:self.fail('filtered before vector'))['passages'])

if __name__=='__main__':unittest.main()
