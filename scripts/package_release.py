"""Package source and selected reproducibility artifacts, excluding runtimes."""
from pathlib import Path
import zipfile,json,hashlib
root=Path(__file__).resolve().parents[1]
files=set()
def add(path):
 p=root/path
 if p.is_file():files.add(p)
 elif p.is_dir():
  files.update(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix not in {'.pyc','.pstats'})
for p in ['fintraocr','tests','scripts','data/holdout','data/fresh','outputs/compact-study/qwen3.5-4b'] :add(p)
for p in ['data/sample','data/inventory_checks.json','outputs/inventory','outputs/inventory-regression']:add(p)
for p in root.iterdir():
 if p.is_file():files.add(p)
for p in (root/'outputs/compact-study').glob('external-*-final'):add(p.relative_to(root))
for p in ['final-report.json','tests.xml','cli-final.json','lakay-first-score.json','montana-first-score.json','iccc-code-profile-after.json']:add('outputs/compact-study/'+p)
for p in (root/'outputs/benchmark').glob('*/medium.ocr.json'):add(p.relative_to(root))
for name in ['sample_commercial_invoice','sample_packing_list','sample_bill_of_lading']:add('outputs/structural-v2/'+name)
for name in ['lakay','montana','iccc']:add('data/external/'+name+'.gold.json')
for p in (root/'data/external').glob('*manifest*'):add(p.relative_to(root))
for jid in ['d7d48e9438cd4830ae2c5eb46f3070e4','28047c0ad21a4da3ba18c84304fe0e0e','1670935ab75b49bbb3afb87db86781d8','0531a4763a2f410e81b0bf7acc580271','728d71eb33a44c40b5c5e1f2734750b1','664588c0c97c41ea809143df3503b07e','47ddef93b8b34f1ea908b1cdd6a7bfb4','5330796a471143b38b6b9709cdf3ab55']:
 add('data/ui/'+jid)
dest=root.parent/'FintraOCR-latest.zip'
for jid in ['7e4a4768c1f946cda2ca298cb866bb85','8f13ceeb6f2a4bd9b4f111d2ca01a69b','6f8291c3adc2496088192d408ad1384a','265dcfbf687947e5923ecaa6dee3cebc','fa9c77a3d3224a9cb37ec90630d4bd3a']:
 add('data/ui/'+jid)
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(files):z.write(p,Path('FintraOCR')/p.relative_to(root))
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
print(json.dumps({'path':str(dest),'files':len(files),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))
