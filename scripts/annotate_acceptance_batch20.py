"""Manual source review of unused batch20. Never reads engine predictions.

Incomplete until every selected document has been transcribed and reviewed.
Do not score an incomplete batch as an acceptance pass.
"""
import hashlib,json
from scripts.azure_acceptance import ROOT
from fintraocr.schemas import catalog,ALIASES

REVIEWED={
 'IMG_OCR_6_T_PL_006895':{
  'fields':{'issue_date':'2004-07-01','invoice_number':'137434','seller':'Ecuity Surgical Co., Ltd.',
   'letter_of_credit_number':'M0502612NS95244','purchase_order_number':'918-913-6622',
   'consignee':'G&D Diamond Co., Ltd.','country_of_origin':'TR','notify_party':'Takamuraen Co., Ltd.',
   'port_of_loading':'KATUNAN, JAPAN','port_of_discharge':'SUNOE, JAPAN','vessel':'NEGAR','voyage':'V.958',
   'departure_date':'2001-09-30','total_packages':'65','gross_weight':'851','gross_weight_unit':'kg','weight_unit':'kg','volume':'995.62','volume_unit':'m3'},
  'items':[
   {'description':"LASER CAVITY ASS'Y",'quantity':'89','unit':'BAG','net_weight':'898','gross_weight':'101','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'547.01','volume_unit':'m3'},
   {'description':'GASKET KIT-ENGINE OVERHAUL UPR','quantity':'14','unit':'CT','net_weight':'829','gross_weight':'452','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'810.83','volume_unit':'m3'},
   {'description':'Turret Turning Device Electric Clutch For High And Low','quantity':'58','unit':'BOX','net_weight':'744','gross_weight':'908','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'574.07','volume_unit':'m3'}],
  'notes':['Source image and all Azure word annotations reviewed before opening this document mapping.',
   'Shipping Mark references Support and Clamp, which cannot be assigned to the three different listed goods by evidence alone.',
   'DPU is explicit but is outside the frozen packing-list fields; retain as a schema coverage limitation.',
   'Unregistered unit spellings BAG, CT and BOX retain their source form under the frozen contract.',
   'Signed-by company Aki Business Hotel is not seller or shipper.']},
 'IMG_OCR_6_T_BL_003726':{
  'fields':{'shipment_date':'2013-09-21','shipper':'RKB FACILITY SOLUTIONS','exporter':'RKB FACILITY SOLUTIONS',
   'booking_number':'26199','document_reference':'944-193-1790','quotation_number':'45-83-79429',
   'forwarding_agent_number':'20-52-17-3010','shipping_origin':'NORWAY','consignee':'ILIGHT ANALYTICS',
   'delivery_party':'CIA CONSULTING','notify_party':'REOPLE, PETS AND VETS','bill_to_party':'GIRAST TRADING CO. LTD.',
   'vessel':'FANGZHOU 21','port_of_loading':'KIBE, JAPAN','port_of_discharge':'LIUZHOU, CHINA',
   'freight_terms':'PREPAID','gross_weight':'70','gross_weight_unit':'kg','weight_unit':'kg',
   'volume':'705.17','volume_unit':'m3','issue_place':'WALTON, CANADA','issue_date':'2000-02-24'},
  'items':[
   {'container_number':'DLSU0487807','marks':'Q730558','package_count':'56','package_type':'PKG',
    'description':'COVER, FOR BEARING, CLEANING PUMP SIDE','gross_weight':'18','weight_unit':'kg','gross_weight_unit':'kg','volume':'503.98','volume_unit':'m3'},
   {'package_count':'26','package_type':'PKG','description':'FIXING BRACKET, FOR SWITCH',
    'gross_weight':'31','weight_unit':'kg','gross_weight_unit':'kg','volume':'448.44','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and source word annotations reviewed before opening model predictions.',
   'BILL OF LADING NO / PO NO is a combined alternative caption over one identifier HG883718. Its unique semantic role requires adjudication; do not assign the same identifier to both roles.',
   'Both declared-value lines are explicitly per-package and contain different amounts; scalar declared_value remains ambiguous.',
   'CFS/CFS and CY/CY are service movement values, not receipt/delivery locations.',
   'Q730558 is unqualified within Marks & No./Container No.; no explicit seal label establishes seal_number.',
   'Prepaid is independently established by a populated Prepaid money column; the checkmark is not needed.',
   'Container identity is printed only beside the first cargo row. No carry-down to the second row is assumed.',
   'This annotation has unresolved combined-caption and marks/seal semantics and is not acceptance eligible without independent adjudication.']},
 'IMG_OCR_6_T_NV_002664':{
  'fields':{'invoice_number':'311373','bill_of_lading_number':'HG311996',
   'exporter':'Rackaging Corp. of America','consignee':'NandAmerica Financial Group','buyer':'NST Solutions',
   'document_reference':'564-062-6006','buyer_reference':'85-64-55132',
   'mode_of_transport':'DPMTH','country_of_origin':'SS','country_of_destination':'AM',
   'vessel':'EVER BLISS','voyage':'V.887','payment_terms':'DEBIT','port_of_loading':'TAKE, JAPAN',
   'departure_date':'2009-05-25','port_of_discharge':'DUFFEL, BELGIUM','place_of_delivery':'ZYYI, CYPRUS',
   'insurance_policy_number':'847-826-4001','letter_of_credit_number':'21-94-79363',
   'total_amount':'83720.57','currency':'HRK'},
  'items':[
   {'product_code':'24-177','description':'Diagnostic Kit, Cholera','hs_code':'9224.70','quantity':'83','unit':'BOX','unit_price':'83.86','amount':'941.32'},
   {'product_code':'71-881','description':'RESISTOR VARIABLE','hs_code':'5895.69','quantity':'5','unit':'Doz','unit_price':'44.85','amount':'335.23'},
   {'product_code':'16-415','description':'Encoder, Axis Angle Digital Display','hs_code':'7754.22','quantity':'47','unit':'t','unit_price':'83.11','amount':'1321.88'}],
  'notes':['Source image and Azure word annotations reviewed before opening any mapping for this document.',
   'Exporter is not automatically seller or shipper. Buyer Reference is not a purchase order.',
   'Total This Page 8 and Consignment Total 7 have no explicit package-count unit; do not assign total_packages.',
   'HRK is printed explicitly despite dollar symbols on amounts; retain the explicit currency code.',
   'BOX and Doz are preserved under the frozen unknown-unit normalization contract; M/T explicitly normalizes to metric t.',
   'No issue date is printed. Signatory company Ricsart is not a transaction party.']},
 'IMG_OCR_6_T_PL_000683':{
  'fields':{'invoice_number':'039604','seller':'Ret Assure Co., Ltd.','consignee':'Xondong Rp Co., Ltd.',
   'notify_party':'Cridgewater Homes Co., Ltd.','letter_of_credit_number':'M5717774NS41344',
   'purchase_order_number':'849-875-9752','country_of_origin':'BS','port_of_loading':'MAHDIA, TUNISIA',
   'port_of_discharge':'IURRETA, SPAIN','vessel':'ELEGANT ACE','voyage':'V.206','departure_date':'2019-06-16',
   'total_packages':'70','gross_weight':'429','gross_weight_unit':'kg','weight_unit':'kg','volume':'393.37','volume_unit':'m3'},
  'items':[
   {'description':'FLY WEIGHT HOLDER','quantity':'80','unit':'YD','net_weight':'775','gross_weight':'262','volume':'573.73','volume_unit':'m3','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'NUT-CASTLE','quantity':'45','unit':'set','net_weight':'225','gross_weight':'415','volume':'886.83','volume_unit':'m3','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'Tachometer (high/low Sensor)','quantity':'49','unit':'set','net_weight':'595','gross_weight':'402','volume':'257.64','volume_unit':'m3','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'expected_review':['fields.issue_date'],
  'notes':['Printed top Date 06-02-2007 has ambiguous month/day order; do not infer its order from a different event date.',
   'Separate Shipping Mark ranges 1–5 Sealing and 10–70 Scraper cannot be linked to these individual goods rows from the printed evidence. Document-wide marks are a frozen-schema gap.',
   'TERM CPT is printed but the frozen packing-list schema lacks incoterms; report a coverage gap, not an invented field.',
   'Header row and all source word annotations visually checked; no predicted mapping opened.']}
}

def main():
 additions=ROOT/'data/acceptance/source-transcriptions-batch20-additions.json'
 if additions.exists():
  for name,manual in json.loads(additions.read_text(encoding='utf-8')).items():
   if name in REVIEWED:raise RuntimeError('Duplicate manual source annotation')
   REVIEWED[name]=manual
 entries={e['id']:e for e in json.loads((ROOT/'data/acceptance/selection.json').read_text(encoding='utf-8'))['entries']}
 out=ROOT/'data/acceptance/gold-holdout-batch20';out.mkdir(exist_ok=True)
 for name,manual in REVIEWED.items():
  e=entries[name];schema=catalog()[e['type']];source=ROOT/'data/acceptance/documents'/name
  unknown=set(manual['fields'])-set(schema['fields'])
  unknown.update(key for row in manual['items'] for key in row if key not in schema['items'])
  if unknown:raise ValueError(f'Unscored manual fields for {name}: {sorted(unknown)}')
  fields={key:manual['fields'].get(key) for key in schema['fields']}
  for alias,target in ALIASES[e['type']].items():fields[alias]=fields[target]
  gold={'document_type':e['type'],'layout_family':e['layout_family'],'novelty':e['novelty'],'fields':fields,
    'items':[{key:row.get(key) for key in schema['items']} for row in manual['items']],
   'expected_review':manual.get('expected_review',[]),'review_notes':manual['notes'],'role':e['role'],
    'source_image_sha256':hashlib.sha256((source/'image.png').read_bytes()).hexdigest(),
    'source_annotation_sha256':hashlib.sha256((source/'annotation.json').read_bytes()).hexdigest(),
    'coverage':'all applicable frozen fields manually source reviewed; ambiguous values have separate expected review status',
    'method':'Manual source image and Azure human word-annotation transcription, without mapping outputs'}
  target=out/(name+'.json');text=json.dumps(gold,ensure_ascii=False,indent=2)
  if manual.get('unscored_source_fields'):
   gold['unscored_source_fields']=manual['unscored_source_fields']
   text=json.dumps(gold,ensure_ascii=False,indent=2)
  if target.exists() and target.read_text(encoding='utf-8')!=text:raise RuntimeError('Reviewed gold must be versioned rather than overwritten')
  target.write_text(text,encoding='utf-8')
 print('Source reviewed',len(REVIEWED),'of 60; independent adjudication and acceptance remain pending')

if __name__=='__main__':main()
