# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Reuse only byte-identical inputs with identical extraction code/model/settings."""
import hashlib,json,os
from pathlib import Path
from urllib.request import urlopen
from atomic_storage import write_json

def identity(image,settings):
    root=Path(os.environ.get('FINTRA_RELEASE_ROOT',''))/'FintraOCR'/'fintraocr'
    if not root.is_dir():return None
    digest=hashlib.sha256(image)
    digest.update(settings.encode())
    digest.update(str(root.resolve()).encode())
    for p in sorted(root.rglob('*.py')):
        digest.update(str(p.relative_to(root)).encode());digest.update(p.read_bytes())
    try:
        with urlopen('http://127.0.0.1:18434/api/tags',timeout=2) as r:models=json.load(r)['models']
        model=next(m for m in models if m['name']==json.loads(settings)['model'])
        digest.update(model['digest'].encode())
    except Exception:return None
    digest.update(os.environ.get('FINTRA_OCR_URL','').encode())
    return digest.hexdigest()

def read(root,token):
    if not token:return None
    p=Path(root)/(token+'.json')
    try:return json.loads(p.read_text('utf-8'))
    except (OSError,ValueError):return None

def store(root,token,value):
    if not token:return
    root=Path(root);root.mkdir(exist_ok=True,parents=True)
    write_json(root/(token+'.json'),value)
