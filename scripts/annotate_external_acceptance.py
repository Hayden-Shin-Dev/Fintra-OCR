"""Manual transcription of publisher images, before external engine inference.

Evaluation fixtures only. No production module imports this file.
"""
import json,hashlib
from scripts.azure_acceptance import ROOT
from fintraocr.schemas import catalog,ALIASES

CASES={
 'kchain-packing':('packing_list','page-1.png',{
  'packing_list_number':'RT/PL/2026/1047','issue_date':'2026-04-08','exporter':'Rajesh Textiles Pvt. Ltd.',
  'consignee':'Weber & Hoffmann GmbH','letter_of_credit_number':'DHB/LC/2026/04521',
  'invoice_number':'RT/INV/2026/1047','vessel':'Maersk Eindhoven','voyage':'2601E',
  'port_of_loading':'Nhava Sheva (JNPT), Mumbai, India','port_of_discharge':'Hamburg, Germany',
  'total_packages':'50','net_weight':'6750','gross_weight':'7500','weight_unit':'kg',
  'net_weight_unit':'kg','gross_weight_unit':'kg','volume':'125','volume_unit':'m3'},
  [{'marks':mark,'description':'Organic cotton fabric, 150cm, 200 GSM, white','quantity':'10','unit':'ea',
    'net_weight':'135','gross_weight':'150','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg',
    'product_size':'120x80x60'} for mark in ['1-10','11-20','21-30','31-40','41-50']],
  ['Publisher explicitly labels this a generated demonstration document, not a real trade record.',
   'Roll count 10/ea is printed per carton, while rows describe carton ranges; do not multiply or reconcile totals.',
   'Dimensions are in cm. The frozen schema has product_size text but no dimension-unit field; report this contract limitation.',
   'Carton No. ranges are marks, not counts. Total Rolls 500 is present but the frozen schema lacks total goods quantity; report as schema coverage gap.']),
 'shipzy-invoice':('commercial_invoice','page-1.png',{
  'invoice_number':'ORG/21/2023','issue_date':'2023-08-16','bill_of_lading_number':'76987',
  'exporter':'ORG EXIM','consignee':'MANARET EL FAYROUZ','notify_party':'MANARET EL FAYROUZ',
  'mode_of_transport':'BY SEA','country_of_origin':'IN','country_of_destination':'EG',
  'port_of_loading':'MUNDRA','port_of_discharge':'ALEXANDRIA','place_of_delivery':'ALEXANDRIA',
  'incoterms':'CIF ALEXANDRIA, EGYPT','payment_terms':'20% advance rest after scanned documents',
  'currency':'USD','total_amount':'73800','net_weight':'54000','gross_weight':'54690',
  'weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},[
   {'description':'TOOR DAL BAGS MADE OF PP BAGS PREMIUM QUALITY AS PER SAMPLE','hs_code':'07139010',
    'quantity':'26.000','unit':'t','package_count':'1300','package_type':'bag','net_weight':'20.00','gross_weight':'20.10',
    'weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','unit_price':'1600.00','amount':'41600.00'},
   {'description':'RICE 40/60 BAGS MADE OF JUTE BAGS','hs_code':'10061010','quantity':'28.000','unit':'t',
    'package_count':'1120','package_type':'bag','net_weight':'25.00','gross_weight':'25.50','weight_unit':'kg',
    'net_weight_unit':'kg','gross_weight_unit':'kg','unit_price':'1150.00','amount':'32200.00'}],
  ['Separate container packing table is not additional goods rows; frozen invoice schema has no container rows. Report this gap.',
   'Net/Gross WT. / BAG is per-package weight, not row total. Frozen schema cannot expose this basis; report contract limitation.',
   'Repeated consignee/notify names occupy address lines too; do not duplicate the party name.',
   'Contract, shipping bill, tax registration, freight charge and beneficiary-bank account are explicit but outside frozen fields. No field added to inflate accuracy.']),
 'usda-handbook':('bill_of_lading','page-44.png',{
  'booking_number':'123456','shipper':'FRESH ORANGE EXPORTER','consignee':'ORIENTAL FRESH FOODS',
  'notify_party':'ORIENTAL FRESH FOODS','carrier':'GLOBETRANS, INC.','vessel':'APL JAPAN','voyage':'V.13',
  'port_of_loading':'SAN PEDRO','port_of_discharge':'HONG KONG','place_of_receipt':'SAN PEDRO',
  'place_of_delivery':'HONG KONG','freight_terms':'PREPAID','total_packages':'950','on_board_date':'1996-03-11',
  'shipping_origin':'CALIFORNIA USA','forwarding_agent':'J.E. LOWDEN & CO.'},[
   {'description':'CARTONS FRESH ORANGES 1/40 FT. CY/CY CONTAINER SHIPPERS LOAD AND COUNT (NET WEIGHT 35,150 LBS.) CARGO UNDER REFRIGERATION MAINTAIN TEMPERATURE AT 42 DEGREE F VENTS 45 CFM',
    'container_number':'APLU 596327-1','package_count':'950','package_type':'ctn','net_weight':'35150','net_weight_unit':'lb'}],
  ['Published USDA handbook example reproduced at low source resolution; distinct from AIHub templates.',
   'B/L number box contains BOOKING#:123456; do not assign it to bill_of_lading_number.',
   'Both imperial and metric gross weight/volume are printed. Frozen scalar fields require ambiguity review, not a guessed unit conversion.',
   'Issue date stamp and forwarding agent reference are not confidently readable from this render; require review rather than guessed values.',
   'APLU123456789 is labelled container number at top, different from cargo-row APLU 596327-1. Frozen schema has only item container number; retain conflict evidence for review.'])
}

def main():
 for name,(kind,image_name,fields,items,notes) in CASES.items():
  folder=ROOT/'data/acceptance/external'/name;image=folder/image_name;schema=catalog()[kind]
  all_fields={k:fields.get(k) for k in schema['fields']}
  for alias,target in ALIASES[kind].items():all_fields[alias]=all_fields[target]
  gold={'document_type':kind,'fields':all_fields,'items':[{k:row.get(k) for k in schema['items']} for row in items],
   'coverage':'all frozen applicable fields; ambiguous and unsupported basis cases explicitly documented',
   'source_image':image_name,'source_image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
   'review_notes':notes,'role':'unseen_external','gold_method':'manual source-image transcription before engine inference',
   'acceptance_eligible':False,'ineligibility':'Independent second review and ambiguous-state adjudication remain required; numeric aggregate score alone cannot certify this set.'}
  target=folder/'gold-v1.json';text=json.dumps(gold,ensure_ascii=False,indent=2)
  if target.exists() and target.read_text(encoding='utf-8')!=text:raise RuntimeError('External gold version immutable')
  target.write_text(text,encoding='utf-8')
 print('External gold frozen:',len(CASES))

if __name__=='__main__':main()
