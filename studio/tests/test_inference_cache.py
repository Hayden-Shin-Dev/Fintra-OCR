# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import inference_cache,ocr_cache

class CacheTests(unittest.TestCase):
    def test_model_context_and_schema_are_part_of_identity(self):
        base={'model':'same-model','messages':['question','source passage'],'format':{'type':'object'}}
        token=inference_cache.key(base);inference_cache.put(token,{'answer':['owned']})
        value=inference_cache.get(token);value['answer'].append('changed')
        self.assertEqual(inference_cache.get(token),{'answer':['owned']})
        self.assertIsNone(inference_cache.get(inference_cache.key(dict(base,messages=['question','different source']))))
    def test_expired_model_response_is_not_reused(self):
        inference_cache.put('expired',{'ok':1})
        with patch('inference_cache.time.monotonic',return_value=inference_cache._values['expired'][0]+1801):self.assertIsNone(inference_cache.get('expired'))
    def test_ocr_input_code_model_and_settings_invalidate_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'FintraOCR/fintraocr';root.mkdir(parents=True);code=root/'pipeline.py';code.write_text('version=1')
            response=MagicMock();response.__enter__.return_value.read.return_value=b'{"models":[{"name":"m","digest":"v1"}]}'
            settings=json.dumps({'model':'m','profile':'medium'})
            with patch.dict('os.environ',{'FINTRA_RELEASE_ROOT':tmp}),patch('ocr_cache.urlopen',return_value=response):
                token=ocr_cache.identity(b'image',settings)
                self.assertNotEqual(token,ocr_cache.identity(b'other image',settings))
                self.assertNotEqual(token,ocr_cache.identity(b'image',json.dumps({'model':'m','profile':'other'})))
                code.write_text('version=2');self.assertNotEqual(token,ocr_cache.identity(b'image',settings))
                code.write_text('version=1');response.__enter__.return_value.read.return_value=b'{"models":[{"name":"m","digest":"v2"}]}'
                self.assertNotEqual(token,ocr_cache.identity(b'image',settings))
