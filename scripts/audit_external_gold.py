"""Source-image adjudication after external development review; retain v1.

No engine predictions are read. These cases are development, never final holdout.
"""
import json,hashlib
from scripts.azure_acceptance import ROOT

CORRECTIONS={
 'kchain-packing':[
  ('fields.packing_list_number',None,'Caption is only Reference; identifier text does not establish a packing-list-number role.'),
  ('fields.document_reference','RT/PL/2026/1047','Reference is the explicitly printed caption.')],
 'shipzy-invoice':[
  ('fields.place_of_delivery',None,'Destination Port repeats Port of Discharge; neither establishes a separate place-of-delivery role.'),
  ('items.0.unit','TON','TON does not specify metric versus short/long ton. Preserve source unit under the frozen unknown-unit contract.'),
  ('items.1.unit','TON','TON does not specify metric versus short/long ton. Preserve source unit under the frozen unknown-unit contract.'),
  *[(f'items.{i}.{field}',None,'WT. / BAG explicitly gives per-bag weight, not this goods-row total. Keep field present and require review; no multiplication is authorized.') for i in range(2) for field in ['net_weight','gross_weight']]],
 'usda-handbook':[
  ('fields.carrier',None,'Signature explicitly says AGENT FOR THE CARRIER. The agent company cannot be assigned the carrier role.')]
}

def main():
 log=[]
 for name,changes in CORRECTIONS.items():
  folder=ROOT/'data/acceptance/external'/name
  source=folder/'gold-v1.json';g=json.loads(source.read_text(encoding='utf-8'))
  image=folder/g['source_image'];assert hashlib.sha256(image.read_bytes()).hexdigest()==g['source_image_sha256']
  for path,value,reason in changes:
   keys=path.split('.');parent=g
   for k in keys[:-1]:parent=parent[int(k)] if isinstance(parent,list) else parent[k]
   old=parent[keys[-1]];parent[keys[-1]]=value
   log.append({'document':name,'field':path,'before':old,'after':value,'reason':reason,'source_image_sha256':g['source_image_sha256'],'prior_gold_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
  g['role']='development_validation';g['gold_method']='v2 source-image semantic-role and measurement-basis adjudication; v1 preserved'
  if name=='shipzy-invoice':g['expected_review']=[f'items.{i}.{field}' for i in range(2) for field in ['net_weight','gross_weight']]
  if name=='usda-handbook':g['expected_review']=['fields.issue_date','fields.gross_weight','fields.volume','items.0.gross_weight','items.0.volume']
  g['review_notes']+=['Gold v2 corrects explicit role and measurement-basis errors. Compare both versions on this same gold; gold changes are not engine improvements. Independent review is still required.']
  dest=folder/'gold-v2.json';text=json.dumps(g,ensure_ascii=False,indent=2)
  if dest.exists() and dest.read_text(encoding='utf-8')!=text:raise RuntimeError('Gold v2 is immutable')
  dest.write_text(text,encoding='utf-8')
 (ROOT/'outputs/acceptance/external-gold-v2-audit.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Source-adjudicated corrections:',len(log))

if __name__=='__main__':main()
