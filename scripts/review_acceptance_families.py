"""Manual visual family assessment of source-only contact sheets (no predictions)."""
import json,hashlib
from scripts.azure_acceptance import ROOT

FAMILIES={
 'commercial_invoice':[
  'exporter-grid-seven-columns','exporter-grid-seven-columns','shipper-seller-shared-buyer-po-columns','exporter-grid-seven-columns','invoice-remittance-footer',
  'exporter-grid-seven-columns','shipper-exporter-single-row','shipper-seller-shared-buyer-po-columns','shipper-seller-shared-buyer-po-columns','buyer-seller-proforma-two-tier-table',
  'shipper-exporter-single-row','shipper-exporter-single-row','shipper-exporter-single-row','shipper-exporter-single-row','buyer-seller-proforma-two-tier-table',
  'invoice-remittance-footer','shipper-exporter-single-row','exporter-grid-seven-columns','shipper-seller-shared-buyer-po-columns','buyer-seller-proforma-two-tier-table'],
 'packing_list':[
  'seller-country-po-three-row-weights','seller-country-po-three-row-weights','seller-buyer-net-gross-volume','seller-country-po-three-row-weights','certification-footer-hs-weights',
  'shipper-exporter-borderless-cargo','seller-country-po-three-row-weights','seller-country-po-three-row-weights','certification-footer-hs-weights','numbered-labels-wide-cargo-table',
  'shipper-exporter-borderless-cargo','shipper-exporter-borderless-cargo','seller-buyer-net-gross-volume','certification-footer-hs-weights','numbered-labels-wide-cargo-table',
  'seller-buyer-net-gross-volume','seller-country-po-three-row-weights','shipper-exporter-borderless-cargo','seller-country-po-three-row-weights','certification-footer-hs-weights'],
 'bill_of_lading':[
  'multimodal-hazard-freight-table','duplicate-consignee-liability-two-rows','duplicate-consignee-liability-two-rows','carrier-branded-receipt-single-row','surrendered-tank-carrier-two-row',
  'multimodal-hazard-freight-table','surrendered-tank-carrier-two-row','multimodal-hazard-freight-table','carrier-branded-receipt-single-row','surrendered-tank-carrier-two-row',
  'multimodal-hazard-freight-table','multimodal-hazard-freight-table','duplicate-consignee-liability-two-rows','surrendered-tank-carrier-two-row','surrendered-tank-carrier-two-row',
  'multimodal-hazard-freight-table','duplicate-consignee-liability-two-rows','multimodal-hazard-freight-table','duplicate-consignee-liability-two-rows','carrier-branded-receipt-single-row']}

def main():
 path=ROOT/'data/acceptance/selection.json';data=json.loads(path.read_text(encoding='utf-8'));report=[]
 for e in data['entries']:
  if not 11<=e['ordinal']<=30:continue
  family=FAMILIES[e['type']][e['ordinal']-11]
  new=family in {'seller-country-po-three-row-weights','surrendered-tank-carrier-two-row'}
  e.update(layout_family=family,novelty='new_to_development_set' if new else 'same_family',
    family_review='Manual source contact and frozen original-sample contact comparison; company names, values and image style alone do not define a family.')
  report.append({'id':e['id'],'type':e['type'],'family':family,'new_to_development_set':new,'image_sha256':e['image_sha256'],'prediction_inspected':False})
 out=ROOT/'outputs/acceptance/source-review-batch20/families.json'
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Source-reviewed families:',len(report))

if __name__=='__main__':main()
