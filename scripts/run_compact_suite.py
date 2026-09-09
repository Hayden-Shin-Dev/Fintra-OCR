import json,subprocess,sys
from pathlib import Path
entries=json.loads(Path('data/holdout/manifest.json').read_text(encoding='utf-8'))+json.loads(Path('data/fresh/manifest.json').read_text(encoding='utf-8'))
for e in entries:
 if not Path('outputs/benchmark',e['id'],'medium.ocr.json').exists():continue
 p=subprocess.run([sys.executable,'-X','utf8','-m','scripts.bench_compact','--id',e['id']],capture_output=True,text=True)
 print(e['id'],p.returncode,p.stdout[-150:] if p.returncode==0 else p.stderr[-1500:],flush=True)
