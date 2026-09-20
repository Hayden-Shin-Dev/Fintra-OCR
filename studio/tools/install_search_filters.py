# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Idempotently extend the installed local search service; preserve existing hybrid index."""
from pathlib import Path
import os,shutil
ROOT=Path(__file__).resolve().parents[1]
def install(home=None):
    home=Path(home or Path(os.environ['LOCALAPPDATA'])/'Fintra/versions/0.6.1-preview/FintraStandards/fintra_standards')
    shutil.copyfile(ROOT/'backend/standards_metadata.py',home/'standards_metadata.py')
    p=home/'search.py';text=p.read_text('utf-8')
    if 'metadata_filters=None' not in text:
        shutil.copyfile(p,p.with_suffix('.py.pre-chat-v2'))
        text=text.replace("method='hybrid'):","method='hybrid',metadata_filters=None):")
        text=text.replace("start=time.perf_counter();query=query.strip()","from .standards_metadata import matches\n        matches({}, metadata_filters)  # validate even for an empty corpus\n        start=time.perf_counter();query=query.strip()")
        text=text.replace("if (not framework or re.sub", "if matches(r,metadata_filters) and (not framework or re.sub")
        p.write_text(text,'utf-8')
    if "r['_standards_metadata']" not in text:
        text=text.replace("self.rows=[dict(r) for r in db.execute('SELECT * FROM chunks ORDER BY id')]", "self.rows=[dict(r) for r in db.execute('SELECT * FROM chunks ORDER BY id')]\n            from .standards_metadata import metadata\n            for r in self.rows:r['_standards_metadata']=metadata(r)")
        p.write_text(text,'utf-8')
    p=home/'server.py';text=p.read_text('utf-8')
    if "metadata_filters=data.get" not in text:
        shutil.copyfile(p,p.with_suffix('.py.pre-chat-v2'))
        text=text.replace("method=data.get('method','hybrid')))","method=data.get('method','hybrid'),metadata_filters=data.get('metadata_filters')))")
        p.write_text(text,'utf-8')
    return str(home)
if __name__=='__main__':print(install())
