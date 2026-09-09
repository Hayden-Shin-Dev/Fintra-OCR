import json
from io import BytesIO
from unittest.mock import patch
from fintraocr.compact import CompactSelector
from fintraocr.mapping import MappingEngine
from fintraocr.layout import LayoutResolver,span
from fintraocr.schemas import ITEM_SCHEMAS
from tests.test_structural import doc,run

def test_model_can_abstain_without_forcing_a_field_or_invalid_label():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('Unrelated note',20,500,220)])
 response={'message':{'content':json.dumps({'1':None})}}
 with patch('fintraocr.compact.urlopen',return_value=BytesIO(json.dumps(response).encode())):
  selector=CompactSelector('mock');r=MappingEngine(selector).map(d)
 assert selector.metadata['model_abstentions']==['1']
 assert selector.metadata['invalid_model_labels']==[]
 assert all(f.value is None for f in r.fields.values())
 request=selector.metadata['trace'][0]['request']
 assert None in request['format']['properties']['1']['enum']

def test_conflicting_inline_values_in_one_token_require_review():
 from fintraocr.grounded import GroundedSelector
 from fintraocr.models import Selection
 d=doc([('COMMERCIAL INVOICE',20,20,250),('Buyer: Alpha Ltd. Buyer: Beta Ltd.',20,100,650)])
 s=GroundedSelector('mock')
 s.label_request=lambda document:{'document_type':'commercial_invoice','title_ids':['0'],'labels':[]}
 t=d.tokens[1]
 s.inline_fields={'buyer':[Selection(spans=[span(t,7,17)],label_spans=[span(t,0,5)],score=1,method='semantic_inline'),Selection(spans=[span(t,24,33)],label_spans=[span(t,18,23)],score=1,method='semantic_inline')]}
 r=MappingEngine(s).map(d)
 assert r.fields['buyer'].value is None
 assert r.fields['buyer'].status=='review'
 assert 'competing_inline_evidence' in r.fields['buyer'].issues

def test_merged_headings_remain_separate_columns():
 d=doc([('PACKING LIST',20,20,250),('Shipping Marks Description of Goods',20,100,600),('Packages',750,100,120),('BLUE CARTON',20,160,180),('Steel hinges',340,160,180),('2',750,160,30)])
 r=run(d,dtype='packing_list')
 assert len(r.items)==1
 assert r.items[0]['marks'].value=='BLUE CARTON'
 assert r.items[0]['description'].value=='Steel hinges'
 assert r.items[0]['package_count'].value=='2'

def test_wrapped_decimal_keeps_decimal_character_as_evidence():
 d=doc([('0.',700,100,30),('25',700,130,30)])
 resolver=LayoutResolver(d)
 s=resolver.select(d.tokens,ITEM_SCHEMAS['packing_list']['volume'],'volume',[span(d.tokens[0])])
 s.label_spans=[]
 assert s.method=='wrapped_decimal'
 assert d.tokens[0].text[s.spans[0].start:s.spans[0].end]=='0.'
 # Label validation is independent; inspect normalized raw without inventing punctuation.
 s.method='legacy'

def test_shared_wrapped_unit_uses_original_character_spans():
 d=doc([('ＣＢ',700,100,30),('M',700,130,30)])
 r=LayoutResolver(d);s=r.shared_unit([span(t) for t in d.tokens])
 f=MappingEngine().field(s,ITEM_SCHEMAS['packing_list']['volume_unit'],r.tokens)
 assert f.value=='m3'
 assert f.raw_text=='ＣＢ M'
 assert len(f.evidence)==2

def test_inline_case_difference_resolves_original_label_and_rejects_generated_value():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('BUYER: Regional Trading Corporation Ltd. Tax ID: Z-44 Address: Example Road',20,100,900)])
 response={'message':{'content':json.dumps({'1':'h.buyer'})}}
 inline={'message':{'content':json.dumps({'selections':[{'token_id':'1','field':'h.buyer','label':'Buyer','value':'Invented Party'}]})}}
 with patch('fintraocr.compact.urlopen',side_effect=[BytesIO(json.dumps(response).encode()),BytesIO(json.dumps(inline).encode())]):
  selector=CompactSelector('mock');selector.label_request(d)
 assert not selector.inline_fields

def test_inline_failure_trace_is_terminal():
 s=CompactSelector('mock')
 d=doc([('Buyer: Some party',20,100,200)])
 with patch('fintraocr.compact.urlopen',side_effect=TimeoutError('test timeout')):
  try:s.inline_request(d.tokens,{'h.buyer':'Buyer'})
  except TimeoutError:pass
 assert s.metadata['trace'][-1]['status']=='failed'

def test_handwritten_box_overlap_and_name_qualifier():
 d=doc([('BILL OF LADING',200,20,210),('#81',405,20,60),('Buyer:',30,100,70),('(Name) Different Trading',30,110,250),('Address 17 Lane',30,150,230)])
 r=run(d,dtype='bill_of_lading')
 assert r.fields['bill_of_lading_number'].value=='81'
 assert r.fields['buyer'].value=='Different Trading'

def test_unit_column_contains_quantity_and_unfamiliar_unit():
 d=doc([('BILL OF LADING',30,20,250),('Goods',30,100,150),('Unit',400,100,100),('Hinges',30,150,150),('12 bu',400,150,100),('Handles',30,210,150),('8 bu',400,210,100)])
 r=run(d,dtype='bill_of_lading')
 assert [row['quantity'].value for row in r.items]==['12','8']
 assert [row['unit'].value for row in r.items]==['bu','bu']

def test_inline_completed_header_does_not_own_next_table_heading():
 d=doc([('COMMERCIAL INVOICE',30,20,250),('P.O.# X-92',30,70,140),('Goods',30,100,150),('Quantity',400,100,120),('Valve',30,150,120),('3',400,150,30)])
 r=run(d)
 assert r.fields['purchase_order_number'].value=='X-92'
 assert r.items[0]['description'].value=='Valve'

def test_contact_label_cannot_be_promoted_to_port():
 d=doc([('BILL OF LADING',30,20,250),('Address',30,100,100),('City, Region',30,150,180)])
 r=run(d,[{'token_id':'1','quote':'Address','field':'port_of_discharge','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['port_of_discharge'].value is None

def test_korean_inline_weight_is_not_a_multiline_column_header():
 d=doc([('포장명세서',30,20,250),('중량단위: kg',30,70,200),('총중량: 18.20',30,100,200),('품명',30,200,100),('포장수',400,200,100),('총중량',700,200,100),('연결 부품',30,250,150),('2',400,250,30),('18.20',700,250,100)])
 r=run(d,dtype='packing_list')
 assert r.fields['gross_weight'].value=='18.20'
 assert r.fields['weight_unit'].value=='kg'

def test_inline_repeated_label_text_has_disjoint_value_span():
 d=doc([('BILL OF LADING',20,20,250),('Trucking Co. Relay Trucking Co.',20,100,400)])
 responses=[{'message':{'content':'{"1":"h.carrier"}'}},{'message':{'content':json.dumps({'selections':[{'token_id':'1','field':'h.carrier','label':'Trucking Co.','value':'Relay Trucking Co.'}]})}}]
 with patch('fintraocr.compact.urlopen',side_effect=[BytesIO(json.dumps(v).encode()) for v in responses]):
  r=MappingEngine(CompactSelector('mock')).map(d)
 assert r.fields['carrier'].value=='Relay Trucking Co.'
 assert r.fields['carrier'].label_evidence[0].end<=r.fields['carrier'].evidence[0].start

def test_postal_code_and_blank_totals_do_not_trigger_inline_model():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('ZIP CODE: 51723',20,100,200),('Total This Page :',20,200,200),('Consignment Total :',20,250,230)])
 with patch('fintraocr.compact.urlopen',return_value=BytesIO(b'{"message":{"content":"{}"}}')) as request:
  s=CompactSelector('mock');s.label_request(d)
 assert request.call_count==1
 assert not s.inline_fields

def test_narrative_shipper_clause_cannot_be_a_party_label():
 d=doc([('BILL OF LADING',20,20,250),('SHIPPER REQUESTS INSURANCE:',20,100,350),('REQUESTS',20,150,120)])
 r=run(d,[{'token_id':'1','quote':'SHIPPER REQUESTS INSURANCE','field':'shipper','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['shipper'].value is None
 with patch('fintraocr.compact.urlopen',return_value=BytesIO(b'{"message":{"content":"{}"}}')) as request:
  CompactSelector('mock').label_request(d)
 assert request.call_count==1

def test_model_candidates_include_headers_below_completed_inline_field():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('P.O.# Z-17',20,70,160),('Item / ID #',20,100,160),('Unit',400,100,100)])
 with patch('fintraocr.compact.urlopen',return_value=BytesIO(b'{"message":{"content":"{}"}}')):
  s=CompactSelector('mock');s.label_request(d)
 assert '2' in s.metadata['label_candidate_ids']

def test_cross_token_inline_label_stops_at_next_field():
 d=doc([('Shipment notes Mode of',20,100,300),('Transport: Sea / Road Ref: Z-18',20,125,450)])
 resolver=LayoutResolver(d)
 labels=[{'token_id':'1','start':22,'end':25,'field':'document_reference'}]
 from fintraocr.schemas import SCHEMAS
 proposal=resolver.fragmented_headers(labels,SCHEMAS['packing_list'])
 field=MappingEngine().field(proposal['mode_of_transport'],SCHEMAS['packing_list']['mode_of_transport'],resolver.tokens)
 assert field.value=='Sea / Road'
 assert len(field.label_evidence)==2

def test_missing_model_table_labels_get_a_targeted_evidence_pass():
 d=doc([('BILL OF LADING',20,20,250),('Item / ID #',20,100,160),('Unit',400,100,100),('Brass fitting',20,150,170),('4 bu',400,150,80)])
 responses=[{'message':{'content':'{}'}},{'message':{'content':'{"1":"i.description","2":"i.quantity"}'}}]
 with patch('fintraocr.compact.urlopen',side_effect=[BytesIO(json.dumps(v).encode()) for v in responses]):
  s=CompactSelector('mock');r=MappingEngine(s).map(d)
 assert r.items[0]['description'].value=='Brass fitting'
 assert r.items[0]['quantity'].value=='4'
 assert any(t['stage']=='table_coverage_repair' for t in s.metadata['trace'])

def test_product_size_is_not_quantity_unit():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('Product code',20,100,110),('Description',180,100,240),('Size',500,100,60),('Quantity',650,100,100),('ZX-11',20,150,90),('Cap',180,150,30),('M',500,150,20),('2',650,150,20)])
 r=run(d)
 assert r.items[0]['description'].value=='Cap'
 assert r.items[0]['product_size'].value=='M'
 assert r.items[0]['unit'].value is None

def test_packaging_in_marks_stays_separate_from_goods_quantity():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('Marks',20,100,120),('Description',250,100,150),('Quantity',500,100,100),('Amount',750,100,100),('RED A',20,150,90),('Bolts',250,150,100),('80 pcs',500,150,100),('20.00',750,150,80),('3 PKG',20,200,90)])
 r=run(d)
 assert r.items[0]['quantity'].value=='80'
 assert r.items[0]['package_count'].value=='3'
 assert r.items[0]['package_type'].value=='PKG'
 assert r.items[0]['marks'].value=='RED A'

def test_short_description_uses_alignment_learned_from_other_rows():
 lines=[('COMMERCIAL INVOICE',20,20,250),('Product code',20,100,100),('Description',330,100,180),('Quantity',700,100,100)]
 for i,name in enumerate(['Long brass connector assembly','Long steel connector assembly','Long copper connector assembly','Cap']):
  y=150+i*50;lines.extend([(f'Z-{i}',20,y,90),(name,180,y,400 if i<3 else 30),('2',700,y,20)])
 r=run(doc(lines))
 assert r.items[3]['product_code'].value=='Z-3'
 assert r.items[3]['description'].value=='Cap'
