# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from atomic_storage import write_json

class AtomicStorageTests(unittest.TestCase):
    def test_transient_windows_lock_preserves_then_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'status.json';target.write_text('{"old":true}')
            original=Path.replace;attempts=[]
            def replace(source,destination):
                attempts.append(source)
                if len(attempts)<3:
                    self.assertEqual(json.loads(target.read_text()),{'old':True})
                    raise PermissionError('sharing violation')
                return original(source,destination)
            with patch.object(Path,'replace',replace),patch('atomic_storage.time.sleep'):
                write_json(target,{'status':'완료'})
            self.assertEqual(json.loads(target.read_text('utf-8')),{'status':'완료'})
            self.assertEqual(len(attempts),3)
            self.assertEqual(list(Path(folder).glob('*.tmp')),[])
    def test_persistent_lock_raises_without_destroying_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'status.json';target.write_text('{"old":true}')
            with patch.object(Path,'replace',side_effect=PermissionError()),patch('atomic_storage.time.sleep'),self.assertRaises(PermissionError):
                write_json(target,{'new':True})
            self.assertEqual(json.loads(target.read_text()),{'old':True})
            self.assertEqual(list(Path(folder).glob('*.tmp')),[])
