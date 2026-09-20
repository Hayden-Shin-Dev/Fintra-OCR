# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from comparison_scope import scope_for,coverage
from presentation import transaction_state
from review_insights import quick_risk,insight

class ScopeTests(unittest.TestCase):
    def tx(self,kind,field='quantity',values=(None,None)):
        c={'check_id':'missing','type':kind,'status':'cannot_evaluate','reason':'required_value_missing','evidence':[{'field_name':field,'normalized_value':v,'original':{'status':'missing'},'source':{'entity_id':str(i)}} for i,v in enumerate(values)]}
        return {'checks':[{'check_id':'link','type':'reference_invoice_number','status':'pass'},c],'documents':{'commercial_invoice':{'id':'0'},'packing_list':{'id':'1'}}}
    def test_missing_quantity_remains_blocking(self):
        self.assertEqual(transaction_state(self.tx('item_quantity_comparison')),'cannot_evaluate')
    def test_optional_reference_not_counted_as_pass(self):
        t=self.tx('reference_buyer_reference');before=copy.deepcopy(t)
        self.assertEqual(transaction_state(t),'pass');self.assertEqual(coverage(t)['supplementary_ids'],['missing']);self.assertEqual(t,before)
    def test_mapping_uncertainty_remains_blocking(self):
        t=self.tx('reference_buyer_reference');t['checks'][1]['evidence'][0]['original']['status']='review'
        self.assertEqual(transaction_state(t),'cannot_evaluate')
    def test_observed_weight_without_unit_remains_blocking(self):
        t=self.tx('item_gross_weight_comparison','gross_weight',('12','12'))
        self.assertEqual(transaction_state(t),'cannot_evaluate')
    def test_mismatch_never_hidden(self):
        t=self.tx('reference_buyer_reference');t['checks'][1]['status']='flag'
        self.assertEqual(transaction_state(t),'review')
    def test_unknown_check_is_required_by_default(self):
        self.assertEqual(transaction_state(self.tx('new_critical_check')),'cannot_evaluate')
    def test_real_normal_result_does_not_waive_essential_checks(self):
        p=Path(__file__).resolve().parents[1]/'data/analyses/4bc3d14e1d8746e7a92491c9a225aafd/result.json'
        if not p.exists():self.skipTest('local regression artifact not available')
        t=json.loads(p.read_text('utf-8'))['audit']['transactions'][0]
        self.assertEqual(len(coverage(t)['supplementary_ids']),31)
        self.assertEqual(transaction_state(t),'pass')
    def test_fast_risk_only_handles_unambiguous_requests(self):
        c={'check_id':'x','type':'item_quantity_comparison','title':'수량','status':'flag','evidence':[{'field_name':'quantity','normalized_value':'7','source':{}}]}
        for q in ['지금 리스크 알려줘','불일치 리스크가 뭐야','이 거래의 위험을 설명해줘']:
            self.assertIsNotNone(quick_risk(q,[c],None,None),q)
        self.assertIsNone(quick_risk('환율이 바뀌면 위험이 어떻게 달라져?',[c],None,None))
        self.assertIn('검수',insight(c)['action'])
