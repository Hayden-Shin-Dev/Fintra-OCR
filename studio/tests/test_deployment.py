# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import deployment
class DeploymentTests(unittest.TestCase):
    def test_public_origin_is_exact_and_required(self):
        with patch.dict('os.environ',{'FINTRA_PUBLIC_ORIGIN':'https://fintra.example'}):
            self.assertTrue(deployment.valid_origin('https://fintra.example',8781))
            for origin in [None,'null','http://fintra.example','https://fintra.example.attacker.test']:
                self.assertFalse(deployment.valid_origin(origin,8781))
            self.assertIn('fintra.example',deployment.allowed_hosts(8781))
    def test_public_configuration_rejects_paths_and_credentials(self):
        for origin in ['http://example.com','https://user@example.com','https://example.com/path']:
            with patch.dict('os.environ',{'FINTRA_PUBLIC_ORIGIN':origin}),self.assertRaises(ValueError):deployment.public_origin()
    def test_local_mode_unchanged(self):
        with patch.dict('os.environ',{'FINTRA_PUBLIC_ORIGIN':''}):
            self.assertTrue(deployment.valid_origin(None,8780))
            self.assertTrue(deployment.valid_origin('http://localhost:8780',8780))
