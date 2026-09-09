"""Evaluation-only human source review, never imported by the extraction engine.

Completes the initial DEVELOPMENT set against all frozen schema fields. Values
below are ground-truth transcriptions, not resolver rules. Original draft and
audited subset gold are retained for the fixed before/after comparison.
"""
import json,hashlib
from pathlib import Path
from scripts.azure_acceptance import ROOT
from fintraocr.schemas import catalog,ALIASES

FIELDS={
 'NV_004233':{'payment_terms':'T/T','currency':'USD'},
 'NV_015564':{'payment_terms':'L/C','currency':'USD'},
 'NV_013073':{'payment_terms':'By T/T 6 % : Upon signing the contract 94 % : Upon cargo arrival at the discharge port 24 % : After inspection within 69 days from cargo arrival at the discharging port'},
 'NV_014523':{'payment_terms':'By C/P 2 % : Upon signing the contract 68 % : Upon cargo arrival at the discharge port 64 % : After inspection within 13 days from cargo arrival at the discharging port'},
 'BL_004195':{'place_of_receipt':'LLICO, CHILE','freight_terms':'PREPAID'},
 'BL_011763':{'place_of_receipt':'ADA, GHANA','freight_terms':'PREPAID'},
 'BL_009780':{'exporter':'KOST MERCHANT SERVICES','declared_value':'941.50','freight_terms':'PREPAID'},
 'BL_019578':{'freight_terms':'PREPAID'},
 'BL_020293':{'freight_terms':'PREPAID'},
 'BL_021639':{'freight_terms':'PREPAID'},
}
ROWS={
 'NV_022258':{0:{'marks':'DLSU6551895 W704363'}},
 'PL_001315':{0:{'marks':'Slide A1 ~ A 6'},1:{'marks':'Nut B10 ~ B 72'}},
 'PL_007151':{0:{'marks':'Lift A1 ~ A 2'},1:{'marks':'SPANNER B10 ~ B 31'}},
 'PL_021849':{0:{'marks':'DLSU4197816 F263284'}},
 'PL_025157':{0:{'marks':'DLSU5937403 T614048'}},
 'BL_002720':{0:{'container_number':'DLSU2808059','seal_number':'R689074'}},
 'BL_005257':{0:{'container_number':'DLSU1738372','seal_number':'T954897'}},
 'BL_014231':{0:{'container_number':'DLSU8513775','seal_number':'C492160'}},
 'BL_017394':{0:{'container_number':'DLSU3847448','seal_number':'A710369'}},
 'BL_004195':{0:{'container_number':'DLSU4520816','marks':'D635551'}},
 'BL_011763':{0:{'container_number':'DLSU6670105','marks':'H733639'}},
 'BL_009780':{0:{'container_number':'DLSU9114238','marks':'Q715038'}},
 'BL_019578':{0:{'container_number':'DLSU8362980','seal_number':'D840548'}},
 'BL_020293':{0:{'container_number':'DLSU5817160','seal_number':'H076558'}},
 'BL_021639':{0:{'container_number':'DLSU7280474','seal_number':'J319282'}},
}

def main():
 out=ROOT/'data/acceptance/gold-full-v1';out.mkdir(exist_ok=True)
 for p in sorted((ROOT/'data/acceptance/gold-audited').glob('*.json')):
  g=json.loads(p.read_text(encoding='utf-8'));code=p.stem.removeprefix('IMG_OCR_6_T_');schema=catalog()[g['document_type']]
  g['schema_coverage_gaps']={k:v for k,v in g['fields'].items() if k not in schema['fields']}
  g['fields']={k:g['fields'].get(k) for k in schema['fields']};g['fields'].update(FIELDS.get(code,{}))
  for i,row in enumerate(g['items']):
   g['items'][i]={k:row.get(k) for k in schema['items']};g['items'][i].update(ROWS.get(code,{}).get(i,{}))
  for section in [g['fields'],*g['items']]:
   for kind in ['gross','net']:
    if section.get(kind+'_weight') is not None and section.get('weight_unit') is not None:section[kind+'_weight_unit']=section['weight_unit']
  for alias,target in ALIASES[g['document_type']].items():g['fields'][alias]=g['fields'][target]
  g.update(coverage='all_applicable_fields_reviewed',gold_version='full-development-v1',unscored_fields=[],source='Human review of source images/contact sheets and independent Azure word annotations; never copied model output',parent_gold_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  g['review_notes']=['Blank fields were reviewed against the source, not inferred from model nulls.','No row totals are calculated. Unlabelled numeric footers are not invented goods rows.','References in signature/company address blocks do not establish a trade-party role.','Physical container identifiers are separated from remaining marks only where the caption names containers.','Payment conditions in the same primary field include their continuation lines. Payment-method labels in a separate remittance block do not replace the primary field.']
  if g['layout_family']=='shipper-exporter-borderless-cargo':g['review_notes'].append('Source caption TOTAL NEW WEIGHT is interpreted as a net-weight typographic error in the paired net/gross weight context. This disputed caption needs separate human adjudication; do not use this development set to certify acceptance.')
  source=ROOT/'data/acceptance/documents'/p.stem
  g['source_image_sha256']=hashlib.sha256((source/'image.png').read_bytes()).hexdigest()
  g['source_annotation_sha256']=hashlib.sha256((source/'annotation.json').read_bytes()).hexdigest()
  target=out/p.name
  content=json.dumps(g,ensure_ascii=False,indent=2)
  if target.exists() and target.read_text(encoding='utf-8')!=content:raise RuntimeError('Gold version is immutable; create a new version')
  target.write_text(content,encoding='utf-8')
 print('Completed reviewed development gold:',len(list(out.glob('*.json'))))
if __name__=='__main__':main()
