"""Source-image adjudication only; never imported by the extraction engine."""
import hashlib,json
from scripts.azure_acceptance import ROOT

def main():
 source=ROOT/'data/acceptance/gold-full-v1';dest=ROOT/'data/acceptance/gold-full-v2';dest.mkdir(exist_ok=True)
 reviewed={'IMG_OCR_6_T_BL_'+n for n in ['002720','005257','014231','017394']}
 changes=[]
 for path in source.glob('*.json'):
  gold=json.loads(path.read_text(encoding='utf-8'))
  if path.stem in reviewed:
   image=ROOT/'data/acceptance/documents'/path.stem/'image.png'
   change={'document':path.stem,'field':'fields.freight_terms','before':gold['fields']['freight_terms'],'after':'PREPAID',
    'reason':'Manually viewed the full source image: Freight & Charges table contains a monetary amount under Prepaid and an empty Collect column. The prior null annotation omitted this explicit table evidence.',
    'source_image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'parent_gold_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
   gold['fields']['freight_terms']='PREPAID';gold['freight_adjudication']=change;changes.append(change)
  text=json.dumps(gold,ensure_ascii=False,indent=2)
  target=dest/path.name
  if target.exists() and target.read_text(encoding='utf-8')!=text:raise RuntimeError('Gold version is immutable')
  target.write_text(text,encoding='utf-8')
 (ROOT/'outputs/acceptance/freight-gold-corrections-v2.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Source-reviewed corrections:',len(changes))

if __name__=='__main__':main()
