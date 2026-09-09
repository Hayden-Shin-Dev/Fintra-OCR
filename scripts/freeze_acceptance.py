"""Create an immutable-by-convention baseline before acceptance work."""
import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen,Request
from fintraocr.schemas import catalog
from fintraocr.compact import PROMPT
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/acceptance/baseline-20260909'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 if (OUT/'manifest.json').exists():raise SystemExit('Baseline already exists; refusing to overwrite')
 OUT.mkdir(parents=True,exist_ok=True)
 source=[p for folder in ['fintraocr','scripts','tests'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 source += [p for p in ROOT.iterdir() if p.is_file()]
 manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'status':'baseline, not acceptance passed','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source},'python':sys.version,'ocr_settings':{'profile':'medium','lang':'en','device':'gpu:0','max_side':2400,'enhance':False,'text_rec_score_thresh':0.0,'use_textline_orientation':True},'model':'qwen3.5:4b','schemas':catalog(),'baseline_documents':[]}
 with zipfile.ZipFile(OUT/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in source:z.write(p,p.relative_to(ROOT))
 (OUT/'prompt.txt').write_text(PROMPT,encoding='utf-8')
 (OUT/'pip-freeze.txt').write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze']))
 for folder in (ROOT/'outputs/inventory').iterdir():
  version=next(v for v in ['final-v7','final-v6','final-v5','final-v4'] if (folder/v/'result.json').exists())
  dest=OUT/'documents'/folder.name;dest.mkdir(parents=True)
  for p in [folder/'source.json',folder/'ocr.json',*list((folder/version).glob('*.json'))]:shutil.copy2(p,dest/p.name)
  manifest['baseline_documents'].append({'id':folder.name,'version':version,'files':{p.name:sha(p) for p in dest.iterdir()}})
 modelroot=Path.home()/'.paddlex/official_models'
 manifest['ocr_model_sha256']={str(p.relative_to(modelroot)):sha(p) for name in ['PP-OCRv6_medium_det','PP-OCRv6_medium_rec','PP-LCNet_x1_0_textline_ori'] for p in (modelroot/name).rglob('*') if p.is_file()}
 manifest['ollama_tags']=json.load(urlopen('http://127.0.0.1:11434/api/tags'))
 manifest['ollama_show']=json.load(urlopen(Request('http://127.0.0.1:11434/api/show',data=json.dumps({'model':'qwen3.5:4b'}).encode(),headers={'Content-Type':'application/json'})))
 manifest['source_zip_sha256']=sha(OUT/'source.zip')
 (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Frozen',len(source),'source files and',len(manifest['baseline_documents']),'documents at',OUT)
if __name__=='__main__':main()
