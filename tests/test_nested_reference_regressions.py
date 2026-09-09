from tests.test_structural import doc,run

def test_nested_reference_caption_is_preserved_for_review_not_whole_value():
    d=doc([('COMMERCIAL INVOICE',20,20,400),('Export references',20,150,250),("Shipper's Ref No: Z-882",20,185,320)])
    r=run(d)
    f=r.fields['document_reference']
    assert f.value is None
    assert f.raw_text=="Shipper's Ref No: Z-882"
    assert f.status=='review'
    assert 'nested_reference_caption_is_not_reference_value' in f.issues

def test_agent_for_unreadable_principal_not_forwarding_agent():
    d=doc([('BILL OF LADING',20,20,400),('AGENT FOR THE XXXXXX',20,150,300),('TOTAL PREPAID',380,150,250)])
    r=run(d,[{'token_id':'1','quote':'AGENT FOR THE XXXXXX','field':'forwarding_agent','scope':'header'}],dtype='bill_of_lading')
    assert r.fields['forwarding_agent'].value is None
