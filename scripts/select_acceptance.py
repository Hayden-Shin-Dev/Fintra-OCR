"""Preselect staged documents without looking at engine output; not a gold mapper."""
import argparse,hashlib,json,random,zipfile
from pathlib import Path
from scripts.azure_acceptance import ROOT,BlobReader,blobs
KINDS={'INV':'commercial_invoice','PL':'packing_list','BL':'bill_of_lading'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=10);a=p.parse_args()
 out=ROOT/'data/acceptance';manifest=out/'selection.json'
 if not manifest.exists():
  excluded={p.stem for p in (ROOT/'data/sample').rglob('*.png')};entries=[]
  for code,kind in KINDS.items():
   pools=[]
   for archive in sorted((out/'labels').glob(code+'*.zip')):
    with zipfile.ZipFile(archive) as z:names=sorted(n for n in z.namelist() if n.endswith('.json') and Path(n).stem not in excluded)
    random.Random('fintra-acceptance-20260909-'+archive.stem).shuffle(names);pools.append((archive,names))
   for i in range(150):
    archive,names=pools[i%len(pools)];member=names[i//len(pools)]
    with zipfile.ZipFile(archive) as z:d=json.loads(z.read(member))
    entries.append({'id':Path(member).stem,'type':kind,'archive':archive.stem,'label_member':member,'ordinal':i+1,'batch':10 if i<10 else 20 if i<30 else 30 if i<60 else 40 if i<100 else 'reserve','role':'unseen','layout_family':None,'novelty':'unassessed','label_sha256':hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()})
  manifest.write_text(json.dumps({'selection_seed':'fintra-acceptance-20260909','note':'Archive shard is NOT a layout family. Layout novelty must be visually reviewed. Batch sizes are incremental 10+20+30+40=100 per type. Extra 50 per type reserved.','entries':entries},ensure_ascii=False,indent=2),encoding='utf-8')
 data=json.loads(manifest.read_text(encoding='utf-8'));existing_hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/sample').rglob('*.png')}
 selected=[e for e in data['entries'] if e['ordinal']<=a.count]
 for tag in sorted({e['archive'] for e in selected}):
  b=next(b for b in blobs() if '/Validation/01.' in b['name'] and b['name'].endswith('_'+tag+'.zip'))
  with zipfile.ZipFile(BlobReader(b)) as z,zipfile.ZipFile(out/'labels'/(tag+'.zip')) as labels:
   files={Path(n).stem:n for n in z.namelist() if not n.endswith('/')}
   for e in selected:
    if e['archive']!=tag:continue
    dest=out/'documents'/e['id'];dest.mkdir(parents=True,exist_ok=True)
    image=dest/'image.png'
    if not image.exists():image.write_bytes(z.read(files[e['id']]))
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    if digest in existing_hashes:raise RuntimeError('Existing image duplicate: '+e['id'])
    (dest/'annotation.json').write_bytes(labels.read(e['label_member']))
    e.update(image_sha256=digest,blob=b['name'],blob_etag=b['properties']['etag'],image_member=files[e['id']])
    print(e['id'],image.stat().st_size,flush=True)
 manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
