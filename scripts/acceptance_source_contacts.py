"""Source-only review sheets; never opens model outputs or predicted fields."""
import json
from PIL import Image,ImageDraw
from scripts.azure_acceptance import ROOT

def main():
 entries=json.loads((ROOT/'data/acceptance/selection.json').read_text(encoding='utf-8'))['entries']
 out=ROOT/'outputs/acceptance/source-review-batch20';out.mkdir(exist_ok=True)
 for kind in ['commercial_invoice','packing_list','bill_of_lading']:
  selected=[e for e in entries if e['type']==kind and 11<=e['ordinal']<=30]
  for start in range(0,len(selected),5):
   sheet=Image.new('RGB',(2250,690),'#dddddd');draw=ImageDraw.Draw(sheet)
   for i,e in enumerate(selected[start:start+5]):
    source=Image.open(ROOT/'data/acceptance/documents'/e['id']/'image.png').convert('RGB');source.thumbnail((440,650))
    sheet.paste(source,(i*450+(440-source.width)//2,35));draw.text((i*450+5,8),e['id']+' / '+str(e['ordinal']),fill='black')
   sheet.save(out/f'{kind}-{start//5}.jpg',quality=92)
 print(out)

if __name__=='__main__':main()
