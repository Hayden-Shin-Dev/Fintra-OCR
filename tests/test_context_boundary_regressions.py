from tests.test_structural import doc,run
from fintraocr.layout import LayoutResolver
from fintraocr.schemas import SCHEMAS

def test_importer_reference_does_not_make_consignee_ambiguous():
    lines=[('COMMERCIAL INVOICE',20,20,400),('CONSIGNEE:',20,150,140),('Receiving Ltd.',20,190,200),('IMPORTER (if other than consignee)',20,280,400),('same as consignee',20,320,240)]
    r=run(doc(lines),[{'token_id':'3','quote':lines[3][0],'field':'consignee','scope':'header'}])
    assert r.fields['consignee'].value=='Receiving Ltd.'
    assert r.fields['buyer'].value is None

def test_party_value_beside_caption_is_not_transport_label():
    d=doc([('PACKING LIST',20,20,400),('Carrier:',20,160,120),('Example Ground',170,160,210),('List',170,220,100)])
    r=run(d,[{'token_id':'2','quote':'Example Ground','field':'mode_of_transport','scope':'header'}],dtype='packing_list')
    assert r.fields['mode_of_transport'].value is None

def test_narrative_purchase_order_mention_not_reference():
    d=doc([('PACKING LIST',20,20,400),('Matches the purchase order',20,150,350),('number on the invoice',20,175,350)])
    assert not LayoutResolver(d).fragmented_headers([],SCHEMAS['packing_list'])

def test_complete_company_name_not_party_caption_but_role_prefix_is():
    d=doc([('COMMERCIAL INVOICE',20,20,400),('Example Corporation',20,150,300),('Anycity',20,190,160)])
    r=run(d,[{'token_id':'1','quote':'Example Corporation','field':'buyer','scope':'header'}])
    assert r.fields['buyer'].value is None

def test_issuer_contact_below_from_title_not_seller_label():
    d=doc([('COMMERCIAL INVOICE from',20,20,400),('Contact Person',20,55,220),('Example Corporation',20,90,300)])
    r=run(d,[{'token_id':'1','quote':'Contact Person','field':'seller','scope':'header'}])
    assert r.fields['seller'].value is None
