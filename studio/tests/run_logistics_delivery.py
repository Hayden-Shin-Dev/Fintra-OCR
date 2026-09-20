# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Live local-model delivery check; does not overwrite user drafts."""
import json,sys,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ.setdefault('FINTRA_STANDARDS_URL','http://127.0.0.1:18769')
from workpapers import generate

folder=ROOT/'tests/qa-analyses/3d140f324fcc47e0b453c993684c1437'
result=json.loads((folder/'result.json').read_text('utf-8'))
started=time.perf_counter()
draft=generate(result,{'framework':'K-IFRS'})
output={'seconds':round(time.perf_counter()-started,3),'draft':draft}
(ROOT/'tests/logistics-delivery-kifrs.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'seconds':output['seconds'],'generation':draft['generation']},ensure_ascii=False))
