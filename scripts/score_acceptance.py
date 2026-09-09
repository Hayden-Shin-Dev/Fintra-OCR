"""Acceptance scoring independent of production resolver and normalization."""
import argparse,json,re,statistics,hashlib
from collections import defaultdict,Counter
from decimal import Decimal,InvalidOperation
from pathlib import Path
from scripts.azure_acceptance import ROOT
from fintraocr.schemas import catalog,ALIASES
def equivalent(a,b,kind):
 if a is None or b is None:return a is b
 if kind=='number':
  try:return Decimal(a)==Decimal(b)
  except InvalidOperation:return False
 return ' '.join(str(a).split())==' '.join(str(b).split())
def flat(g):
 out={'fields.'+k:v for k,v in g['fields'].items()}
 for i,row in enumerate(g['items']):out.update({f'items.{i}.{k}':v for k,v in row.items()})
 return out
def actual(r,path):
 cur=r
 for part in path.split('.'):
  if isinstance(cur,list):cur=cur[int(part)] if int(part)<len(cur) else {}
  elif isinstance(cur,dict):cur=cur.get(part,{})
  else:return {}
 return cur if isinstance(cur,dict) else {}

def audit_result_contract(r,g):
 """Do not let null equality hide a missing field or an unresolved ambiguity."""
 issues=[]
 for path in flat(g):
  field=actual(r,path)
  if 'value' not in field or 'status' not in field:
   issues.append({'field':path,'reason':'missing_applicable_field_or_status'})
 for path in g.get('expected_review',[]):
  field=actual(r,path)
  if field.get('status')!='review' or field.get('value') is not None:
   issues.append({'field':path,'reason':'ambiguous_source_requires_null_and_review','actual_status':field.get('status'),'actual_value':field.get('value')})
 return issues
def bucket():return {'tp':0,'fp':0,'fn':0,'tn':0,'checks':0}
def count(b,expected,got,correct):
 b['checks']+=1
 if correct:b['tp' if expected is not None else 'tn']+=1
 else:
  if got is not None:b['fp']+=1
  if expected is not None:b['fn']+=1
def rates(b):
 b.update(precision=b['tp']/(b['tp']+b['fp']) if b['tp']+b['fp'] else None,recall=b['tp']/(b['tp']+b['fn']) if b['tp']+b['fn'] else None)
 return b
def cause(r,field,path,expected):
 if r.get('document_type')=='unknown':return 'document_classification'
 if path.startswith('items.') and int(path.split('.')[1])>=len(r.get('items',[])):return 'item_row_link'
 if field.get('value') is not None:return 'wrong_field_link'
 issues=' '.join(field.get('issues',[]))
 if any(s in issues for s in ['invalid_date','ambiguous_number','invalid_number','unrecognized','numeric_material']):return 'normalization'
 if field.get('status')=='review':return 'evidence_validation'
 ocr=' '.join(t['text'] for t in r.get('ocr',{}).get('tokens',[]))
 clean=lambda s:re.sub(r'\W','',str(s)).casefold()
 if expected is not None and clean(expected) not in clean(ocr):return 'ocr_omission'
 return 'model_nonproposal' if field.get('null_reason') in ['not_proposed','label_not_proposed',None] else 'wrong_field_link'
def main():
 p=argparse.ArgumentParser();p.add_argument('--version',default='baseline');p.add_argument('--count',type=int,default=10);p.add_argument('--start-ordinal',type=int,default=1);p.add_argument('--gold-dir',default='gold');p.add_argument('--report-name');a=p.parse_args()
 selection=json.loads((ROOT/'data/acceptance/selection.json').read_text(encoding='utf-8'))['entries'];groups={};errors=[];documents=[]
 for e in selection:
  if not a.start_ordinal<=e['ordinal']<=a.count:continue
  gpath=ROOT/'data/acceptance'/a.gold_dir/(e['id']+'.json');rpath=ROOT/'outputs/acceptance/runs'/e['id']/a.version/'result.json'
  if not gpath.exists() or not rpath.exists():documents.append({'id':e['id'],'status':'not_scored','gold_exists':gpath.exists(),'result_exists':rpath.exists()});continue
  g=json.loads(gpath.read_text(encoding='utf-8'));r=json.loads(rpath.read_text(encoding='utf-8'));kind=g['document_type'];schema=catalog()[kind]
  group=groups.setdefault(kind,{'metrics':bucket(),'per_field':{},'families':{},'documents':0,'unscored_predictions':0,'mapping_seconds':[]});group['documents']+=1
  timing=json.loads((rpath.parent/'map-timing.json').read_text());group['mapping_seconds'].append(timing['seconds'])
  group['model_response_replayed']=bool(timing.get('replayed'))
  local=bucket();family=group['families'].setdefault(g['layout_family'],bucket());expected=flat(g)
  for path,want in expected.items():
   key=path.split('.')[-1]
   if path.startswith('fields.') and key in ALIASES[kind]:continue
   field=actual(r,path);got=field.get('value');spec=schema['items' if path.startswith('items.') else 'fields'].get(key)
   if spec is None:continue # Reported separately as a frozen-schema coverage gap.
   ok=equivalent(want,got,spec['kind']);label=re.sub(r'items\.\d+\.','items.',path);per=group['per_field'].setdefault(label,bucket())
   for b in [local,group['metrics'],family,per]:count(b,want,got,ok)
   if not ok:errors.append({'id':e['id'],'type':kind,'field':path,'expected':want,'actual':got,'status':field.get('status'),'reason':field.get('null_reason'),'issues':field.get('issues'),'provisional_cause':cause(r,field,path,want),'cause_confirmed':False})
  # Additional emitted goods rows are false positives, not unscored fields.
  for i in range(len(g['items']),len(r.get('items',[]))):
   for key,field in r['items'][i].items():
    if field.get('value') is None:continue
    per=group['per_field'].setdefault('items.'+key,bucket())
    for b in [local,group['metrics'],family,per]:count(b,None,field['value'],False)
    errors.append({'id':e['id'],'type':kind,'field':f'items.{i}.{key}','expected':None,'actual':field['value'],'status':field.get('status'),'reason':'additional_goods_row','issues':field.get('issues'),'provisional_cause':'item_row_link','cause_confirmed':False})
  uncovered=[]
  for name,field in r.get('fields',{}).items():
   if 'fields.'+name not in expected and name not in ALIASES[kind] and field.get('value') is not None:uncovered.append('fields.'+name)
  for i,row in enumerate(r.get('items',[])):
   for name,field in row.items():
    if i<len(g['items']) and f'items.{i}.{name}' not in expected and field.get('value') is not None:uncovered.append(f'items.{i}.{name}')
  group['unscored_predictions']+=len(uncovered)
  gaps=[path for path in expected if path.split('.')[-1] not in schema['items' if path.startswith('items.') else 'fields']]
  alias_errors=[alias for alias,target in ALIASES[kind].items() if actual(r,'fields.'+alias).get('value')!=actual(r,'fields.'+target).get('value')]
  documents.append({'id':e['id'],'metrics':rates(local),'unscored_predictions':uncovered,'schema_coverage_gaps':gaps,'contract_errors':audit_result_contract(r,g),'expected_rows':len(g['items']),'actual_rows':len(r.get('items',[])),'coverage':g['coverage'],'role':e['role'],'gold_sha256':hashlib.sha256(gpath.read_bytes()).hexdigest(),'result_sha256':hashlib.sha256(rpath.read_bytes()).hexdigest(),'classification_correct':r.get('document_type')==kind,'alias_errors':alias_errors})
 for group in groups.values():
  rates(group['metrics'])
  for b in [*group['per_field'].values(),*group['families'].values()]:rates(b)
  group['mapping_median_seconds']=statistics.median(group['mapping_seconds']);group['mapping_max_seconds']=max(group['mapping_seconds'])
  group['low_performing_fields']={k:v for k,v in group['per_field'].items() if any(v[m] is not None and v[m]<.95 for m in ['precision','recall'])}
 report={'version':a.version,'gold_directory':a.gold_dir,'acceptance_passed':False,'reason':'Final acceptance requires complete independent holdout, per-core-field threshold, and external validation; development or replay scores cannot certify acceptance','groups':groups,'documents':documents,'errors':errors,'provisional_failure_counts':dict(Counter(e['provisional_cause'] for e in errors))}
 out=ROOT/'outputs/acceptance'/('score-'+(a.report_name or a.version)+'.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:{'documents':v['documents'],**v['metrics'],'unscored_predictions':v['unscored_predictions']} for k,v in groups.items()},indent=2));print('Errors',len(errors),'Acceptance: NOT PASSED')
if __name__=='__main__':main()
