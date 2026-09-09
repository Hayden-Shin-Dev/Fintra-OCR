from fintraocr.layout import unambiguous_date_prefix
from tests.test_structural import doc,run
import pytest

@pytest.mark.parametrize('scale',[.6,1,2.2])
def test_date_merged_with_sentence_keeps_exact_date_span(scale):
    d=doc([('PACKING LIST',20,20,400),('Ship Date:',20,150,150),('02/24/2014 Additional shipment information',20,190,700)],scale)
    r=run(d,dtype='packing_list');f=r.fields['shipment_date']
    assert f.value=='2014-02-24'
    assert f.raw_text=='02/24/2014'
    assert f.evidence[0].start==0 and f.evidence[0].end==10

def test_date_range_and_ambiguous_date_are_not_shortened():
    for raw in ['03/04/2024 Note','2024-01-02 to 2024-01-03','2024-01-02 until next week','2024-01-02 and a later date']:
        assert unambiguous_date_prefix(raw) is None

def test_empty_transport_field_does_not_jump_over_omitted_caption():
    d=doc([('BILL OF LADING',20,20,400),('Pre-carriage by',20,100,180),('Ocean Vessel / Voyage / Flag',20,140,350),('Example Vessel/',20,175,260)])
    r=run(d,dtype='bill_of_lading')
    assert r.fields['mode_of_transport'].value is None

def test_freight_category_is_not_payable_place():
    d=doc([('BILL OF LADING',20,20,400),('Freight payable at',20,140,230),('OCEAN FREIGHT',20,180,220)])
    r=run(d,dtype='bill_of_lading');f=r.fields['freight_payable_at']
    assert f.value is None
    assert f.status=='review'
    assert f.raw_text=='OCEAN FREIGHT'


@pytest.mark.parametrize('scale,offset,name',[(.6,0,'Cedar Logistics'),(1,85,'Orion Receiving Ltd.'),(2.2,170,'Delta Import Services')])
def test_side_contact_caption_does_not_cut_off_split_party_label(scale,offset,name):
    # An adjacent contact caption must not become a vertical party-cell boundary.
    lines=[('PACKING LIST',20,20,300),('Notify',20,100,80),('Party',20,125,80),
           ('Fax',180,125,70),(name,20,160,290),('+11 444 777',370,160,200)]
    shifted=[(text,x+offset,y+offset,width) for text,x,y,width in lines]
    r=run(doc(shifted,scale),dtype='packing_list')
    field=r.fields['notify_party']
    assert field.value==name
    assert [e.selected_text for e in field.label_evidence]==['Notify','Party']
    assert all('Fax' not in e.selected_text for e in field.evidence)
