# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from report_renderer import create_report

class ReportLedgerTests(unittest.TestCase):
    def test_optional_ledger_does_not_break_pdf(self):
        for ledger in (None, {}, {'fields': {'transaction_id': {'value': 'sample-transaction'}}}):
            with self.subTest(ledger=ledger), tempfile.TemporaryDirectory() as folder:
                payload={'audit': {'transactions': [{'transaction_id':'sample', 'ledger':ledger, 'documents':{}, 'checks':[], 'audit_points':[]}]}}
                original=copy.deepcopy(payload)
                path=Path(folder)/'report.pdf'
                result=create_report(payload,path,'test')
                self.assertEqual(result['status'],'complete')
                self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
                self.assertEqual(payload,original)

if __name__=='__main__': unittest.main()
