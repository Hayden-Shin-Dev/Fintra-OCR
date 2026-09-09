"""Structural regressions discovered across the inventory; unrelated fixture values."""
import json
from io import BytesIO
from unittest.mock import patch
import pytest
from tests.test_structural import doc,run
from fintraocr.compact import CompactSelector
from fintraocr.mapping import MappingEngine
from fintraocr.normalize import normalize

@pytest.mark.parametrize('scale',[.6,1,1.8])
def test_complete_rows_establish_alignment_for_short_and_wrapped_names(scale):
 d=doc([('COMMERCIAL INVOICE',20,20,300),('Product Code',30,100,100),('Description of Goods',250,100,180),('Quantity',600,100,90),('Amount',800,100,80),
 ('A-14',30,160,65),('Nut',160,160,30),('8',600,160,15),('2.50',800,160,45),
 ('B-29',30,240,65),('Long connector',160,240,200),('9',600,240,15),('7.40',800,240,45),('assembly',160,266,85)],scale)
 r=run(d)
 assert [x['description'].value for x in r.items]==['Nut','Long connector assembly']
 assert [x['product_code'].value for x in r.items]==['A-14','B-29']

def test_invoice_and_lc_dates_are_distinct():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Invoice No. and date',20,100,200),('Z-418',20,140,80),('2021-11-23',300,140,140),('L/C No and Date',20,200,190),('LC-83',20,240,80),('2020-02-29',300,240,140)]))
 assert r.fields['issue_date'].value=='2021-11-23'
 assert r.fields['letter_of_credit_date'].value=='2020-02-29'
 assert r.fields['letter_of_credit_number'].value=='LC-83'

def test_item_purchase_orders_are_not_document_order_or_product_code():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,150),('Quantity',400,100,100),('PO No.',650,100,100),('Pipe',20,150,70),('2',400,150,20),('PO-22',650,150,80),('Valve',20,220,70),('3',400,220,20),('PO-38',650,220,80)]))
 assert r.fields['purchase_order_number'].value is None
 assert [row['purchase_order_number'].value for row in r.items]==['PO-22','PO-38']

def test_explicit_unfamiliar_unit_on_quantity_unit_second_line():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,150),("Q'ty / Unit",400,100,120),('Amount',650,100,100),('Rod',20,150,60),('6',400,150,20),('8.20',650,150,60),('Bag',400,180,60)]))
 assert r.items[0]['quantity'].value=='6'
 assert r.items[0]['unit'].value=='Bag'

def test_split_side_caption_names_party_above_caption_midpoint():
 r=run(doc([('PACKING LIST',20,20,200),('Cedar Export Ltd.',180,130,210),('15 Elm Road',180,160,180),('Notify',20,180,80),('Canada',180,190,100),('Party',20,205,80),('TEL: 100-200',180,220,160)]),dtype='packing_list')
 assert r.fields['notify_party'].value=='Cedar Export Ltd.'
 assert [e.selected_text for e in r.fields['notify_party'].label_evidence]==['Notify','Party']

def test_same_to_reference_preserves_referral_and_actual_company():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Buyer',20,100,100),('Same to consignee',20,140,240),('Consignee',20,200,120),('Maple Co.',20,240,130)]))
 assert r.fields['buyer'].value=='Maple Co.'
 assert r.fields['buyer'].reference_field=='consignee'
 assert r.fields['buyer'].reference_evidence[0].selected_text=='Same to consignee'

def test_phone_caption_and_signature_are_not_party_roles():
 d=doc([('BILL OF LADING',20,20,300),('Consignee',20,100,120),('Oak Ltd.',20,140,130),('Consignee Phone No.',20,180,200),('+13-202-4567',20,220,200),('Signed by',20,280,130),('Birch Ltd.',20,320,130)])
 r=run(d,[{'token_id':'3','quote':'Consignee Phone No.','field':'consignee','scope':'header'},{'token_id':'5','quote':'Signed by','field':'forwarding_agent','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['consignee'].value=='Oak Ltd.'
 assert r.fields['forwarding_agent'].value is None

def test_inline_vessel_and_adjacent_voyage_are_not_labels_for_other_values():
 r=run(doc([('BILL OF LADING',20,20,300),('Vessel/voy. NORTHERN STAR',20,100,350),('V.824',450,100,90),('Port of Discharge',450,160,230),('Odense, Denmark',450,200,210)]),dtype='bill_of_lading')
 assert r.fields['vessel'].value=='NORTHERN STAR'
 assert r.fields['voyage'].value=='V.824'
 assert r.fields['port_of_discharge'].value=='Odense, Denmark'

def test_combined_fmc_caption_distinguishes_name_and_registration():
 r=run(doc([('BILL OF LADING',20,20,300),('Forwarding Agent/FMC No.',20,100,300),('Cedar Freight Ltd.',20,140,230),('Booking No.',500,170,150),('778812',500,210,100)]),dtype='bill_of_lading')
 assert r.fields['forwarding_agent'].value=='Cedar Freight Ltd.'
 assert r.fields['forwarding_agent_number'].value is None

def test_country_and_date_normalization_keep_original_tokens():
 assert normalize('The Philippines','country')[0]=='PH'
 assert normalize('Port City, Denmark','country')[0]=='DK'
 assert normalize('Jun 12,2011','date')[0]=='2011-06-12'
 assert normalize('22-0ct-2007','date')[0] is None

def test_incoterms_cannot_accept_a_payment_caption():
 assert normalize('payment due date','incoterms')[0] is None
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Terms of delivery and payment',20,100,350),('FCA, Payment term: By T/T',20,140,350)]))
 assert r.fields['incoterms'].value=='FCA'
 assert r.fields['payment_terms'].value=='By T/T'

def test_model_cannot_propose_a_context_value_outside_candidate_enum():
 d=doc([('COMMERCIAL INVOICE',20,20,300),('Invoice Number',20,100,200),('491773',20,140,100)])
 with patch('fintraocr.compact.urlopen',return_value=BytesIO(b'{"message":{"content":"{\\"2\\":\\"h.invoice_number\\"}"}}')):
  s=CompactSelector('mock');s.label_request(d)
 request=next(x['request'] for x in s.metadata['trace'] if x['stage']=='label_selection')
 assert '2' not in request['format']['properties']
 assert s.metadata['invalid_model_labels']==[['2','h.invoice_number']]
 assert isinstance(json.loads(request['messages'][1]['content'])['allowed_fields'],dict)

def test_a_value_must_not_extend_a_multiline_header():
 r=run(doc([('BILL OF LADING',20,20,250),('Container No.',20,100,150),('Description',260,100,160),('Gross Weight',550,100,170),('Measurement',800,100,160),('ABCU1234567',20,150,150),('Hinge',260,150,100),('25KG',550,150,70),('4 CBM',800,150,100)]),dtype='bill_of_lading')
 assert len(r.items)==1
 assert r.items[0]['container_number'].value=='ABCU1234567'
 assert r.items[0]['description'].value=='Hinge'

def test_split_words_are_read_left_to_right_within_one_line():
 r=run(doc([('COMMERCIAL INVOICE',20,20,250),('Description',20,100,260),('Quantity',500,100,100),('Amount',750,100,100),('Long',20,152,60),('connector',85,150,170),('2',500,150,20),('5.00',750,150,60)]))
 assert r.items[0]['description'].value=='Long connector'

def test_hazardous_marker_is_not_goods_unit():
 d=doc([('BILL OF LADING',20,20,250),('Description',20,100,150),('H/M',300,100,60),('Packages',500,100,120),('Weight',750,100,120),('Valve',20,150,100),('X',300,150,20),('4 PKG',500,150,90),('9 KG',750,150,90)])
 r=run(d,[{'token_id':'2','quote':'H/M','field':'unit','scope':'item'}],dtype='bill_of_lading')
 assert r.items[0]['unit'].value is None

def test_signature_name_is_not_forwarding_agent_label():
 d=doc([('BILL OF LADING',20,20,250),('BY X',20,150,70),('CEDAR LOGISTICS',100,150,220),('DRIVERS SIGNATURE',20,200,240),('VICE PRESIDENT',20,240,220)])
 r=run(d,[{'token_id':'2','quote':'CEDAR LOGISTICS','field':'forwarding_agent','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['forwarding_agent'].value is None

def test_real_token_count_avoids_byte_based_context_overallocation():
 from fintraocr.context_budget import context_budget
 context,info=context_budget('qwen3.5:4b',[{'content':'The field contains the invoice reference. '*450}],1800)
 assert info['method']=='qwen35_tokenizer_with_256_frame_reserve'
 assert context==16384
 assert info['required_tokens']<16384

def test_compound_identifier_caption_does_not_assert_two_roles_for_one_value():
 r=run(doc([('BILL OF LADING',20,20,250),('B/L No / PO No',20,100,250),('REF-4482',20,150,130)]),dtype='bill_of_lading')
 for key in ('bill_of_lading_number','purchase_order_number'):
  assert r.fields[key].value is None
  assert r.fields[key].null_reason=='conflicting_span_reuse'

def test_generic_terms_cannot_become_issue_location():
 d=doc([('PACKING LIST',20,20,250),('Terms',20,100,100),('Sales by specification',20,150,300)])
 r=run(d,[{'token_id':'1','quote':'Terms','field':'issue_place','scope':'header'}],dtype='packing_list')
 assert r.fields['issue_place'].value is None

@pytest.mark.parametrize('code',['DAF','DES','DEQ','DDU','DAT'])
def test_legacy_delivery_codes_are_preserved_without_conversion(code):
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Terms of delivery and payment',20,100,360),(code+', Payment term: By D/P',20,150,340)]))
 assert r.fields['incoterms'].value==code
 assert r.fields['payment_terms'].value=='By D/P'

def test_split_weight_footnote_and_plural_volume_preserve_total():
 d=doc([('BILL OF LADING',20,20,250),('Description',20,100,200),('GROSS',500,100,100),('WEIGHT*',500,123,120),('MEASUREMENTS',750,100,190),('Valve',20,170,100),('15 KG',500,170,100),('2 CBM',750,170,100),('TOTAL',20,260,100),('15 KG',500,260,100),('2 CBM',750,260,100)])
 r=run(d,dtype='bill_of_lading')
 assert r.fields['gross_weight'].value=='15'
 assert r.fields['volume'].value=='2'
 assert r.items[0]['gross_weight'].value=='15'

@pytest.mark.parametrize('position',[(20,135),(430,102)])
def test_on_date_requires_adjacent_issuance_context(position):
 r=run(doc([('BILL OF LADING',20,20,250),('ISSUED AT Copenhagen',20,100,320),('ON 2021-11-23',*position,230)]),dtype='bill_of_lading')
 assert r.fields['issue_date'].value=='2021-11-23'
 assert r.fields['issue_place'].value=='Copenhagen'

def test_movement_value_cannot_be_a_header_label():
 d=doc([('BILL OF LADING',20,20,250),('CY/CFS',20,100,100),('Number of Originals',20,150,240)])
 r=run(d,[{'token_id':'1','quote':'CY/CFS','field':'mode_of_transport','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['mode_of_transport'].value is None

def test_wrapped_explanatory_value_cannot_label_a_transport_field():
 d=doc([('PACKING LIST',20,20,250),('Reference: R-28 Reason for export:',20,100,400),('Components for laboratory evaluation',20,135,400),('Cargo details',20,180,200)])
 r=run(d,[{'token_id':'2','quote':'Components for laboratory evaluation','field':'movement_type','scope':'header'}],dtype='packing_list')
 assert r.fields['movement_type'].value is None

def test_secondary_qualified_document_title_is_not_a_reference_label():
 d=doc([('BILL OF LADING',20,20,250),('Sample Bill of Lading',20,100,300),('Cedar Freight LLC',20,150,250)])
 r=run(d,[{'token_id':'1','quote':'Sample Bill of Lading','field':'document_reference','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['document_reference'].value is None

def test_material_column_cannot_poison_product_codes():
 d=doc([('COMMERCIAL INVOICE',20,20,260),('Code',20,100,100),('Description',200,100,180),('Material',500,100,130),('QTY',800,100,100),('R-25',20,150,80),('Valve',200,150,130),('Brass',500,150,100),('2',800,150,30)])
 r=run(d,[{'token_id':'3','quote':'Material','field':'product_code','scope':'item'}])
 assert r.items[0]['product_code'].value=='R-25'
 assert r.items[0]['material'].value=='Brass'

def test_shipping_origin_country_is_not_loading_port():
 d=doc([('COMMERCIAL INVOICE',20,20,260),('Ship from: Denmark',20,100,280)])
 r=run(d,[{'token_id':'1','quote':'Ship from','field':'port_of_loading','scope':'header'}])
 assert r.fields['shipping_origin'].value=='Denmark'
 assert r.fields['port_of_loading'].value is None

def test_table_values_are_context_but_not_unbounded_label_targets():
 d=doc([('COMMERCIAL INVOICE',20,20,260),('Description',20,100,200),('Quantity',500,100,150),('Amount',800,100,100),('Valve',20,150,100),('2',500,150,30),('5.00',800,150,100),('Connector',20,230,130),('3',500,230,30),('9.00',800,230,100),('Bracket',20,310,100),('4',500,310,30),('12.00',800,310,100)])
 with patch('fintraocr.compact.urlopen',return_value=BytesIO(b'{"message":{"content":"{}"}}')):
  s=CompactSelector('mock');s.label_request(d)
 request=next(t['request'] for t in s.metadata['trace'] if t['stage']=='label_selection')
 content=json.loads(request['messages'][1]['content'])
 assert content['OCR_context_all_tokens']['10']=='Bracket'
 assert '10' not in content['classify_only_these_ids']
 assert {'1','2','3'}<=set(content['classify_only_these_ids'])

def test_commercial_disclaimer_is_not_reference_label():
 d=doc([('PACKING LIST',20,20,250),('Demonstration goods - not for sale',20,100,400),('No commercial value',20,150,280)])
 r=run(d,[{'token_id':'1','quote':'Demonstration goods - not for sale','field':'document_reference','scope':'header'}],dtype='packing_list')
 assert r.fields['document_reference'].value is None

def test_punctuation_cannot_become_a_name():
 assert normalize('.', 'text')[0] is None
 assert normalize('---', 'party')[0] is None

def test_station_identifier_does_not_establish_shipping_origin():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('Code of station: 543210 CEDAR TERMINAL',20,100,430)])
 r=run(d,[{'token_id':'1','quote':'Code of station','field':'shipping_origin','scope':'header'}])
 assert r.fields['shipping_origin'].value is None

def test_wrapped_abbreviated_packages_caption_is_not_goods_quantity():
 d=doc([('BILL OF LADING',20,20,260),('Description',20,100,200),('NO. OF',500,100,100),('PKGS.',500,123,100),('Gross Weight',800,100,180),('Valve',20,180,100),('8 PKG',500,180,100),('12 KG',800,180,100)])
 r=run(d,[{'token_id':'2','quote':'NO. OF','field':'quantity','scope':'item'}],dtype='bill_of_lading')
 assert r.items[0]['package_count'].value=='8'
 assert r.items[0]['quantity'].value is None and r.items[0]['unit'].value is None

def test_legal_clause_fragment_cannot_compete_with_issue_location():
 d=doc([('BILL OF LADING',20,20,250),('transported to such place as agreed,',20,100,400),('authorized or',20,140,200),('Place and Date of issue',20,220,350),('Copenhagen, Denmark',20,260,280),('2022-11-23',500,260,180)])
 r=run(d,[{'token_id':'1','quote':'transported to such place as agreed,','field':'issue_place','scope':'header'}],dtype='bill_of_lading')
 assert r.fields['issue_place'].value=='Copenhagen, Denmark'

def test_quantity_of_sets_is_quantity_not_package_count():
 d=doc([('COMMERCIAL INVOICE',20,20,250),('Description',20,100,200),('Q-TY OF',500,100,150),('SETS',500,123,100),('Amount',800,100,100),('Connector',20,180,170),('6',500,180,30),('18.00',800,180,100)])
 r=run(d,[{'token_id':'3','quote':'SETS','field':'package_count','scope':'item'}])
 assert r.items[0]['quantity'].value=='6'
 assert r.items[0]['unit'].value=='set'
 assert r.items[0]['package_count'].value is None

def test_numeric_material_needs_review():
 assert normalize('316','material')[0] is None
 assert normalize('316 stainless steel','material')[0]=='316 stainless steel'

def test_unknown_weight_caption_without_unit_needs_review():
 d=doc([('BILL OF LADING',20,20,250),('Description',20,100,200),('Unresolved caption',500,100,230),('Quantity',800,100,150),('Valve',20,160,100),('123',500,160,80),('2',800,160,30)])
 r=run(d,[{'token_id':'2','quote':'Unresolved caption','field':'gross_weight','scope':'item'}],dtype='bill_of_lading')
 assert r.items[0]['gross_weight'].value is None
 assert r.items[0]['gross_weight'].raw_text=='123'
