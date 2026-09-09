import pytest
from fintraocr.models import OCRDocument,Page,Token,Selection,Span,Proposal
from fintraocr.grounded import GroundedSelector
from fintraocr.mapping import MappingEngine
from fintraocr.schemas import SCHEMAS,ALIASES

def doc(lines,scale=1):
    return OCRDocument(pages=[Page(page=1,width=round(1000*scale),height=round(1400*scale),source='test')],tokens=[Token(id=str(i),page=1,text=text,bbox=[(x*scale,y*scale),((x+w)*scale,y*scale),((x+w)*scale,(y+20)*scale),(x*scale,(y+20)*scale)],confidence=.99) for i,(text,x,y,w) in enumerate(lines)])

def run(d,labels=(),dtype='commercial_invoice'):
    selector=GroundedSelector('mock')
    selector.label_request=lambda d:{'document_type':dtype,'title_ids':['0'],'labels':list(labels)}
    return MappingEngine(selector).map(d)

@pytest.mark.parametrize('scale',[.5,1,2.3])
def test_inline_identifier_date_and_distinct_party_roles(scale):
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Invoice number: Z-019',30,100,250),('Issued on: 2024-11-02',30,150,250),('Buyer: Orbit Ltd.',30,200,250),('Consignee: Arc Ltd.',30,250,250)],scale)
    r=run(d)
    assert r.fields['invoice_number'].value=='Z-019'
    assert r.fields['issue_date'].value==r.fields['invoice_date'].value=='2024-11-02'
    assert r.fields['buyer'].value=='Orbit Ltd.'
    assert r.fields['consignee'].value=='Arc Ltd.'
    assert set(r.fields)==set(SCHEMAS['commercial_invoice'])
    assert r.fields['purchase_order_number'].value is None
    assert r.fields['purchase_order_number'].null_reason=='label_not_proposed'

def test_two_columns_do_not_merge_companies():
    r=run(doc([('COMMERCIAL INVOICE',30,20,300),('Buyer',30,100,100),('Consignee',500,100,100),('Alpha Ltd.',30,140,160),('Beta Ltd.',500,140,160)]))
    assert r.fields['buyer'].value=='Alpha Ltd.'
    assert r.fields['consignee'].value=='Beta Ltd.'

def test_table_numbers_and_units_share_token_disjoint_spans():
    r=run(doc([('PACKING LIST',30,20,300),('Goods',30,100,100),('Packages',400,100,110),('Gross weight',650,100,140),('Motor',30,160,100),('4 PKG',400,160,90),('52.40 KG',650,160,120),('Valve',30,220,100),('9 PKG',400,220,90),('10.20 KG',650,220,120)]),dtype='packing_list')
    assert len(r.items)==2
    assert [i['package_count'].value for i in r.items]==['4','9']
    assert r.items[0]['gross_weight'].value=='52.40'
    assert r.items[0]['weight_unit'].value=='kg'
    assert r.items[0]['quantity'].value is None

def test_repeated_role_is_ambiguous_not_guessed_from_position():
    r=run(doc([('BILL OF LADING',30,20,300),('Consignee',30,100,120),('One Ltd.',30,140,160),('Consignee',30,230,120),('Two Ltd.',30,270,160)]),dtype='bill_of_lading')
    assert r.fields['consignee'].value is None
    assert r.fields['consignee'].status=='review'
    assert r.fields['shipper'].value is None

def test_explicit_party_reference_keeps_both_source_and_reference():
    r=run(doc([('PACKING LIST',30,20,300),('Consignee',30,100,120),('Receiving Ltd.',30,140,160),('Notify party',30,230,120),('Same as above.',30,270,160)]),dtype='packing_list')
    assert r.fields['notify_party'].value=='Receiving Ltd.'
    assert r.fields['notify_party'].reference_evidence[0].selected_text=='Same as above.'
    assert r.fields['notify_party'].reference_field=='consignee'

def test_label_cannot_be_its_own_value():
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Buyer',30,100,100)])
    selection=Selection(spans=[Span(token_id='1',start=0,end=5)],label_spans=[Span(token_id='1',start=0,end=5)],score=1,method='layout')
    p=Proposal(document_type='commercial_invoice',type_score=1,type_evidence=[Span(token_id='0',start=0,end=18)],fields={'buyer':selection})
    r=MappingEngine().map(d,proposal=p)
    assert r.fields['buyer'].value is None
    assert 'label_used_as_value' in r.fields['buyer'].issues

def test_cross_document_reference_is_not_discarded():
    r=run(doc([('COMMERCIAL INVOICE',30,20,300),('Bill of lading number: REF-208',30,100,320)]))
    assert r.fields['bill_of_lading_number'].value=='REF-208'
    assert r.fields['invoice_number'].value is None

def test_exporter_is_not_assumed_to_be_seller():
    r=run(doc([('COMMERCIAL INVOICE',30,20,300),('Exporter: Trading Agent Ltd.',30,100,320)]))
    assert r.fields['exporter'].value=='Trading Agent Ltd.'
    assert r.fields['seller'].value is None

def test_narrative_field_words_do_not_become_labels():
    r=run(doc([('COMMERCIAL INVOICE',30,20,300),('Buyer should retain this copy for their records.',30,100,600),('Unrelated Ltd.',30,140,180)]))
    assert r.fields['buyer'].value is None

def test_split_weight_headers_and_total_stay_in_their_columns():
    d=doc([('PACKING LIST',30,20,300),('Goods',30,100,100),('Quantity or net',400,100,160),('weight',450,125,70),('Gross',650,100,100),('Weight',650,125,100),('Rotor',30,180,100),('255KG',440,180,90),('884KG',650,180,90),('TOTAL',30,250,100),('121KG',440,250,90),('210KG',650,250,90)])
    r=run(d,dtype='packing_list')
    assert len(r.items)==1
    assert r.items[0]['net_weight'].value=='255'
    assert r.items[0]['gross_weight'].value=='884'
    assert r.fields['net_weight'].value=='121'
    assert r.fields['gross_weight'].value=='210'

def test_mixed_weight_units_are_separate_not_silently_shared():
    d=doc([('PACKING LIST',30,20,300),('Goods',30,100,100),('Net weight',400,100,160),('Gross weight',650,100,160),('Rotor',30,160,100),('10 kg',400,160,90),('25 lb',650,160,90)])
    r=run(d,dtype='packing_list')
    assert r.items[0]['net_weight_unit'].value=='kg'
    assert r.items[0]['gross_weight_unit'].value=='lb'
    assert r.items[0]['weight_unit'].value is None
    assert r.items[0]['weight_unit'].status=='review'

def test_scalar_cell_cannot_join_distinct_numbers_into_grouped_number():
    from fintraocr.layout import LayoutResolver
    from fintraocr.schemas import FieldSpec
    d=doc([('PACKING LIST',30,20,300),('884',30,100,70),('255',250,100,70)])
    selection=LayoutResolver(d).select(d.tokens[1:],FieldSpec('number','weight'),'gross_weight',[Span(token_id='0',start=0,end=12)])
    p=Proposal(document_type='packing_list',type_score=1,type_evidence=[Span(token_id='0',start=0,end=12)],fields={'gross_weight':selection})
    r=MappingEngine().map(d,proposal=p)
    assert r.fields['gross_weight'].value is None
    assert 'multiple_values_in_scalar_cell' in r.fields['gross_weight'].issues

@pytest.mark.parametrize('raw,expected', [('PC','pcs'),('Cft','ft3'),('drum','drum'),('spool','spool'),('123',None)])
def test_explicit_unit_column_preserves_unknown_text_but_not_number(raw,expected):
    from fintraocr.fast import StructuralSelector
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Description',30,100,150),('Quantity',400,100,100),('Unit Type',650,100,120),('Cable',30,160,100),('7',400,160,30),(raw,650,160,80)])
    s=StructuralSelector()
    result=MappingEngine(s).map(d)
    assert result.items[0]['unit'].value==expected
    assert s.metadata['calls']==[]
    if expected:
        assert result.items[0]['unit'].raw_text==raw
        assert result.items[0]['unit'].evidence[0].selected_text==raw
        assert result.items[0]['unit'].label_evidence


def test_fast_path_does_not_force_country_normalization():
    from fintraocr.fast import StructuralSelector
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Country of Final Destination',30,100,280),('Scotland',30,140,100)])
    r=MappingEngine(StructuralSelector()).map(d)
    v=r.fields['country_of_destination']
    assert v.value is None and v.status=='review' and v.raw_text=='Scotland'


def test_split_table_total_does_not_take_first_row_as_document_total():
    from fintraocr.fast import StructuralSelector
    d=doc([('COMMERCIAL INVOICE',30,20,300),('CODE',30,100,80),('PRODUCT DESCRIPTION',170,100,200),('QTY',420,100,60),('UNIT',600,90,60),('VALUE',600,112,60),('SUB',780,90,60),('TOTAL',780,112,70),('ABC',30,150,80),('Cable',170,150,100),('1',420,150,30),('7.00',600,150,60),('7.00',780,150,60)])
    r=MappingEngine(StructuralSelector()).map(d)
    assert r.fields['total_amount'].value is None
    assert r.items[0]['amount'].value=='7.00'
    assert r.items[0]['unit_price'].value=='7.00'


def test_unmapped_columns_do_not_contaminate_description_or_quantity():
    from fintraocr.fast import StructuralSelector
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Product Description',30,100,180),('Size',300,100,50),('Qty',450,100,50),('Material',600,100,100),('Unit Price',800,100,100),('Coil',30,160,90),('XL',300,160,40),('3',450,160,30),('Copper',600,160,90),('9.00',800,160,60)])
    r=MappingEngine(StructuralSelector()).map(d)
    assert r.items[0]['description'].value=='Coil'
    assert r.items[0]['quantity'].value=='3'
    assert r.items[0]['unit_price'].value=='9.00'


@pytest.mark.parametrize('raw,expected',[('27-9-2025','2025-09-27'),('9/27/2025','2025-09-27'),('9/10/2025',None),('31/2/2025',None)])
def test_numeric_date_requires_unique_valid_interpretation(raw,expected):
    from fintraocr.normalize import normalize
    assert normalize(raw,'date')[0]==expected


def test_large_model_input_compaction_keeps_every_token(monkeypatch):
    import io,json
    import fintraocr.grounded as grounded
    d=doc([('COMMERCIAL INVOICE',30,20,300)]+[(f'Cell {i}',30,100+i*25,100) for i in range(60)])
    original=grounded.payload(d)
    selector=GroundedSelector('mock');selector.max_chars=len(json.dumps(original).encode())-100
    sent=[]
    def request(req,**kwargs):
        sent.append(json.loads(req.data))
        return io.BytesIO(json.dumps({'message':{'content':json.dumps({'document_type':'commercial_invoice','title_ids':['0'],'labels':[]})}}).encode())
    monkeypatch.setattr(grounded,'urlopen',request)
    selector.label_request(d)
    content=json.loads(sent[0]['messages'][1]['content'])
    assert content['token_columns']==['id','page','text','confidence','bbox']
    assert [(r[0],r[2]) for r in content['tokens']]==[(t.id,t.text) for t in d.tokens]


def test_combined_party_roles_and_invoice_number_date():
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Shipper / Exporter',30,100,210),('Origin Company',30,140,190),('No. & Date of invoice',500,100,250),('19281-7722-8833',500,140,210),('2025-04-12',500,180,150)])
    r=run(d)
    assert r.fields['invoice_number'].value=='19281-7722-8833'
    assert r.fields['issue_date'].value=='2025-04-12'
    assert r.fields['shipper'].value==r.fields['exporter'].value=='Origin Company'
    assert r.fields['seller'].value is None


def test_shared_quantity_unit_column_and_unit_on_next_line():
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Description',30,100,150),('Quantity/Unit',400,100,140),('Unit Price',650,100,130),('Cable',30,160,110),('9',400,160,30),('12.00',650,160,80),('M/T',400,190,60)])
    r=run(d)
    assert r.items[0]['quantity'].value=='9'
    assert r.items[0]['unit'].value=='t'


def test_inline_total_without_separator():
    r=run(doc([('COMMERCIAL INVOICE',30,20,300),('Total$1,245.20',30,140,220)]))
    assert r.fields['total_amount'].value=='1245.20'


def test_model_title_label_cannot_steal_invoice_reference():
    d=doc([('PACKING LIST',30,20,300),('Invoice No. & date of Invoice',30,100,300),('A-4521',30,140,140),('2025-03-25',30,180,150)])
    r=run(d,[{'token_id':'0','quote':'PACKING LIST','field':'packing_list_number','scope':'header'}],dtype='packing_list')
    assert r.fields['invoice_number'].value=='A-4521'
    assert r.fields['packing_list_number'].value is None


def test_wrong_model_seller_cannot_override_explicit_dual_role():
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Shipper / Exporter',30,100,210),('Supplier Company',30,140,190)])
    r=run(d,[{'token_id':'1','quote':'Shipper / Exporter','field':'seller','scope':'header'}])
    assert r.fields['seller'].value is None
    assert r.fields['shipper'].value==r.fields['exporter'].value=='Supplier Company'


def test_centered_value_is_not_a_new_label():
    d=doc([('BILL OF LADING',30,20,300),('Mode of initial carriage',30,100,300),('ROAD',130,140,90),('Place of receipt',500,100,200),('Port Alpha',500,140,160),('Vessel name',30,200,200),('Sea Runner',30,240,160)])
    r=run(d,[{'token_id':'2','quote':'ROAD','field':'vessel','scope':'header'}],dtype='bill_of_lading')
    assert r.fields['vessel'].value=='Sea Runner'
    assert r.fields['place_of_receipt'].value=='Port Alpha'


def test_ambiguous_consignment_total_not_assumed_money():
    d=doc([('COMMERCIAL INVOICE',30,20,300),('Consignment total:',30,100,220),('8',300,100,30)])
    r=run(d,[{'token_id':'1','quote':'Consignment total','field':'subtotal','scope':'header'}])
    assert r.fields['subtotal'].value is None
    assert r.fields['subtotal'].status=='review'
