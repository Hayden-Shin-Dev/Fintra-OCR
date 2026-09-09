import json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--version',default='candidate-v2');p.add_argument('--checks',default='data/inventory_checks.json');a=p.parse_args()
checks=json.loads(Path(a.checks).read_text(encoding='utf-8'))['checks'];correct=total=0;fail=[];missing=[]
for name,fields in checks.items():
 version=a.version
 if version=='final':version=next(v for v in ['final-v7','final-v6','final-v5','final-v4'] if (Path('outputs/inventory')/name/v/'result.json').exists())
 path=Path('outputs/inventory')/name/version/'result.json'
 if not path.exists():missing.append(name);continue
 r=json.loads(path.read_text(encoding='utf-8'))
 for field,expected in fields.items():
  value=r
  for part in field.split('.'):
   value=value[int(part)] if isinstance(value,list) and int(part)<len(value) else value.get(part,{}) if isinstance(value,dict) else {}
  actual=value.get('value') if isinstance(value,dict) else None
  total+=1;correct+=actual==expected
  if actual!=expected:fail.append({'document':name,'field':field,'expected':expected,'actual':actual,'reason':value.get('issues') if isinstance(value,dict) else None})
print(json.dumps({'version':a.version,'checks_source':a.checks,'correct':correct,'total':total,'errors':fail,'missing_documents':missing,'complete':not missing},ensure_ascii=False,indent=2))
if fail or missing:raise SystemExit(1)
