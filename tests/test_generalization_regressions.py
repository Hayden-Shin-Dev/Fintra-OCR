import fintraocr.domain as experiment
from tests.test_structural import doc,run

def test_long_unique_caption_noise_keeps_original_label_and_value():
    for scale in (.6,1,2):
        d=doc([('COMMERCIAL INVOICE',50,20,400),('3. NOTFY PARTY',50,200,230),('Example Trading Ltd.',50,240,300)],scale)
        r=run(d)
        assert r.fields['notify_party'].value=='Example Trading Ltd.'
        assert r.fields['notify_party'].label_evidence[0].selected_text=='3. NOTFY PARTY'

def test_fuzzy_caption_does_not_correct_values_or_accept_short_words_and_sentences():
    for text in ['Buver','Please contact the notfy party after discharge','Invoice 123456']:
        assert experiment.caption_candidate(text) is None
    assert not experiment.one_edit('abc','xyz')

def test_damaged_description_caption_requires_actual_table_context():
    d=doc([('COMMERCIAL INVOICE',50,20,400),('Descrlption of Goods',50,300,260),('Quantity',400,300,180),('Unit Price',650,300,200),('Coupling',50,350,250),('2',400,350,180),('12.50',650,350,200)])
    r=run(d)
    assert r.items[0]['description'].value=='Coupling'

def test_forwarding_agent_reference_heading_does_not_become_buyer_reference():
    d=doc([('BILL OF LADING',50,20,400),('F/Agent Name & Ref',50,200,300),('Transport Partners Ltd.',50,240,300)])
    r=run(d,dtype='bill_of_lading')
    assert r.fields['forwarding_agent'].value=='Transport Partners Ltd.'
    assert r.fields['buyer_reference'].value is None

from tests.test_structural import doc,run
from fintraocr.normalize import normalize
from fintraocr.domain import document_heading_types

def test_qualified_heading_and_colon_have_consistent_grounding():
    for title,dtype in [('Master Packing List','packing_list'),('Container Packing List:','packing_list'),('COMMERCIAL INVOICE from','commercial_invoice'),('Customs Invoice','commercial_invoice')]:
        r=run(doc([(title,50,20,500),('Invoice Number',50,200,250),('X-729',50,240,200)]),dtype=dtype)
        assert r.document_type==dtype

def test_document_references_and_prose_are_not_complete_headings():
    for title in ['Note: one packing list per shipment','Invoice Number','Invoice: X-729','See attached packing list','Bill of Lading Terms and Conditions']:
        assert not document_heading_types(title)

def test_named_month_punctuation_and_invalid_dates():
    for raw in ['MAR.28.2023','March.28.2023','28.Mar.2023','Mar-28-2023','Mar. 28, 2023']:
        assert normalize(raw,'date')[0]=='2023-03-28'
    for raw in ['03.04.2023','MAR.32.2023','MAR.28.23','22-0ct-2007']:
        assert normalize(raw,'date')[0] is None

def test_known_field_caption_is_not_document_type_evidence():
    from fintraocr.grounded import GroundedSelector
    from fintraocr.mapping import MappingEngine
    class WrongTitle(GroundedSelector):
        def label_request(self,document):return {'document_type':'packing_list','title_ids':['0'],'labels':[]}
    result=MappingEngine(WrongTitle('unused')).map(doc([('Consignor/Shipper',50,20,500),('Example Ltd.',50,60,200)]))
    assert result.document_type=='unknown'

from tests.test_structural import doc,run
import pytest

@pytest.mark.parametrize('scale',[.5,1,2.7])
def test_titleless_contract_requires_independent_carriage_evidence(scale):
    lines=[('B/L No.',20,20,160),('R-890',20,50,160),('Shipper',20,100,160),('Consignee',500,100,160),('Port of loading',20,220,160),('Port of discharge',500,220,160),('RECEIVED in apparent good order and condition',20,310,700),('Original Bills of Lading have been signed',20,350,700)]
    d=doc(lines,scale)
    r=run(d,dtype='bill_of_lading')
    assert r.document_type=='bill_of_lading'
    assert len(r.proposal.type_evidence)==7
    assert r.fields['bill_of_lading_number'].value=='R-890'
    # A document reference and routing labels cannot independently prove type.
    assert run(doc(lines[:-2],scale),dtype='bill_of_lading').document_type=='unknown'
    # A model guess of packing list cannot reuse the BL contract evidence.
    assert run(d,dtype='packing_list').document_type=='unknown'

def test_invoice_heading_overrides_carriage_reference():
    d=doc([('COMMERCIAL INVOICE',20,20,500),('B/L No.',20,80,160),('REF-77',20,120,160)])
    assert run(d,dtype='bill_of_lading').document_type=='commercial_invoice'

from tests.test_structural import doc,run
from fintraocr.domain import structural_caption
from fintraocr.models import Selection,Span
from fintraocr.grounded import GroundedSelector
from fintraocr.mapping import MappingEngine

def test_copy_count_caption_is_not_payable_location():
    r=run(doc([('BILL OF LADING',20,20,400),('Freight payable at',20,100,180),("Number of Original B/L’s",240,100,230),('3',240,150,40)]),dtype='bill_of_lading')
    assert r.fields['freight_payable_at'].value is None

def test_publication_air_reference_return_reason_not_trade_reference():
    lines=[('COMMERCIAL INVOICE',20,20,400),('Figure 12: Commercial Invoice',20,100,400),('AIR WAYBILL NO: AX-888',20,170,400),('REASON FOR RETURN: Repair',20,240,400)]
    labels=[{'token_id':str(i),'quote':lines[i][0].split(':')[0],'field':field,'scope':'header'} for i,field in [(1,'invoice_number'),(2,'bill_of_lading_number'),(3,'document_reference')]]
    r=run(doc(lines),labels)
    for field in ['invoice_number','bill_of_lading_number','document_reference']:assert r.fields[field].value is None

def test_contract_attribution_cannot_reenter_through_inline_selection():
    d=doc([('BILL OF LADING',20,20,400),('Carrier named hereon. This Bill of lading is issued by Other Ltd.',20,100,700)])
    selector=GroundedSelector('mock')
    selector.inline_fields={'carrier':[Selection(spans=[Span(token_id='1',start=14,end=20)],label_spans=[Span(token_id='1',start=0,end=7)],score=1,method='semantic_inline')]}
    selector.label_request=lambda d:{'document_type':'bill_of_lading','title_ids':['0'],'labels':[]}
    r=MappingEngine(selector).map(d)
    assert r.fields['carrier'].value is None
    assert selector.metadata['rejected_inline_selections'][0]['reason']=='contract_attribution_is_not_party_identity'

def test_compound_caption_and_reference_are_boundaries_not_arbitrary_values():
    assert structural_caption('Forwarding agent references')
    assert structural_caption('Ocean Vessel / Voyage / Flag')
    assert not structural_caption('Ocean vessel model kit')
    assert not structural_caption('Original bearing kit')
