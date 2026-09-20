# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import gzip
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from http_payload import encode_payload, content_etag

class PayloadTests(unittest.TestCase):
    def test_text_roundtrip(self):
        for mime in ('application/json','text/javascript','text/css'):
            raw=('한글 document result ' * 1000).encode()
            body, encoding=encode_payload(raw,mime,'br, gzip')
            self.assertEqual(encoding,'gzip')
            self.assertEqual(gzip.decompress(body),raw)
            self.assertLess(len(body),len(raw))
    def test_identity_clients(self):
        raw=b'a'*5000
        for accept in ('','identity','gzip;q=0','*;q=1,gzip;q=0'):
            self.assertEqual(encode_payload(raw,'text/javascript',accept),(raw,None))
    def test_binary_unchanged(self):
        for mime in ('image/png','application/pdf'):
            raw=b'a'*5000
            self.assertEqual(encode_payload(raw,mime,'gzip'),(raw,None))
    def test_small_payload_unchanged(self):
        self.assertEqual(encode_payload(b'{}','application/json','gzip'),(b'{}',None))
    def test_changed_asset_invalidates(self):
        self.assertEqual(content_etag(b'old'),content_etag(b'old'))
        self.assertNotEqual(content_etag(b'old'),content_etag(b'new'))
if __name__=='__main__':unittest.main()
