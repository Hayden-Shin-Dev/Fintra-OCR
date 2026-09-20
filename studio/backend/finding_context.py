# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Model-independent Finding context, units/arithmetic and scoped conversation memory."""
from decimal import Decimal,InvalidOperation
from review_rules import build,REVIEW_RULES
from conversation_plan import previous_state
DOCS={'ledger':'장부','commercial_invoice':'상업송장','packing_list':'포장명세서','bill_of_lading':'선하증권'}
UNIT_FIELDS={'currency','unit','package_type','weight_unit','gross_weight_unit','net_weight_unit','volume_unit'}
def decimal(v):
 try:
  n=Decimal(str(v).replace(',',''));return n if n.is_finite() else None
 except (InvalidOperation,ValueError):return None

def findings(audit):
 review=build(audit);out=[]
 for tx in review['transactions']:
  for rule in tx['rule_results']:
   if rule['status']=='NOT_APPLICABLE':continue
   area,title=REVIEW_RULES.get(rule['rule_id'],('unmapped','추가 검토'))
   vs=rule.get('values',[]);primary=[v for v in vs if v['field'] not in UNIT_FIELDS] or vs
   values=[]
   for v in primary:
    source=v.get('source') or {};unitset={str(u['value']) for u in vs if u['field'] in UNIT_FIELDS and u.get('entity_id')==v.get('entity_id') and u.get('source',{}).get('item_index')==source.get('item_index') and u.get('value') is not None}
    values.append({'source':v.get('document_type') or 'unknown','field':v['field'],'value':v['value'],'unit':next(iter(unitset)) if len(unitset)==1 else '', 'provenance':source})
   f={'id':rule['check_id'],'check_ids':[rule['check_id']],'transaction_id':tx['transaction_id'],'transaction_name':tx['title'],'area':area,'title':title,'rule_id':rule['rule_id'],'status':rule['status'],'finding_type':{'FAIL':'value_mismatch','MISSING':'missing_evidence','REVIEW':'unresolved_comparison','PASS':'matched_values'}[rule['status']],'values':values,'performed_procedure':'document_value_comparison','difference':None,'direction':None}
   if len(values)==2:
    left,right=values;f.update(left_source=left['source'],right_source=right['source'],left_value=left['value'],right_value=right['value'],unit=left['unit'] if left['unit']==right['unit'] else None)
    x,y=decimal(left['value']),decimal(right['value'])
    if x is not None and y is not None and left['unit'] and left['unit']==right['unit'] and primary[0]['field'] not in UNIT_FIELDS:
     diff=x-y;f['difference']=str(diff);f['direction']='left_greater' if diff>0 else 'left_less' if diff<0 else 'equal'
   # Merge repeated, identical facts while retaining every evidence/check identifier.
   match=next((v for v in out if v['transaction_id']==f['transaction_id'] and v['rule_id']==f['rule_id'] and v['status']==f['status'] and v['values']==f['values']),None)
   if match:match['check_ids'].extend(f['check_ids'])
   else:out.append(f)
 return out

def select(all_findings,plan,history=(),transaction_id=None):
 state=previous_state(history);rows=all_findings
 if transaction_id:rows=[f for f in rows if f['transaction_id']==transaction_id]
 if plan.transaction:rows=[f for f in rows if f['transaction_name'].upper()==plan.transaction.upper() or f['transaction_id']==plan.transaction]
 elif not transaction_id and plan.follow_up and state.get('active_transaction'):rows=[f for f in rows if f['transaction_id']==state['active_transaction']]
 if plan.areas:rows=[f for f in rows if f['area'] in plan.areas]
 elif plan.follow_up and state.get('active_finding'):
  selected=[f for f in rows if f['id'] in state['active_finding']]
  if selected:rows=selected
 if plan.task not in ('FACT_LOOKUP','SUMMARY','EVIDENCE_REQUEST'):
  issues=[f for f in rows if f['status']!='PASS'];rows=issues or rows
 ordered=sorted(rows,key=lambda f:({'FAIL':0,'MISSING':1,'REVIEW':2,'PASS':3}[f['status']],f['area']))
 if plan.task=='SUMMARY':
  grouped={}
  for row in ordered:grouped.setdefault((row['transaction_id'],row['area']),row)
  return list(grouped.values())[:16]
 return ordered[:4]

def state_for(selected,plan):
 tx={f['transaction_id'] for f in selected}
 return {'active_transaction':next(iter(tx)) if len(tx)==1 else None,'active_finding':[f['id'] for f in selected],'current_topic':list(dict.fromkeys(f['area'] for f in selected)),'task_intent':plan.task}

def fmt(v,unit=''):
 n=decimal(v)
 return (f'{n:,.2f}'.rstrip('0').rstrip('.') if n is not None else str(v)) + (' '+unit if unit else '')

def fact_sentence(f):
 if f['difference'] is not None:
  d=decimal(f['difference']);l=DOCS.get(f['left_source'],f['left_source']);r=DOCS.get(f['right_source'],f['right_source']);unit=f.get('unit') or ''
  if d:return f"{l} {fmt(f['left_value'],unit)}, {r} {fmt(f['right_value'],unit)}로, {l}가 {r}보다 {fmt(abs(d),unit)} {'높습니다' if d>0 else '낮습니다'}."
  return f"{f['title']}은 {fmt(f['left_value'],unit)}로 일치합니다."
 vals=' / '.join(DOCS.get(v['source'],v['source'])+' '+('확인되지 않음' if v['value'] is None else fmt(v['value'],v['unit'])) for v in f['values'][:4])
 status={'FAIL':'서로 다릅니다','MISSING':'필수 정보가 없어 비교를 완료하지 못했습니다','REVIEW':'비교 범위를 추가로 확인해야 합니다','PASS':'비교한 값이 일치합니다'}[f['status']]
 return f['title']+(': '+vals if vals else '')+' — '+status+'.'

def transaction_context(selected):
 txs={}
 for f in selected:
  tx=txs.setdefault(f['transaction_id'],{'transaction_id':f['transaction_id'],'groups':[]})
  tx['groups'].append({'title':f['title'],'status':f['status'],'values':[{'field':v['field'],'value':v['value'],'source':v['provenance']} for v in f['values']]})
 return {'transaction':{'transactions':list(txs.values())}}
