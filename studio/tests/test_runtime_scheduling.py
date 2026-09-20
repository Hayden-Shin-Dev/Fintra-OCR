# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Exercise scheduler functions without starting Paddle/GPU inference."""
import ast,os,threading,unittest
from pathlib import Path
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor

class RuntimeSchedulingTests(unittest.TestCase):
    def namespace(self):
        source=Path(os.environ['LOCALAPPDATA'])/'Fintra/versions/0.6.1-preview/FintraOCR/fintraocr/web.py'
        tree=ast.parse(source.read_text('utf-8'))
        tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('finish_mapping','run_job')]
        pool=ThreadPoolExecutor(max_workers=1);self.addCleanup(pool.shutdown)
        ns={'os':os,'time':__import__('time'),'MAPPING_POOL':pool,'run_stage':Mock(),'run_warm_ocr':Mock(),'stop_warm_ocr':Mock()}
        def update(job,**values):job.update(values)
        ns['update']=update;exec(compile(tree,'scheduler','exec'),ns)
        return ns
    def job(self):return {'cancel':threading.Event(),'settings':{'model':'qwen3.5:4b','mode':'full','mapping_strategy':'semantic'}}
    def test_mapping_failure_is_visible_and_next_job_can_run(self):
        ns=self.namespace();ns['run_stage'].side_effect=[RuntimeError('model unavailable'),None]
        a,b=self.job(),self.job();ns['run_job'](a);ns['run_job'](b)
        ns['MAPPING_POOL'].submit(lambda:None).result()
        self.assertEqual(a['status'],'failed');self.assertEqual(b['status'],'complete')
    def test_cancelled_mapping_never_calls_model(self):
        ns=self.namespace();job=self.job();job['cancel'].set();ns['finish_mapping'](job)
        self.assertEqual(job['status'],'cancelled');ns['run_stage'].assert_not_called()
    def test_next_ocr_can_run_while_mapping_waits(self):
        ns=self.namespace();entered=threading.Event();release=threading.Event();self.addCleanup(release.set)
        def mapping(*args):entered.set();release.wait(2)
        ns['run_stage'].side_effect=mapping
        ns['run_job'](self.job());self.assertTrue(entered.wait(1))
        ns['run_job'](self.job());self.assertEqual(ns['run_warm_ocr'].call_count,2)
        release.set();ns['MAPPING_POOL'].submit(lambda:None).result()
