from fintra_ocr.common_schema import build_common_document_from_form_type
from fintra_ocr.field_extraction import extract_fields
from fintra_ocr.label_bbox import OCRBoundingBox
from fintra_ocr.normalization import normalize_fields
from fintra_ocr.oracle_validation import inject_ground_truth_values, build_oracle_document, compare_actual_to_oracle
from fintra_ocr.prediction_parser import OCRPrediction


def p(text, l,t,r,b,score=.8): return OCRPrediction(text,(l,r,r,l),(t,t,b,b),score)
def g(text, l,t,r,b): return OCRBoundingBox('g',text,(l,r,r,l),(t,t,b,b))


def test_inject_gt_replaces_value_region_but_keeps_static_label():
    predictions=[p('TOTAL',10,10,60,30),p('S000',10,40,80,60)]
    gt=[g('$5000',10,40,80,60)]
    injected=inject_ground_truth_values(predictions,gt)
    assert [x.text for x in injected] == ['TOTAL','$5000']


def test_oracle_classifies_ocr_value_degradation():
    predictions=[p('TOTAL',10,10,60,30),p('S000',10,40,80,60)]
    actual_fields=normalize_fields(extract_fields('상업송장',predictions))
    actual=build_common_document_from_form_type('상업송장','d',actual_fields)
    oracle=build_oracle_document('상업송장','d',predictions,[g('$5000',10,40,80,60)])
    diagnostics=compare_actual_to_oracle(actual,oracle)
    assert diagnostics['amount'].oracle_status == 'found'
    assert diagnostics['amount'].classification in {'ocr_value_degradation','ocr_or_extractor_value_mismatch'}


def test_semantic_oracle_does_not_reward_caption_as_shipper():
    actual = {
        'fields': {
            'shipper': {
                'status': 'found',
                'value': 'DESCRIPTION OF PACKAGES AND GOODS',
                'normalized': 'DESCRIPTION OF PACKAGES AND GOODS',
            }
        }
    }
    oracle = {
        'fields': {
            'shipper': {
                'status': 'found',
                'value': 'DESCRIPTION OF PACKAGES AND GOODS',
                'normalized': 'DESCRIPTION OF PACKAGES AND GOODS',
            }
        }
    }
    diagnostics = compare_actual_to_oracle(actual, oracle)
    assert diagnostics['shipper'].classification == 'oracle_semantically_invalid'
    assert diagnostics['shipper'].classification != 'e2e_matches_oracle'


def test_both_missing_is_not_counted_as_extractor_failure():
    actual = {
        'fields': {
            'date': {'status': 'missing', 'value': None, 'normalized': None}
        }
    }
    oracle = {
        'fields': {
            'date': {'status': 'missing', 'value': None, 'normalized': None}
        }
    }
    diagnostics = compare_actual_to_oracle(actual, oracle)
    assert diagnostics['date'].classification == 'both_missing_or_oracle_unavailable'
