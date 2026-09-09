from scripts.score_acceptance import audit_result_contract, bucket, count, rates


def test_null_is_not_a_positive_and_missing_contract_is_reported():
    gold={'fields':{'issue_date':None},'items':[]}
    b=bucket();count(b,None,None,True)
    assert rates(b)['precision'] is None
    assert b['tp']==0
    assert audit_result_contract({'fields':{},'items':[]},gold)==[
        {'field':'fields.issue_date','reason':'missing_applicable_field_or_status'}]


def test_ambiguous_source_cannot_pass_as_absent_or_accepted():
    gold={'fields':{'issue_date':None},'items':[],
          'expected_review':['fields.issue_date']}
    for status,value in [('missing',None),('accepted','2025-03-04'),('review','2025-03-04')]:
        r={'fields':{'issue_date':{'value':value,'status':status}},'items':[]}
        assert audit_result_contract(r,gold)[0]['reason']=='ambiguous_source_requires_null_and_review'
    assert audit_result_contract({'fields':{'issue_date':{'value':None,'status':'review'}},'items':[]},gold)==[]
