# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys,threading,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import engine

class SchedulingTests(unittest.TestCase):
    def run_job(self,reader):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'test').mkdir()
            job={'id':'test','settings':{},'status':'queued','stage':'inputs','timings':{},'failures':[],
                 'cancel':threading.Event(),'document_records':[{'id':str(i),'stored':str(i)+'.png','name':str(i),'stage':'ocr_mapping'} for i in range(3)]}
            with patch.object(engine,'DATA',root),patch.object(engine,'read_document',side_effect=reader),patch.object(engine,'write_result') as write,patch.dict('os.environ',{'FINTRA_DOCUMENT_WORKERS':'3'}):
                engine.run(job)
            return job,write.call_args.args[1]
    def test_parallel_completion_preserves_uploaded_order(self):
        barrier=threading.Barrier(3)
        def reader(job,record):
            barrier.wait(timeout=2);i=int(record['id']);time.sleep((2-i)*.01)
            return Path(str(i)+'.json'),{'document_type':'commercial_invoice','fields':{'number':i},'items':[]}
        job,result=self.run_job(reader)
        self.assertEqual(job['status'],'awaiting_review')
        self.assertEqual([d['fields']['number'] for d in result['ocr_documents']],[0,1,2])
    def test_one_failed_document_does_not_erase_other_results(self):
        def reader(job,record):
            if record['id']=='1':raise ValueError('unreadable')
            return Path(record['id']+'.json'),{'document_type':'packing_list','fields':{'number':record['id']},'items':[]}
        job,result=self.run_job(reader)
        self.assertEqual(len(job['failures']),1);self.assertEqual(len(result['ocr_documents']),2)
        self.assertEqual(job['document_records'][1]['status'],'failed')
    def test_cancellation_cannot_publish_review_ready(self):
        def reader(job,record):
            job['cancel'].set();raise InterruptedError('cancelled')
        job,_=self.run_job(reader)
        self.assertEqual(job['status'],'cancelled')
