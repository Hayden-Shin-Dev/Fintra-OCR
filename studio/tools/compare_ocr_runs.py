# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def stable(obj):
    if isinstance(obj,dict):
        return {k:stable(v) for k,v in obj.items() if k not in {'mapping_metadata','source','seconds','created_at'}}
    if isinstance(obj,list):return [stable(v) for v in obj]
    return obj
a,b=[json.loads((ROOT/'tests'/('speed-'+x+'.json')).read_text('utf-8')) for x in sys.argv[1:]]
findings=[]
for path in sorted((ROOT/'tests/speed-runs'/a['job_id']).glob('*.result.json')):
    left=json.loads(path.read_text('utf-8'));right=json.loads((ROOT/'tests/speed-runs'/b['job_id']/path.name).read_text('utf-8'))
    sections={k:stable(left[k])==stable(right[k]) for k in ('document_type','fields','items','issues','ocr','proposal')}
    findings.append({'document':path.name,'same':sections})
out={'before':a,'after':b,'comparison':findings,'equal':all(all(f['same'].values()) for f in findings)}
(ROOT/'tests'/('equivalence-'+sys.argv[1]+'-'+sys.argv[2]+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
