# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_extraction_release import assess
class ReleaseTests(unittest.TestCase):
    def test_equal_wrong_outputs_do_not_pass_quality_gate(self):
        self.assertFalse(assess({'comparison':[{}],'equal':True},{'total':16,'all_passed':False,'run':{'wall_seconds':20}})['release_ready'])
    def test_missing_evidence_cannot_pass(self):
        self.assertFalse(assess({}, {})['release_ready'])
    def test_all_gates_required(self):
        eq={'comparison':[{}],'equal':True};hold={'total':16,'all_passed':True,'run':{'wall_seconds':20}}
        self.assertTrue(assess(eq,hold)['release_ready'])
        hold['run']['wall_seconds']=80;self.assertFalse(assess(eq,hold)['release_ready'])
