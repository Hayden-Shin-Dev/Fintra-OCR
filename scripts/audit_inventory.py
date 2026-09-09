"""Inventory all provided images and reuse OCR only after matching image bytes."""
import json,hashlib,time,argparse
from pathlib import Path
from urllib.request import Request,urlopen
from fintraocr.models import OCRDocument
from fintraocr.compact import CompactSelector
from fintraocr.mapping import MappingEngine
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--version',default='before');p.add_argument('--ids',nargs='*');a=p.parse_args()
 out=ROOT/'outputs/inventory';out.mkdir(exist_ok=True)
 entries=read(ROOT/'data/sample/manifest.json');cache={}
 for path in (ROOT/'data/ui').glob('*/ocr.json'):
  image=path.parent/'page-1.png'
  if image.exists():cache[digest(image)]=path
 for i,e in enumerate(entries):
  source=Path(e['path']);name=source.stem
  if a.ids and name not in a.ids:continue
  dest=out/name;dest.mkdir(exist_ok=True);ocrpath=dest/'ocr.json'
  if not ocrpath.exists():
   found=cache.get(digest(source))
   if found:ocrpath.write_bytes(found.read_bytes())
   else:
    with urlopen(Request(f'http://127.0.0.1:8768/api/samples/{i}',data=json.dumps({'mode':'ocr','model':'qwen3.5:4b'}).encode(),headers={'Content-Type':'application/json'})) as response:jid=json.load(response)['id']
    started=time.monotonic()
    while True:
     jobpath=ROOT/'data/ui'/jid/'job.json'
     try:job=read(jobpath) if jobpath.exists() else {}
     except json.JSONDecodeError:job={}
     if job.get('status') in ['complete','failed','cancelled']:break
     if time.monotonic()-started>900:raise TimeoutError(jid)
     time.sleep(.5)
    if job['status']!='complete':raise RuntimeError(job)
    ocrpath.write_bytes((jobpath.parent/'ocr.json').read_bytes())
  meta={'image':str(source),'image_sha256':digest(source),'expected_type':e['expected_type'],'ocr_sha256':digest(ocrpath)}
  (dest/'source.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
  version=dest/a.version;version.mkdir(exist_ok=True)
  if (version/'result.json').exists():continue
  s=CompactSelector('qwen3.5:4b');s.trace_path=version/'trace.json';started=time.monotonic()
  try:
   r=MappingEngine(s).map(OCRDocument.model_validate(read(ocrpath)))
   (version/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
   status={'seconds':time.monotonic()-started,'document_type':r.document_type,'header_accepted':sum(f.value is not None for f in r.fields.values()),'rows':len(r.items)}
   (version/'timing.json').write_text(json.dumps(status),encoding='utf-8');print(name,status,flush=True)
  finally:s.persist_trace()
if __name__=='__main__':main()
