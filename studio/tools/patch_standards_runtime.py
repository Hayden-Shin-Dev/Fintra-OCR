# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Apply the retrieval API compatibility fix to an installed local Fintra runtime.

Backs up the original file and fails on unfamiliar source instead of guessing.
Restart the Fintra service supervisor after applying while no jobs are running.
"""
import json, os
from pathlib import Path

def apply(home=None):
    home=Path(home or Path(os.environ['LOCALAPPDATA'])/'Fintra').resolve()
    release=json.loads((home/'current.json').read_text('utf-8'))['version']
    target=(home/'versions'/release/'FintraStandards/fintra_standards/server.py').resolve()
    if not target.is_relative_to(home/'versions'):raise ValueError('Runtime path outside versions')
    before=target.read_text('utf-8')
    old="ENGINE.search(data['query'],top_k=data.get('top_k',5),framework=data.get('framework'))"
    new="ENGINE.search(data['query'],top_k=data.get('top_k',5),framework=data.get('framework'),source_types=data.get('source_types'),method=data.get('method','hybrid'))"
    if new in before:return False
    if before.count(old)!=1:raise ValueError('Unrecognized standards API version')
    backup=target.with_suffix('.py.before-source-filter')
    if not backup.exists():backup.write_bytes(target.read_bytes())
    target.write_text(before.replace(old,new),encoding='utf-8')
    return True

if __name__=='__main__':print('Updated' if apply() else 'Already current')
