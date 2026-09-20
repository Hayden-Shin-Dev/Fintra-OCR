# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Evaluate sealed, external-layout annotations; never feed gold to inference."""
import hashlib,json,sys
from decimal import Decimal,InvalidOperation
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PUBLIC=ROOT/'tests/holdout/public'
gold=json.loads((PUBLIC/'expected.json').read_text('utf-8'))
def normalized(value):
    s=str(value).strip().casefold()
    try:return str(Decimal(s.replace(',','')).normalize())
    except InvalidOperation:return ' '.join(s.split())
if sys.argv[1]=='seal':
    seal={'annotation_sha256':hashlib.sha256((PUBLIC/'expected.json').read_bytes()).hexdigest(),
          'images':{c['image']:hashlib.sha256((PUBLIC/c['image']).read_bytes()).hexdigest() for c in gold['cases']}}
    p=PUBLIC/'seal.json'
    if p.exists():raise SystemExit('Already sealed; do not overwrite holdout gold')
    p.write_text(json.dumps(seal,indent=2),'utf-8');print('Sealed 3 external layouts before inference');raise SystemExit
seal=json.loads((PUBLIC/'seal.json').read_text('utf-8'))
assert seal['annotation_sha256']==hashlib.sha256((PUBLIC/'expected.json').read_bytes()).hexdigest()
run=json.loads((ROOT/'tests'/('speed-'+sys.argv[1]+'.json')).read_text('utf-8'))
folder=ROOT/'tests/speed-runs'/run['job_id'];rows=[]
for i,case in enumerate(gold['cases']):
    assert seal['images'][case['image']]==hashlib.sha256((PUBLIC/case['image']).read_bytes()).hexdigest()
    p=folder/(str(i)+'.result.json');out=json.loads(p.read_text('utf-8')) if p.exists() else {}
    checks=[{'field':'document_type','expected':case['type'],'actual':out.get('document_type'),'pass':out.get('document_type')==case['type']}]
    for field,expected in case['fields'].items():
        cell=out.get('fields',{}).get(field,{})
        actual=cell.get('value');ok=actual is not None and normalized(actual)==normalized(expected) and cell.get('status')=='accepted'
        checks.append({'field':field,'expected':expected,'actual':actual,'status':cell.get('status'),'pass':ok})
    checks.append({'field':'item_count','expected':case['item_count'],'actual':len(out.get('items',[])),'pass':len(out.get('items',[]))==case['item_count']})
    rows.append({'image':case['image'],'source':case['source'],'checks':checks})
allchecks=[c for r in rows for c in r['checks']]
report={'scope':gold['scope'],'run':run,'documents':rows,'passed':sum(c['pass'] for c in allchecks),'total':len(allchecks),'all_passed':all(c['pass'] for c in allchecks)}
(ROOT/'tests'/('holdout-'+sys.argv[1]+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=False))
