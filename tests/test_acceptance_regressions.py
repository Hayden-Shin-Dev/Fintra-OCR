"""Common defects found in unseen forms, using unrelated values and geometry."""
from tests.test_structural import doc,run
from fintraocr.domain import semantic_label

def test_unlabelled_trailing_measures_are_preserved_without_inventing_item_or_total():
 for scale in (.6,1,1.8):
  lines=[('PACKING LIST',20,20,300),('Description',20,110,220),('Net Weight',450,110,180),('Gross Weight',750,110,180),
   ('Fasteners',20,180,180),('12 KG',450,180,100),('15 KG',750,180,100),('18 KG',450,290,100),('23 KG',750,290,100)]
  r=run(doc(lines,scale),dtype='packing_list')
  assert len(r.items)==1
  assert r.fields['net_weight'].value is None
  assert 'unassigned_table_row_requires_review' in r.issues
  assert [s['token_id'] for s in r.mapping_metadata['table_diagnostics'][0]['region_ocr_evidence']]==['7','8']
  with_footer=lines+[('Certification',20,325,200),('Shipping mark',400,325,180)]
  assert len(run(doc(with_footer,scale),dtype='packing_list').items)==1
  lines.append(('Brackets',20,290,180))
  assert len(run(doc(lines,scale),dtype='packing_list').items)==2
  lines[-1]=('TOTAL',20,290,180)
  r=run(doc(lines,scale),dtype='packing_list')
  assert len(r.items)==1 and r.fields['net_weight'].value=='18'

def test_shipping_marks_and_split_package_caption_establish_cargo_columns():
 for scale in (.6,1,1.8):
  lines=[('BILL OF LADING',20,20,300),('Marks & Numbers',20,110,180),
   ('No of Pkgs or',250,100,180),('Shipping Units',250,125,180),
   ('Description of Goods',470,110,230),('Gross Weight',780,110,180),
   ('Z-428',20,200,100),('6 PKG',250,200,100),('Fasteners',470,200,160),('22 KG',780,200,100)]
  r=run(doc(lines,scale),dtype='bill_of_lading')
  assert len(r.items)==1
  assert r.items[0]['package_count'].value=='6'
  assert r.items[0]['marks'].value=='Z-428'
  assert {e.selected_text for e in r.items[0]['package_count'].label_evidence}=={'No of Pkgs or','Shipping Units'}
  assert semantic_label('Marks and numbers must be shown on all packages') is None

def test_inline_shipping_mark_does_not_anchor_a_false_goods_table():
 lines=[('PACKING LIST',20,20,300),('Shipping mark: 2 ~ 6',400,100,240),('ACME',700,100,90),
  ('Description',20,250,220),('Quantity',350,250,150),('Net Weight',570,250,150),('Gross Weight',800,250,180),
  ('Fasteners',20,310,150),('6',350,310,50),('12 KG',570,310,100),('15 KG',800,310,100)]
 r=run(doc(lines),dtype='packing_list',labels=[{'token_id':'2','quote':'ACME','field':'package_count','scope':'item'}])
 assert len(r.items)==1
 assert r.items[0]['gross_weight'].value=='15' and r.items[0]['package_type'].value is None

def test_declared_value_basis_selector_preserves_amount_and_requests_review():
 for scale in (.6,1,1.8):
  for basis in ['PER PACKAGE / O KILOGRAM WEIGHT / O OR ENTIRE SHIPMENT','PER KILOGRAM']:
   lines=[('BILL OF LADING',20,20,300),('Declared Value: US$ 123.45',20,200,310),(basis,450,200,480)]
   result=run(doc(lines,scale),dtype='bill_of_lading').fields['declared_value']
   assert result.value is None and result.status=='review'
   assert result.raw_text=='123.45'
   assert 'declared_value_basis_requires_review' in result.issues
   assert result.reference_evidence[0].selected_text==basis
  # General liability prose is not an amount's basis selector.
  lines[-1]=('Carrier liability is limited to a sum per package.',20,250,700)
  assert run(doc(lines,scale),dtype='bill_of_lading').fields['declared_value'].value=='123.45'

def test_service_mode_does_not_assert_a_named_route_location():
 for scale in (.6,1,1.8):
  for mode in ['CY/CY','CFS / CY','CY-CFS','DOOR/SD']:
   result=run(doc([('BILL OF LADING',20,20,300),('Place of Receipt: '+mode,20,200,500)],scale),dtype='bill_of_lading').fields['place_of_receipt']
   assert result.value is None and result.status=='review' and result.raw_text==mode
   assert 'service_mode_is_not_named_location' in result.issues
  result=run(doc([('BILL OF LADING',20,20,300),('Place of Receipt: Bergen CY',20,200,500)],scale),dtype='bill_of_lading').fields['place_of_receipt']
  assert result.value=='Bergen CY'
  # Rejecting an observed cell must not substitute a nearby unrelated caption.
  result=run(doc([('BILL OF LADING',20,20,300),('Place of Receipt',350,200,240),
   ('CFS/CFS',350,235,120),('Charges to be:',630,230,190)],scale),dtype='bill_of_lading').fields['place_of_receipt']
  assert result.value is None and result.status=='review' and result.raw_text=='CFS/CFS'
  result=run(doc([('BILL OF LADING',20,20,300),('Place of Delivery',20,200,250),
   ('Final Destination',500,200,250),('CY/CFS',20,235,150),('Odense, Denmark',500,235,250)],scale),dtype='bill_of_lading')
  assert result.fields['place_of_delivery'].value=='Odense, Denmark'
  assert result.mapping_metadata['rejected_location_candidates']

def test_port_abbreviations_require_paired_maritime_context_and_typed_locations():
 for scale in (.6,1,1.8):
  r=run(doc([('PACKING LIST',20,20,300),('POL: Bergen, Norway',350,110,320),
   ('P.O.D.: Odense, Denmark',350,155,340),('Vessel: Northern Light',350,235,330)],scale),dtype='packing_list')
  assert r.fields['port_of_loading'].value=='Bergen, Norway'
  assert r.fields['port_of_discharge'].value=='Odense, Denmark'
  assert r.fields['port_of_discharge'].label_evidence[0].selected_text=='P.O.D.:'
  for lines in [
   [('POD: Signed by receiver',350,110,320),('Vessel: Northern Light',350,200,330)],
   [('POL: Bergen, Norway',350,110,320),('POD: Signed, Denmark',350,155,340)],
   [('POL: Bergen, Norway',350,110,320),('POD: 2024-04-12',350,155,340),('Vessel: Northern Light',350,235,330)]]:
   r=run(doc([('PACKING LIST',20,20,300)]+lines,scale),dtype='packing_list')
   assert r.fields['port_of_discharge'].value is None

def test_package_caption_below_goods_body_has_document_scope():
 for scale in (.6,1,1.8):
  lines=[('PACKING LIST',20,20,300),('Description',20,110,180),('Quantity',400,110,150),
   ('Coupler',20,170,180),('7',400,170,50),('Bracket',20,260,180),('11',400,260,50),
   ('Number of Packages: 8 PKG',20,410,330)]
  r=run(doc(lines,scale),dtype='packing_list')
  assert r.fields['total_packages'].value=='8'
  assert r.fields['total_packages'].evidence[0].selected_text=='8'
  assert len(r.items)==2
  # An annotation within the goods body does not establish a document total.
  lines[-1]=('Number of Packages: 8 PKG',20,215,330)
  assert run(doc(lines,scale),dtype='packing_list').fields['total_packages'].value is None

def test_populated_charge_columns_establish_freight_terms_without_extra_title():
 for scale in (.6,1,1.8):
  for paid,collect,money_x,expected in [('Prepaid','Collect',600,'PREPAID'),('Collect','Prepaid',600,'COLLECT')]:
   lines=[('BILL OF LADING',20,20,300),('Charges',20,120,120),('Rate',350,120,80),
    (paid,560,120,160),(collect,800,120,160),('Handling',20,170,140),('14.00',350,170,80),('$98.00',money_x,170,80)]
   r=run(doc(lines,scale),dtype='bill_of_lading')
   assert r.fields['freight_terms'].value==expected
   assert r.fields['freight_terms'].evidence[0].selected_text.upper()==expected
   # Both columns populated: do not assert a single payment basis.
   lines.append(('$42.00',840,170,80))
   assert run(doc(lines,scale),dtype='bill_of_lading').fields['freight_terms'].value is None
  assert run(doc([('BILL OF LADING',20,20,300),('Prepaid',560,120,160),('Collect',800,120,160),('$98.00',600,170,80)],scale),dtype='bill_of_lading').fields['freight_terms'].value is None

def test_volume_in_explicit_total_block_keeps_scope_and_unit_evidence():
 for scale in (.6,1,1.8):
  lines=[('PACKING LIST',20,20,300),('Description',20,110,180),('Quantity',400,110,150),
   ('Coupler',20,170,180),('7',400,170,50),('Total Gross Weight: 125 KG',20,310,400),('4.25 CBM',315,350,140)]
  r=run(doc(lines,scale),dtype='packing_list')
  assert r.fields['volume'].value=='4.25'
  assert r.fields['volume_unit'].value=='m3'
  assert r.fields['volume'].evidence[0].selected_text=='4.25'
  assert r.fields['volume'].reference_evidence
  lines[-1]=('120 x 80 x 60 cm',315,350,200)
  assert run(doc(lines,scale),dtype='packing_list').fields['volume'].value is None
  lines[-1]=('4.25 CBM',315,350,140)
  lines[-2]=('Gross Weight: 125 KG',20,310,400)
  assert run(doc(lines,scale),dtype='packing_list').fields['volume'].value is None
  lines[-2]=('Total Gross Weight: 125 KG',20,310,400)
  lines.append(('150 CFT',315,380,140))
  ambiguous=run(doc(lines,scale),dtype='packing_list').fields['volume']
  assert ambiguous.value is None and ambiguous.status=='review'

def test_payment_schedule_preserves_instalments_and_wrapped_clause():
 for scale in (.6,1,2):
  r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Payment terms: By transfer',500,100,290),
   ('15 % upon order confirmation',500,130,330),('85 % after receipt of the',500,160,300),
   ('shipping documents',550,190,210),('Signature',500,220,130),('Someone Else',500,250,180),
   ('Other party',20,130,150)],scale),labels=[{'token_id':'4','quote':'shipping documents','field':'routing_instructions','scope':'header'}])
  assert r.fields['payment_terms'].value=='By transfer 15 % upon order confirmation 85 % after receipt of the shipping documents'
  assert [e.token_id for e in r.fields['payment_terms'].evidence]==['1','2','3','4']
  assert r.fields['routing_instructions'].value is None

def test_payment_schedule_stops_at_other_field_or_unrelated_percent():
 for following in ['Tax: 15 %','15 % cotton','Remarks']:
  r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Payment terms: By transfer',500,100,290),
   (following,500,130,330),('85 % after shipment',500,160,300)]))
  assert r.fields['payment_terms'].value=='By transfer'

def test_wrapped_packing_explanation_preserves_literal_measure():
 from fintraocr.layout import LayoutResolver
 from fintraocr.schemas import SCHEMAS
 from fintraocr.mapping import MappingEngine
 for scale in (.6,1,1.7):
  d=doc([('PACKING LIST',20,20,300),('Total Volume:',500,100,160),
   ('84 CBM (12',500,125,140),('cartons x 7.5',500,150,160),('CBM each)',500,175,120)],scale)
  resolver=LayoutResolver(d)
  label={'token_id':'1','start':0,'end':12,'field':'volume'}
  s=resolver.header(label,SCHEMAS['packing_list']['volume'],'volume',[label],set())
  f=MappingEngine().field(s,SCHEMAS['packing_list']['volume'],resolver.tokens)
  assert f.value=='84'  # Printed value wins even when the explanation does not reconcile.
  assert f.evidence[0].token_id=='2' and f.evidence[0].selected_text=='84'

def test_measure_explanation_does_not_choose_conversions_or_dimensions():
 from fintraocr.layout import explained_measure_end
 for raw in ['84 CBM (2966 ft3)','84 CBM (12 cartons x 7 kg each)',
             '84 CBM (12 x 7 x 4 cm)','84 CBM (12 cartons x 7 CBM each',
             '84 CBM (12 cartons x 7 CBM each) or 90 CBM']:
  assert explained_measure_end(raw,'volume') is None
 assert explained_measure_end('84 CBM (12 cartons x 7 CBM each)','volume') is not None
 assert explained_measure_end('84 CBM (12 cartons x 7 CBM each)','gross_weight') is None

def test_document_volume_suffix_unit_keeps_exact_evidence_without_model_unit_label():
 r=run(doc([('PACKING LIST',20,20,300),('Total Volume:',500,100,160),
  ('84 CBM (12',500,125,140),('cartons x 7.5',500,150,160),('CBM each)',500,175,120)]),
  labels=[{'token_id':'1','quote':'Total Volume','field':'volume','scope':'header'}],dtype='packing_list')
 assert r.fields['volume'].value=='84'
 unit=r.fields['volume_unit']
 assert unit.value=='m3' and unit.evidence[0].selected_text=='CBM'
 assert unit.evidence[0].token_id=='2' and unit.evidence[0].start==3
 assert unit.label_evidence[0].selected_text=='Total Volume'

def test_document_volume_does_not_promote_length_suffix_to_volume_unit():
 r=run(doc([('PACKING LIST',20,20,300),('Total Volume:',500,100,160),('84 feet',500,125,140)]),
  labels=[{'token_id':'1','quote':'Total Volume','field':'volume','scope':'header'}],dtype='packing_list')
 assert r.fields['volume_unit'].value is None

def test_total_volume_unit_does_not_validate_mislabelled_dimensions_column():
 r=run(doc([('PACKING LIST',20,20,300),('Description',20,100,160),('Dimensions (cm)',500,100,190),
  ('Couplers',20,150,140),('20x30x40',500,150,140),('Total Volume:',20,300,170),('84 CBM',220,300,100)]),
  labels=[{'token_id':'1','quote':'Description','field':'description','scope':'item'},
   {'token_id':'2','quote':'Dimensions (cm)','field':'volume','scope':'item'},
   {'token_id':'5','quote':'Total Volume','field':'volume','scope':'header'}],dtype='packing_list')
 assert r.fields['volume_unit'].value=='m3'
 assert r.items[0]['volume'].value is None
 assert r.items[0]['volume_unit'].value is None

def test_empty_receipt_does_not_steal_adjacent_party_address():
 r=run(doc([('BILL OF LADING',20,20,300),
  ('For delivery of goods place apply to :',650,150,400),
  ('Example Logistics Ltd',650,180,320),
  ('48 Dock Road, OSLO',650,210,310),
  ('Place of Receipt',310,220,220),('CFS/CY',360,255,100)]))
 assert r.fields['place_of_receipt'].value is None
 assert r.fields['delivery_party'].value=='Example Logistics Ltd'

def test_receipt_inline_location_without_neighbor_owner_is_preserved():
 r=run(doc([('BILL OF LADING',20,20,300),
  ('Place of Receipt',20,150,220),('OSLO, NORWAY',300,150,220)]))
 assert r.fields['place_of_receipt'].value=='OSLO, NORWAY'

def test_currency_requires_monetary_column_alignment_and_agreement():
 lines=[('COMMERCIAL INVOICE',20,20,300),('Description',20,100,180),
  ('Quantity',250,100,120),('Unit Price',450,100,120),('Amount',700,100,100),
  ('EUR',470,135,60),('EUR',710,135,60),('Coupler',20,200,150),
  ('3',270,200,30),('12',470,200,40),('36',710,200,40)]
 r=run(doc(lines))
 assert r.fields['currency'].value=='EUR'
 assert r.fields['currency'].evidence[0].selected_text=='EUR'
 changed=lines.copy();changed[6]=('USD',710,135,60)
 r=run(doc(changed))
 assert r.fields['currency'].value is None
 assert r.fields['currency'].status=='review'
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Bank note: USD account',20,900,350)]))
 assert r.fields['currency'].value is None

def test_shared_container_and_seal_header_preserves_distinct_identifiers():
 lines=[('BILL OF LADING',20,20,300),('Marks and Numbers',20,100,190),
  ('(Container No. & Seal',20,125,210),('No.)',20,150,50),
  ('Packages',280,100,140),('Description',480,100,170),('Gross Weight',750,100,150),
  ('ABCU1234567',20,200,170),('9 PKG',280,200,90),('Couplers',480,200,140),
  ('81 KG',750,200,80),('S98765',20,230,110)]
 r=run(doc(lines))
 assert len(r.items)==1
 assert r.items[0]['container_number'].value=='ABCU1234567'
 assert r.items[0]['seal_number'].value=='S98765'
 assert r.items[0]['marks'].value is None

def test_merged_description_weight_requires_neighbor_column_geometry():
 lines=[('BILL OF LADING',20,20,300),('Packages',20,100,140),
  ('Description',230,100,180),('Gross Weight',640,100,150),('Volume',850,100,100),
  ('5 PKG',20,200,90),('Industrial coupler type Z7 81KG',230,200,520),('3 CBM',850,200,100)]
 r=run(doc(lines))
 assert r.items[0]['description'].value=='Industrial coupler type Z7'
 assert r.items[0]['gross_weight'].value=='81'
 assert r.items[0]['gross_weight'].evidence[0].selected_text=='81'
 assert r.items[0]['gross_weight_unit'].value=='kg'
 # A product's capacity inside its description is not a shipment weight.
 lines[6]=('Industrial coupler type Z7 81KG',230,200,300)
 r=run(doc(lines))
 assert r.items[0]['description'].value=='Industrial coupler type Z7 81KG'
 assert r.items[0]['gross_weight'].value is None

def test_freight_options_need_populated_charge_column_not_proximity():
 from fintraocr.layout import LayoutResolver
 base=[('BILL OF LADING',20,20,300),('Freight and charges',20,100,210),
  ('PREPAID',450,100,100),('COLLECT',700,100,100)]
 assert LayoutResolver(doc(base)).freight_column() is None
 result=run(doc(base+[('$48.25',450,150,90)]))
 assert result.fields['freight_terms'].value=='PREPAID'
 assert result.mapping_metadata['freight_column_evidence']['charge_spans']
 assert LayoutResolver(doc(base+[('$48.25',450,150,90),('$19.50',700,150,90)])).freight_column() is None

def test_terms_only_page_does_not_produce_transaction_fields_or_call_model():
 from fintraocr.grounded import GroundedSelector
 from fintraocr.mapping import MappingEngine
 selector=GroundedSelector('mock')
 def forbidden(_):raise AssertionError('Terms-only pages should not invoke model')
 selector.label_request=forbidden
 d=doc([('Bill of Lading · Terms and Conditions',20,20,550),
  ('Vessel',20,100,100),('means any ship operated by the carrier',160,100,400)])
 r=MappingEngine(selector).map(d)
 assert r.document_type=='unknown'
 assert r.fields=={} and r.items==[]
 assert r.ocr==d

def test_transaction_heading_with_terms_keeps_real_fields():
 r=run(doc([('BILL OF LADING',20,20,300),('B/L No. X-781',20,100,220),
  ('Bill of Lading - Terms and Conditions',20,900,500)]))
 assert r.document_type=='bill_of_lading'
 assert r.fields['bill_of_lading_number'].value=='X-781'

def test_inline_month_date_is_not_rejected_as_postal_address():
 r=run(doc([('PACKING LIST',20,20,300),('Date: October 4, 2025',20,100,300)]),
  labels=[{'token_id':'1','quote':'Date','field':'issue_date','scope':'header'}])
 assert r.fields['issue_date'].value=='2025-10-04'

def test_total_goods_column_does_not_become_document_total():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,170),
  ('Quantity',250,100,120),('Unit Price (EUR)',450,100,180),('TOTAL',750,100,110),
  ('Washer',20,170,140),('4',250,170,30),('12.50',450,170,90),('50.00',750,170,90)]))
 assert r.fields['total_amount'].value is None
 assert r.items[0]['amount'].value=='50.00'
 assert r.fields['currency'].value=='EUR'

def test_product_unit_total_cannot_compete_with_package_total():
 r=run(doc([('PACKING LIST',20,20,300),('Description',20,100,170),('Rolls',250,100,90),
  ('Net Weight',450,100,150),('Fabric',20,170,140),('10',250,170,40),('50 KG',450,170,90),
  ('Total Cartons: 8',20,400,240),('Total Rolls: 80',20,450,240)]),labels=[
   {'token_id':'2','quote':'Rolls','field':'quantity','scope':'item'},
   {'token_id':'8','quote':'Total Rolls','field':'total_packages','scope':'header'}])
 assert r.fields['total_packages'].value=='8'
def test_proforma_abbreviation_retains_own_identifier_role():
 assert semantic_label('P/I No. REF-028')[0]=='proforma_invoice_number'
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('P/I No. REF-028',20,100,250)]))
 assert r.fields['proforma_invoice_number'].value=='REF-028'
 assert r.fields['invoice_number'].value is None

def test_inline_voyage_and_compound_issuance_preserve_distinct_values():
 r=run(doc([('BILL OF LADING',20,20,300),('Voyage No. V.902',20,100,200),('Place and date ofissueFEB 21, 2024',20,250,400),('OSLO, NORWAY',20,285,180)]))
 assert r.fields['voyage'].value=='V.902'
 assert r.fields['issue_date'].value=='2024-02-21'
 assert r.fields['issue_place'].value=='OSLO, NORWAY'

def test_dated_onboard_caption_requires_nearby_event_evidence():
 r=run(doc([('BILL OF LADING',20,20,300),('LADEN ON BOARD THE VESSEL',20,250,350),('Date: FEB 21, 2024',20,285,230)]))
 assert r.fields['on_board_date'].value=='2024-02-21'
 assert r.fields['issue_date'].value is None
 r=run(doc([('BILL OF LADING',20,20,300),('Date: FEB 21, 2024',20,285,230)]))
 assert r.fields['on_board_date'].value is None
def test_stacked_invoice_number_and_date_label_uses_both_fragments():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Invoice',20,100,95),('No. & Date',20,126,110),('REF-819',180,110,110),('2022-11-30',340,110,150)]))
 assert r.fields['invoice_number'].value=='REF-819'
 assert r.fields['issue_date'].value=='2022-11-30'
def test_two_tier_table_retains_lower_identity_and_upper_numeric_columns():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Quantity',450,100,100),('Unit Price',650,100,120),('Amount',850,100,100),('HS Code',20,155,120),('Description',210,155,140),('7001.99',20,220,100),('Connector',210,220,140),('12',450,220,35),('8.50',650,220,60),('102.00',850,220,80)]))
 assert len(r.items)==1
 assert r.items[0]['description'].value=='Connector'
 assert r.items[0]['quantity'].value=='12'
 assert r.items[0]['amount'].value=='102.00'

def test_incoterm_qualified_total_requires_explicit_amount_separator():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),
  ('TOTAL AMOUNT FOB ROTTERDAM PORT : 834.25',20,700,550)]))
 assert r.fields['total_amount'].value=='834.25'
 assert r.fields['total_amount'].evidence[0].selected_text=='834.25'
 assert semantic_label('The total amount FOB Rotterdam shall be settled later') is None
 assert semantic_label('TOTAL AMOUNT FOR SERVICES: 834.25') is None

def test_separate_container_table_does_not_create_invoice_goods_rows():
 d=doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,160),
  ('Quantity',250,100,110),('Amount',650,100,110),('Couplers',20,160,150),
  ('8',250,160,30),('96.00',650,160,80),('Total: 96.00',20,220,220),
  ('Container No.',20,500,150),('Seal No.',250,500,110),('Packages',450,500,110),
  ('Net Weight',650,500,150),('Gross Weight',850,500,150),
  ('ABCU7654321',20,550,150),('X90218',250,550,110),('3',450,550,30),
  ('50 KG',650,550,80),('60 KG',850,550,80)])
 r=run(d)
 assert len(r.items)==1
 assert r.items[0]['description'].value=='Couplers'
 table=r.mapping_metadata['auxiliary_tables'][0]
 assert 'auxiliary_container_table_requires_review' in r.issues
 assert table['status']=='review'
 assert any(s['token_id']=='13' for s in table['region_ocr_evidence'])
 assert r.ocr==d

def test_amount_in_words_does_not_take_adjacent_account_number():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Total Amount: 834.25',20,100,320),
  ('Amount in Words:',20,700,200),('AC NO: 009827561',650,700,260),
  ('EIGHT HUNDRED THIRTY FOUR AND 25 CENTS',20,735,560)]),labels=[
   {'token_id':'2','quote':'Amount in Words','field':'total_amount','scope':'header'}])
 assert r.fields['total_amount'].value=='834.25'

def test_per_package_weight_preserves_evidence_without_claiming_row_total():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,160),
  ('Packages',250,100,110),('Net WT. / BAG',550,100,190),
  ('Powder',20,170,110),('12 BAGS',250,170,100),('18.50 KG',550,170,120)]),labels=[
   {'token_id':'3','quote':'Net WT. / BAG','field':'net_weight','scope':'item'}])
 v=r.items[0]['net_weight']
 assert v.value is None and v.status=='review'
 assert 'per_package_measure_is_not_row_total' in v.issues
 assert v.raw_text=='18.50'
 assert v.evidence and v.label_evidence

def test_split_weight_basis_label_is_preserved_as_review_evidence():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,160),
  ('Packages',250,100,110),('Net WT. /',550,100,190),('CARTON',570,126,110),
  ('Powder',20,180,110),('12 CTN',250,180,100),('18.50 KG',550,180,120)]),labels=[
   {'token_id':'3','quote':'Net WT. /','field':'net_weight','scope':'item'}])
 v=r.items[0]['net_weight']
 assert v.value is None and v.status=='review'
 assert any(e.selected_text=='CARTON' for e in v.label_evidence)

def test_footer_freight_is_not_merged_into_last_goods_amount():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,180),
  ('Quantity',350,100,110),('Amount',800,100,130),('Coupler',20,170,150),
  ('4',350,170,40),('48.00',800,170,80),('Freight :',600,215,150),('9.50',800,215,80),
  ('Total: 57.50',600,260,280)]))
 assert len(r.items)==1
 assert r.items[0]['amount'].value=='48.00'
 assert r.fields['total_amount'].value=='57.50'
 # A freight service written in the goods column remains a valid goods row.
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Description',20,100,180),
  ('Quantity',350,100,110),('Amount',800,100,130),('Freight :',20,170,150),
  ('1',350,170,40),('9.50',800,170,80)]))
 assert r.items[0]['amount'].value=='9.50'

def test_split_row_ordinal_does_not_become_shipping_marks():
 lines=[('COMMERCIAL INVOICE',20,20,300),('Sr.',20,100,40),('No.',20,125,40),
  ('Description',180,100,160),('Quantity',450,100,120),('Amount',750,100,110),
  ('7',20,185,30),('Elbow',180,185,120),('8',450,185,30),('64.00',750,185,90)]
 r=run(doc(lines),labels=[{'token_id':'1','quote':'Sr.','field':'marks','scope':'item'}])
 assert len(r.items)==1
 assert r.items[0]['marks'].value is None
 assert r.items[0]['quantity'].value=='8'
 # Numeric shipping marks are legitimate when their actual caption says so.
 lines[1]=('Shipping Marks',20,100,150);lines.pop(2)
 r=run(doc(lines))
 assert r.items[0]['marks'].value=='7'

def test_registration_and_customs_references_cannot_conflate_trade_identifiers():
 lines=[('COMMERCIAL INVOICE',20,20,300),('GSTIN: ZX9981',20,100,240),
  ('IEC NO.: AC662',20,145,240),('S/B NO.: 84392',20,190,240),('B/L NO.: W-817',20,240,240)]
 r=run(doc(lines),labels=[
  {'token_id':'1','quote':'GSTIN','field':'buyer_reference','scope':'header'},
  {'token_id':'2','quote':'IEC NO.','field':'letter_of_credit_number','scope':'header'},
  {'token_id':'3','quote':'S/B NO.','field':'bill_of_lading_number','scope':'header'}])
 assert r.fields['buyer_reference'].value is None
 assert r.fields['letter_of_credit_number'].value is None
 assert r.fields['bill_of_lading_number'].value=='W-817'

def test_export_authorization_caption_cannot_be_a_voyage_label():
 from fintraocr.domain import unsupported_reference_caption
 for caption in ('LICENSE EXCEPTION', 'Export licence exception'):
  for scale in (.6, 1, 1.8):
   r=run(doc([('BILL OF LADING',20,20,300),(caption+': TMP',20,100,350),
    ('Voyage: R-527',500,180,250)],scale),dtype='bill_of_lading',labels=[
     {'token_id':'1','quote':caption,'field':'voyage','scope':'header'}])
   assert r.fields['voyage'].value=='R-527'
   assert r.fields['voyage'].evidence[0].selected_text=='R-527'
 assert not unsupported_reference_caption('License exception documentation enclosed with goods')

def test_observed_money_and_freight_option_cannot_be_named_places():
 for caption,field,value,issue in [('Place of issue','issue_place','$827.40','monetary_amount_is_not_named_location'),
   ('Freight payable at','freight_payable_at','COLLECT','freight_payment_option_is_not_named_location')]:
  r=run(doc([('BILL OF LADING',20,20,300),(caption+': '+value,20,140,400)]),dtype='bill_of_lading')
  v=r.fields[field]
  assert v.value is None and v.status=='review'
  assert v.raw_text==value and issue in v.issues and v.evidence and v.label_evidence
 r=run(doc([('BILL OF LADING',20,20,300),('Freight payable at: New York',20,140,450)]),dtype='bill_of_lading')
 assert r.fields['freight_payable_at'].value=='New York'

def test_compound_issuance_with_inline_place_and_separate_date():
 for scale in (.6,1,1.8):
  lines=[('BILL OF LADING',20,20,300),('Place and date of Issue: Bergen Norway',450,180,480),
   ('18 SEP 2024',970,180,170),('Date: 2023-06-25',20,240,250)]
  r=run(doc(lines,scale),dtype='bill_of_lading',labels=[
   {'token_id':'3','quote':'Date','field':'issue_date','scope':'header'}])
  assert r.fields['issue_place'].value=='Bergen Norway'
  assert r.fields['issue_date'].value=='2024-09-18'
  assert r.fields['issue_date'].evidence[0].token_id=='2'
  assert r.mapping_metadata['unqualified_date_candidates'][0]['spans'][0]['token_id']=='3'
  lines[3]=('Issue date: 2023-06-25',20,240,300)
  r=run(doc(lines,scale),dtype='bill_of_lading')
  assert r.fields['issue_date'].value is None and r.fields['issue_date'].status=='review'

def test_negotiability_notice_does_not_compete_with_consignee_identity():
 for scale in (.6,1,1.8):
  lines=[('BILL OF LADING',20,20,300),('Northern Maritime',700,100,280),
   ("NOT NEGOTIABLE UNLESS CONSIGNED 'TO ORDER'",680,155,500),
   ("Consignee(if 'To Order' so indicate)",20,180,400),('Harbor Parts Ltd.',20,215,280),
   ('Country of Origin',680,190,230),('Finland',680,230,100)]
  r=run(doc(lines,scale),dtype='bill_of_lading',labels=[
   {'token_id':'1','quote':'Northern Maritime','field':'consignee','scope':'header'}])
  assert r.fields['consignee'].value=='Harbor Parts Ltd.'
  assert all('NOT NEGOTIABLE' not in e.selected_text for e in r.fields['consignee'].evidence)

def test_reference_row_date_and_explicit_shipment_incoterm():
 from fintraocr.normalize import normalize
 assert normalize('21st May 2024','date')[0]=='2024-05-21'
 assert normalize('12nd May 2024','date')[0] is None
 lines=[('COMMERCIAL INVOICE',20,20,300),('Invoice No.: Z-903',20,100,250),
  ('DT.: 21ST MAY 2024',650,100,230),('Contract No.: A-24',20,150,250),
  ('DT.: 22ND MAY 2024',650,150,230),('Shipment Terms: FCA Oslo',20,230,400)]
 r=run(doc(lines))
 assert r.fields['issue_date'].value=='2024-05-21'
 assert r.fields['incoterms'].value=='FCA Oslo'
 assert semantic_label('Shipment Terms: Prompt dispatch') is None

def test_footer_charge_is_not_reintroduced_as_an_aggregate_goods_row():
 lines=[('COMMERCIAL INVOICE',20,20,300),('Description',20,100,180),
  ('Quantity',350,100,110),('Unit Price',600,100,130),('Amount',800,100,130),
  ('Coupler',20,170,150),('4',350,170,40),('12.00',600,170,80),('48.00',800,170,80),
  ('Freight :',600,215,120),('9.50',800,215,80),('Total: 57.50',600,260,280)]
 r=run(doc(lines))
 assert len(r.items)==1
 assert r.items[0]['amount'].value=='48.00'
 assert r.fields['total_amount'].value=='57.50'

def test_inline_vessel_and_voyage_keep_separate_character_evidence():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Vessel: Northern Beacon, Voyage Q-408',30,150,640)]))
 assert r.fields['vessel'].value=='Northern Beacon'
 assert r.fields['voyage'].value=='Q-408'
 a=r.fields['vessel'].evidence[0];b=r.fields['voyage'].evidence[0]
 assert a.token_id==b.token_id and a.end<=b.start
 assert r.fields['voyage'].label_evidence[0].selected_text.strip()=='Voyage'

def test_freight_literal_is_separate_from_option_list_or_narrative():
 r=run(doc([('BILL OF LADING',20,20,300),('FREIGHT COLLECT',20,150,280)]),dtype='bill_of_lading')
 assert r.fields['freight_terms'].value=='COLLECT'
 assert r.fields['freight_terms'].evidence[0].selected_text=='COLLECT'
 assert r.fields['freight_terms'].label_evidence[0].selected_text.strip()=='FREIGHT'
 assert semantic_label('Freight prepaid or collect') is None
 assert semantic_label('Freight prepaid unless otherwise agreed') is None

def test_quoted_freight_literal_retains_exact_value_and_rejects_untyped_competitor():
 for scale in (.6,1,1.8):
  lines=[('BILL OF LADING',20,20,300),('Freight details: FCA',20,150,300),
   ('"FREIGHT COLLECT"',400,150,280)]
  r=run(doc(lines,scale),dtype='bill_of_lading',labels=[
   {'token_id':'1','quote':'Freight details','field':'freight_terms','scope':'header'}])
  assert r.fields['freight_terms'].value=='COLLECT'
  assert r.fields['freight_terms'].evidence[0].selected_text=='COLLECT'
  assert r.mapping_metadata['rejected_freight_candidates']
  lines[1]=('FREIGHT PREPAID',20,150,280)
  r=run(doc(lines,scale),dtype='bill_of_lading')
  assert r.fields['freight_terms'].value is None and r.fields['freight_terms'].status=='review'
  lines.append(('FREIGHT COLLECT',400,250,280))
  r=run(doc(lines,scale),dtype='bill_of_lading')
  assert r.fields['freight_terms'].value is None and r.fields['freight_terms'].status=='review'
 assert semantic_label('"FREIGHT PREPAID OR COLLECT"') is None

def test_shipper_reference_cannot_be_relabelled_as_buyer_reference():
 r=run(doc([('BILL OF LADING',20,20,300),("Shipper's Ref",20,150,200),
  ('Q-8371',20,180,100),("Buyer's Ref",500,150,200),('B-7164',500,180,100)]),
  dtype='bill_of_lading',labels=[{'token_id':'1','quote':"Shipper's Ref",'field':'buyer_reference','scope':'header'}])
 assert r.fields['document_reference'].value=='Q-8371'
 assert r.fields['buyer_reference'].value=='B-7164'

def test_candidate_validity_does_not_depend_on_an_accidental_competitor():
 for scale in (.6,1,1.8):
  r=run(doc([('BILL OF LADING',20,20,300),('Delivery',20,150,150),
   ('Temperature control instructions',20,195,350),('Freight payable at: FCA',500,300,350)],scale),
   dtype='bill_of_lading',labels=[{'token_id':'1','quote':'Delivery','field':'mode_of_transport','scope':'header'}])
  assert r.fields['mode_of_transport'].value is None
  assert 'delivery_caption_does_not_establish_transport_mode' in r.fields['mode_of_transport'].issues
  assert r.fields['freight_payable_at'].value is None
  assert 'trade_term_is_not_named_location' in r.fields['freight_payable_at'].issues
  d=doc([('BILL OF LADING',20,20,300),('Unclear OCR caption',20,150,260),('Harbor Supply Ltd.',20,190,260)],scale)
  d.tokens[1].confidence=.72
  r=run(d,dtype='bill_of_lading',labels=[{'token_id':'1','quote':'Unclear OCR caption','field':'buyer_reference','scope':'header'}])
  assert r.fields['buyer_reference'].value is None and r.fields['buyer_reference'].status=='review'
  assert r.fields['buyer_reference'].raw_text=='Harbor Supply Ltd.'
  assert 'uncertain_ocr_label_role' in r.fields['buyer_reference'].issues

def test_hs_identifier_rejects_prose_but_preserves_leading_zeros():
 lines=[('COMMERCIAL INVOICE',20,20,300),('Description',20,100,180),('HS Code',350,100,120),
  ('Quantity',650,100,110),('Valve',20,180,110),('Declaration',350,180,170),('3',650,180,30)]
 r=run(doc(lines))
 v=r.items[0]['hs_code']
 assert v.value is None and v.status=='review' and v.raw_text=='Declaration'
 assert 'invalid_hs_code_characters' in v.issues
 lines[5]=('0101.21-0000',350,180,170)
 assert run(doc(lines)).items[0]['hs_code'].value=='0101.21-0000'


def test_spelled_copy_count_cannot_shift_goods_columns_or_replace_bl_identifier():
 for scale in (.6,1,1.8):
  for word in ['-SIX-','THREE (3)','NINETY']:
   lines=[('BILL OF LADING',20,20,300),('B/L No.: REF-729',20,70,300),
    ('Number of Bills of Lading',780,100,220),(word,800,135,120),
    ('Marks & Numbers',20,160,200),('Description of Goods',300,160,240),
    ('Quantity',600,160,130),('Gross Weight',800,160,170),
    ('M-482',20,220,100),('Couplers',300,220,180),('7 pcs',600,220,100),('31 KG',800,220,110)]
   r=run(doc(lines,scale),dtype='bill_of_lading',labels=[
    {'token_id':'2','quote':lines[2][0],'field':'bill_of_lading_number','scope':'header'},
    {'token_id':'3','quote':word,'field':'marks','scope':'item'}])
   assert r.fields['bill_of_lading_number'].value=='REF-729'
   assert len(r.items)==1
   assert r.items[0]['description'].value=='Couplers'
   assert r.items[0]['marks'].value=='M-482'
   assert {e.token_id for e in r.items[0]['marks'].label_evidence}=={'4'}


def test_combined_vessel_heading_with_inline_voyage_resolves_continuation_as_value():
 for scale in (.6,1,1.8):
  lines=[('BILL OF LADING',20,20,300),('Vessel / Voy. No V.731',20,150,330),
   ('Northern Beacon',20,190,260),('Port of Discharge',450,150,230),('OSLO, NORWAY',450,190,200)]
  r=run(doc(lines,scale),dtype='bill_of_lading',labels=[
   {'token_id':'2','quote':'Northern Beacon','field':'vessel','scope':'header'}])
  assert r.fields['vessel'].value=='Northern Beacon'
  assert r.fields['voyage'].value=='V.731'
  assert r.fields['vessel'].evidence[0].token_id=='2'
  assert r.fields['voyage'].evidence[0].token_id=='1'
  assert r.fields['voyage'].evidence[0].start>=r.fields['voyage'].label_evidence[0].end


def test_spaced_grouped_amount_retains_exact_ocr_span_and_header_currency():
 from fintraocr.layout import value_spans
 from fintraocr.normalize import normalize
 for scale in (.6,1,1.8):
  lines=[('COMMERCIAL INVOICE',20,20,300),('Description',20,150,220),
   ('Quantity',350,150,140),('Amount (US $)',700,150,230),
   ('Fasteners',20,220,180),('3',350,220,40),('4 250,50',700,220,180)]
  r=run(doc(lines,scale))
  assert r.items[0]['amount'].value=='4250.50'
  assert r.items[0]['amount'].evidence[0].selected_text=='4 250,50'
  assert r.fields['currency'].value=='USD'
  assert r.fields['currency'].evidence[0].selected_text=='US $'
  token=doc([('12 34',20,100,200)]).tokens[0]
  assert value_spans(token,'number','amount')==[]
 assert normalize('$','currency')[0] is None


def test_bare_date_caption_cannot_become_missing_invoice_identifier():
 r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Invoice No:',20,150,220),('Date:',650,150,140)]))
 assert r.fields['invoice_number'].value is None


def test_country_formal_order_is_derived_from_registry_without_fuzzy_repair():
 from fintraocr.normalize import normalize
 assert normalize('Republic of Korea','country')[0]=='KR'
 assert normalize('Republic of Moldova','country')[0]=='MD'
 assert normalize('Republic of Kcrea','country')[0] is None


def test_empty_reference_caption_block_is_not_a_goods_description():
 from fintraocr.layout import LayoutResolver,span
 from fintraocr.schemas import ITEM_SCHEMAS
 d=doc([('Goods Description',20,100,250),('Agreement No.:',20,160,180),('Project Name:',20,185,180)])
 resolver=LayoutResolver(d)
 result=resolver.select(d.tokens[1:],ITEM_SCHEMAS['commercial_invoice']['description'],'description',[span(d.tokens[0])],'table')
 assert 'document_metadata_is_not_goods_description' in result.reasons
 assert len(result.spans)==2
 d.tokens[2].text='Projector mounting assembly'
 result=resolver.select(d.tokens[1:],ITEM_SCHEMAS['commercial_invoice']['description'],'description',[span(d.tokens[0])],'table')
 assert not result.reasons



def test_remittance_payment_and_currency_component():
 for scale in (.6,1,1.8):
  for code in ('USD','EUR','JPY'):
   lines=[('COMMERCIAL INVOICE',20,20,300),('Payment terms: T/T',500,110,260),('Description',20,300,180),('Amount',750,300,150),('Fasteners',20,350,170),('72.45',750,350,100),('17% advance '+code+' (with order)',260,700,380),('83% balance '+code+' (after delivery)',260,740,430),('REMIT',90,770,100),('PAYMENT TO:',70,795,170)]
   r=run(doc(lines,scale))
   assert r.fields['payment_terms'].value=='T/T '+lines[6][0]+' '+lines[7][0]
   assert r.fields['currency'].value==code
   assert r.fields['currency'].reference_evidence==r.fields['payment_terms'].evidence
   assert len(r.items)==1
   without_caption=run(doc(lines[:8],scale))
   assert without_caption.fields['payment_terms'].value=='T/T'
   assert without_caption.fields['currency'].value is None

def test_mixed_payment_currency_keeps_terms_but_requires_currency_review():
 lines=[('COMMERCIAL INVOICE',20,20,300),('Payment terms: T/T',500,110,260),('23% deposit USD (with order)',260,700,380),('77% balance EUR (after delivery)',260,740,430),('Remittance',70,770,160)]
 r=run(doc(lines))
 assert r.fields['payment_terms'].status=='accepted'
 assert r.fields['currency'].status=='review'
 assert 'conflicting_payment_currencies' in r.fields['currency'].issues

def test_parenthesized_carrier_role_is_not_signing_agent():
 for scale in (.6,1,1.8):
  lines=[('BILL OF LADING',20,20,300),('Signed on behalf of the Carrier:',450,600,430),('Harbor Agency Ltd.',600,640,260),('As Agent For the carrier',600,670,300),('Northern Marine PLC (AS CARRIER)',520,720,440)]
  r=run(doc(lines,scale),dtype='bill_of_lading',labels=[{'token_id':'1','quote':lines[1][0][:-1],'field':'carrier','scope':'header'}])
  assert r.fields['carrier'].value=='Northern Marine PLC'
  assert r.fields['carrier'].evidence[0].end<=r.fields['carrier'].label_evidence[0].start
  lines.append(('Southern Shipping Inc. (AS CARRIER)',520,800,450))
  conflict=run(doc(lines,scale),dtype='bill_of_lading')
  assert conflict.fields['carrier'].status=='review'
  assert 'competing_explicit_carrier_names' in conflict.fields['carrier'].issues



def test_settlement_amounts_do_not_become_goods_rows():
 for scale in (.6,1,1.8):
  lines=[('COMMERCIAL INVOICE',20,20,300),('Description',20,250,180),('Quantity',400,250,140),('Unit Price',650,250,140),('Amount',850,250,140),('Contract No.:',20,300,180),('120.50',650,410,100),('120.50',850,410,100),('230.75',650,470,100),('230.75',850,470,100),('100 PCT OF TOTAL AMOUNT',20,580,400),('351.25',850,580,100),('(17 PCT PAID BY ADVANCE PAYMENT)',20,620,540),('59.71',850,620,100),('(83 PCT TO BE PAID BY T/T)',20,660,540),('291.54',850,660,100)]
  r=run(doc(lines,scale))
  assert len(r.items)==2
  assert [row['amount'].value for row in r.items]==['120.50','230.75']
  assert all(row['description'].value is None for row in r.items)
  assert any(x['kind']=='payment_settlement_section' for x in r.mapping_metadata['table_diagnostics'])
  # A product name mentioning payment remains a goods row without the
  # corroborating percentage-summary and multi-clause settlement structure.
  simple=[('COMMERCIAL INVOICE',20,20,300),('Description',20,250,180),('Amount',850,250,140),('Payment terminal',20,310,230),('351.25',850,310,100)]
  r=run(doc(simple,scale))
  assert r.items[0]['description'].value=='Payment terminal'


def test_unreadable_month_keeps_raw_date_candidate_without_repair():
 for scale in (.6,1,1.8):
  r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Date of Issue',500,150,200),('21-0ct-2024',740,150,170)],scale))
  field=r.fields['issue_date']
  assert field.value is None and field.status=='review'
  assert field.raw_text=='21-0ct-2024'
  assert field.evidence[0].selected_text=='21-0ct-2024'
  assert field.label_evidence[0].selected_text=='Date of Issue'


from tests.test_acceptance_regressions import doc,run

def test_account_details_cannot_establish_seller_identity():
    for scale in (.6,1,1.8):
        lines=[('COMMERCIAL INVOICE',20,20,300),('Seller Oak Manufacturing Ltd.',450,120,420),("Seller's account information (only for EUR)",50,700,580),('Director',180,760,160)]
        r=run(doc(lines,scale),labels=[{'token_id':'1','quote':'Seller','field':'seller','scope':'header'},{'token_id':'2','quote':lines[2][0],'field':'seller','scope':'header'}])
        assert r.fields['seller'].value=='Oak Manufacturing Ltd.'
        assert r.fields['seller'].evidence
        rejected=[t for t in r.mapping_metadata['trace'] if t['stage']=='validated_labels'][0]['rejected']
        assert any(x['reason']=='party_account_details_are_not_party_identity' for x in rejected)

def test_company_name_containing_account_is_not_filtered():
    r=run(doc([('COMMERCIAL INVOICE',20,20,300),('Seller: Account Services Ltd.',450,120,420)]))
    assert r.fields['seller'].value=='Account Services Ltd.'

from tests.test_structural import doc,run
from fintraocr.grounded import GroundedSelector
from fintraocr.mapping import MappingEngine
from fintraocr.models import Selection,Span

def test_goods_carrier_word_does_not_conflict_with_named_carrier():
    for scale in (.6,1,1.8):
        lines=[('PACKING LIST',20,20,300),('Carrier',20,110,150),('Northern Freight Ltd.',20,150,320),('Description',20,300,200),('Quantity',500,300,150),('Gross Weight',760,300,190),('Carrier support bracket',20,370,340),('7 pcs',500,370,150),('18 KG',760,370,140)]
        d=doc(lines,scale)
        selector=GroundedSelector('mock')
        selector.label_request=lambda d:{'document_type':'packing_list','title_ids':['0'],'labels':[{'token_id':'6','quote':'Carrier','field':'carrier','scope':'header'}]}
        selector.inline_fields={'carrier':[Selection(spans=[Span(token_id='6',start=8,end=len(lines[6][0]))],label_spans=[Span(token_id='6',start=0,end=7)],score=1,method='semantic_inline')]}
        r=MappingEngine(selector).map(d)
        assert r.fields['carrier'].value=='Northern Freight Ltd.'
        assert r.items[0]['description'].value=='Carrier support bracket'
        assert any(x['reason']=='goods_cell_is_not_document_party_label' for x in r.mapping_metadata['rejected_inline_selections'])

def test_competing_document_carriers_still_require_review():
    r=run(doc([('PACKING LIST',20,20,300),('Carrier: Northern Freight Ltd.',20,110,440),('Carrier: Southern Freight Ltd.',20,210,440)]),dtype='packing_list')
    assert r.fields['carrier'].value is None and r.fields['carrier'].status=='review'


from tests.test_structural import doc,run

def test_date_aligned_with_document_title_retains_own_issue_role():
    for scale in (.6,1,1.8):
        for title,dtype in [('PACKING LIST','packing_list'),('COMMERCIAL INVOICE','commercial_invoice'),('BILL OF LADING','bill_of_lading')]:
            r=run(doc([(title,50,30,330),('Date: 23-Jul-2022',680,35,250),('Invoice No: Q-93',400,180,300)],scale),dtype=dtype)
            assert r.fields['issue_date'].value=='2022-07-23'
            assert r.fields['issue_date'].evidence[0].selected_text=='23-Jul-2022'
            assert r.mapping_metadata['document_title_date_context'][0]['title_evidence']['token_id']=='0'

def test_date_belonging_to_reference_or_body_is_not_title_issue_date():
    r=run(doc([('PACKING LIST',50,30,300),('Invoice No: Q-93',400,35,230),('Date: 23-Jul-2022',680,35,250)]),dtype='packing_list')
    assert r.fields['issue_date'].value is None
    assert r.fields['invoice_date'].value=='2022-07-23'
    body=run(doc([('BILL OF LADING',50,30,300),('Date: 23-Jul-2022',680,800,250)]),dtype='bill_of_lading')
    assert body.fields['issue_date'].value is None

def test_ambiguous_title_date_is_not_guessed():
    r=run(doc([('PACKING LIST',50,30,300),('Date: 03-07-2022',680,35,250)]),dtype='packing_list')
    assert r.fields['issue_date'].value is None
    assert r.fields['issue_date'].status=='review'
    assert r.fields['issue_date'].raw_text=='03-07-2022'


from tests.test_structural import doc,run

def test_numeric_total_beside_words_uses_only_numeric_evidence():
    for scale in (.5,1,2):
        r=run(doc([('COMMERCIAL INVOICE',40,20,300),('Total: Eight thousand Euros.',40,300,450),('8 000,00',600,300,150)],scale))
        f=r.fields['total_amount']
        assert f.value=='8000.00'
        assert f.evidence[0].selected_text=='8 000,00'
        assert f.label_evidence[0].selected_text=='Total'

def test_total_words_never_synthesize_amount_or_choose_multiple_numbers():
    for extra in ([],[('8 000,00',600,400,150)],[('8 000,00',600,300,100),('9 000,00',800,300,100)]):
        r=run(doc([('COMMERCIAL INVOICE',40,20,300),('Total: Eight thousand Euros.',40,300,450)]+extra))
        assert r.fields['total_amount'].value is None

def test_inline_numeric_total_remains_authoritative():
    r=run(doc([('COMMERCIAL INVOICE',40,20,300),('Total: 8000.00',40,300,450),('9000.00',600,300,150)]))
    assert r.fields['total_amount'].value=='8000.00'


from fintraocr.domain import document_heading_types
import json
from io import BytesIO
from unittest.mock import patch
from fintraocr.compact import CompactSelector
from tests.test_structural import doc

def test_full_qualified_heading_avoids_only_classification_call():
    for title,kind in [('MULTIMODAL OCEAN BILL OF LADING','bill_of_lading'),('SAMPLE COMMERCIAL INVOICE','commercial_invoice'),('COPY PACKING LIST','packing_list')]:
        selector=CompactSelector('mock')
        with patch('fintraocr.compact.urlopen',return_value=BytesIO(json.dumps({'message':{'content':'{}'}}).encode())) as call:
            result=selector.label_request(doc([(title,100,20,500)]))
        assert call.call_count==1
        assert result['document_type']==kind and result['title_ids']==['0']
        assert [t['stage'] for t in selector.metadata['trace']]==['label_selection']

def test_narrative_and_reference_mentions_are_not_titles():
    for text in ['Copy of bill of lading required','Refer to commercial invoice','Bill of Lading No: X-17','Original invoice to be supplied','Non-negotiable unless consigned to order']:
        assert document_heading_types(text)==set()

def test_conflicting_document_titles_still_request_classification():
    responses=[BytesIO(json.dumps({'message':{'content':'{"type":"unknown","title":"0"}'}}).encode())]
    selector=CompactSelector('mock')
    with patch('fintraocr.compact.urlopen',side_effect=responses):
        result=selector.label_request(doc([('COMMERCIAL INVOICE',100,20,400),('PACKING LIST',100,80,400)]))
    assert result['document_type']=='unknown'
    assert selector.metadata['trace'][0]['stage']=='document_classification'


import json
from io import BytesIO
from unittest.mock import patch
from fintraocr.compact import CompactSelector
from fintraocr.mapping import MappingEngine
from tests.test_structural import doc

def test_unknown_caption_in_table_band_is_available_to_model_not_auto_assigned():
    for scale in (.6,1,2):
        d=doc([('BILL OF LADING',50,20,400),('Place of Delivery',400,100,400),('Packages',50,150,110),('Merchandise particulars',420,150,270),('Gross Weight',800,150,150),('9 PKG',50,220,100),('Pump assembly',420,220,180),('71 KG',800,220,100)],scale)
        selector=CompactSelector('mock')
        with patch('fintraocr.compact.urlopen',return_value=BytesIO(json.dumps({'message':{'content':'{}'}}).encode())):
            result=MappingEngine(selector).map(d)
        assert '3' in selector.metadata['label_candidate_ids']
        assert all(row['description'].value is None for row in result.items)

def test_scalar_or_party_values_do_not_become_caption_candidates_from_alignment():
    for text in ['72.50','Orbit Ltd.']:
        d=doc([('BILL OF LADING',50,20,400),('Place of Delivery',400,100,400),('Packages',50,150,110),(text,420,150,270),('Gross Weight',800,150,150)])
        selector=CompactSelector('mock')
        with patch('fintraocr.compact.urlopen',return_value=BytesIO(json.dumps({'message':{'content':'{}'}}).encode())):
            selector.label_request(d)
        assert '3' not in selector.metadata['label_candidate_ids']


from tests.test_structural import doc,run

def test_unknown_model_selected_caption_uses_table_context_not_parent_value_region():
    for scale in (.6,1,2):
        d=doc([('BILL OF LADING',50,20,400),('Place of Delivery',400,100,400),('Packages',50,150,110),('Merchandise particulars',420,150,270),('Gross Weight',800,150,150),('9 PKG',50,220,100),('Pump assembly',420,220,180),('71 KG',800,220,100)],scale)
        r=run(d,[{'token_id':'3','quote':'Merchandise particulars','field':'description','scope':'item'}],dtype='bill_of_lading')
        assert r.items[0]['description'].value=='Pump assembly'
        assert r.items[0]['description'].label_evidence[0].selected_text=='Merchandise particulars'
        assert r.mapping_metadata['model_column_header_context']

def test_goods_value_mislabelled_as_heading_remains_excluded():
    d=doc([('BILL OF LADING',50,20,400),('Packages',50,150,110),('Goods',420,150,270),('Gross Weight',800,150,150),('9 PKG',50,220,100),('Pump assembly',420,220,180),('71 KG',800,220,100)])
    r=run(d,[{'token_id':'5','quote':'Pump assembly','field':'description','scope':'item'}],dtype='bill_of_lading')
    assert r.items[0]['description'].value=='Pump assembly'
    assert r.items[0]['description'].label_evidence[0].selected_text=='Goods'


from tests.test_structural import doc,run

def test_explicit_carrier_value_and_signing_agent_do_not_create_other_party_roles():
    for scale in (.6,1,2):
        d=doc([('BILL OF LADING',50,20,400),('Forwarding Agent',50,100,250),('Transit Ltd.',50,140,250),('Signed on behalf of the Carrier:',500,500,400),('Signature Services Ltd.',500,540,300),('As Agent For the carrier',500,580,300),('Oceanic',500,620,150),('Oceanic Ltd. (AS CARRIER)',500,660,400),('Special handling instructions',500,710,400)],scale)
        labels=[{'token_id':str(i),'quote':d.tokens[i].text,'field':field,'scope':'header'} for i,field in [(5,'forwarding_agent'),(6,'carrier'),(7,'carrier')]]
        r=run(d,labels,dtype='bill_of_lading')
        assert r.fields['carrier'].value=='Oceanic Ltd.'
        assert r.fields['forwarding_agent'].value=='Transit Ltd.'

def test_two_explicit_carriers_still_conflict():
    r=run(doc([('BILL OF LADING',50,20,400),('Oceanic Ltd. (AS CARRIER)',500,500,400),('Marine Ltd. (AS CARRIER)',500,600,400)]),dtype='bill_of_lading')
    assert r.fields['carrier'].value is None
    assert r.fields['carrier'].status=='review'


from tests.test_structural import doc,run

def semantic_guard_label(d,index,field,scope='header'):
    return dict(token_id=str(index),quote=d.tokens[index].text.split(':')[0],field=field,scope=scope)

def test_dangerous_goods_reference_cannot_compete_with_issue_place():
    for scale in (.6,1,2):
        d=doc([('BILL OF LADING',50,20,400),('UN-NO: 1203',50,300,200),('Place of Issue',500,300,200),('Oslo, Norway',500,340,200)],scale)
        r=run(d,[semantic_guard_label(d,1,'issue_place')],dtype='bill_of_lading')
        assert r.fields['issue_place'].value=='Oslo, Norway'

def test_form_instruction_does_not_label_routing():
    d=doc([('BILL OF LADING',50,20,400),('Mark with X to designate hazardous material as',50,300,600),('Defined in transport regulations',50,340,500)])
    r=run(d,[semantic_guard_label(d,1,'routing_instructions')],dtype='bill_of_lading')
    assert r.fields['routing_instructions'].value is None

def test_trade_term_is_not_transport_mode_even_with_explicit_mode_caption():
    d=doc([('BILL OF LADING',50,20,400),('Mode of Transport',50,300,250),('FOB',50,340,150)])
    r=run(d,dtype='bill_of_lading')
    assert r.fields['mode_of_transport'].value is None
    assert r.fields['mode_of_transport'].raw_text=='FOB'
    assert r.fields['mode_of_transport'].status=='review'

def test_generic_class_cannot_become_customs_code_but_hs_heading_can():
    for heading,expected in [('CLASS',None),('HS Code','8504.40')]:
        d=doc([('COMMERCIAL INVOICE',50,20,400),('Description',50,300,220),(heading,400,300,150),('Quantity',700,300,150),('Transformer',50,350,220),('8504.40',400,350,150),('2',700,350,150)])
        r=run(d,[semantic_guard_label(d,2,'hs_code','item')])
        assert r.items[0]['hs_code'].value==expected
