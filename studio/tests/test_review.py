# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ.setdefault('FINTRA_WEB_DATA',str(ROOT/'data'/'analyses'))
import server

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.folder=self.root/'test';self.folder.mkdir()
        self.job={'id':'test','status':'awaiting_review','document_records':[{'id':'d','result_file':'d.json'}]}
        cell={'value':'360','status':'accepted','raw_text':'360 KG','evidence':[{'token_id':'t1','start':0,'end':3,'bbox':[[0,0],[20,0],[20,10],[0,10]]}]}
        self.original={'document_type':'packing_list','fields':{'gross_weight':cell,'issue_date':dict(value='2026-09-01',status='accepted')},'items':[]}
        (self.folder/'d.json').write_text(json.dumps(self.original),'utf-8')
        (self.folder/'result.json').write_text('{}','utf-8')
        self.a=patch.object(server.engine,'DATA',self.root);self.a.start()
        self.b=patch.object(server.engine,'write_result',lambda job,r:server.write(self.folder/'result.json',r));self.b.start()
    def tearDown(self):
        self.b.stop();self.a.stop();self.tmp.cleanup()
    def change(self,value,field='gross_weight'):
        return {'document_id':'d','group':'fields','field':field,'value':value}
    def test_correction_keeps_original_evidence(self):
        server.corrections(self.job,[self.change('1,250.50')],'reviewer')
        result=json.loads((self.folder/'d.json').read_text())
        self.assertEqual(result['fields']['gross_weight']['value'],'1250.50')
        self.assertEqual(result['fields']['gross_weight']['evidence'],self.original['fields']['gross_weight']['evidence'])
        self.assertEqual(result['fields']['gross_weight']['raw_text'],'360 KG')
        self.assertEqual(json.loads((self.folder/'d.json.original.json').read_text()),self.original)
    def test_invalid_batch_does_not_write_partial_changes(self):
        before=(self.folder/'d.json').read_bytes()
        for invalid in [self.change('360x'),self.change('2026-99-99','issue_date'),dict(self.change('4'),group='-1')]:
            with self.assertRaises(ValueError):server.corrections(self.job,[self.change('400'),invalid],'reviewer')
            self.assertEqual((self.folder/'d.json').read_bytes(),before)
    def test_completed_analysis_cannot_be_silently_changed(self):
        self.job['status']='complete'
        with self.assertRaises(ValueError):server.corrections(self.job,[self.change('400')],'reviewer')
    def test_clear_is_not_accepted_value(self):
        server.corrections(self.job,[self.change('')],'reviewer')
        cell=json.loads((self.folder/'d.json').read_text())['fields']['gross_weight']
        self.assertIsNone(cell['value']);self.assertEqual(cell['status'],'missing')

if __name__=='__main__':unittest.main()
