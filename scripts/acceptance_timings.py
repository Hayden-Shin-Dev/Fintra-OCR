"""Timing-only report; does not inspect unseen mapping predictions."""
import argparse,json,statistics,math
from scripts.azure_acceptance import ROOT

def stats(values):
 if not values:return None
 values=sorted(values)
 return {'count':len(values),'median':statistics.median(values),'p95':values[math.ceil(len(values)*.95)-1],'max':max(values)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--ocr-version',default='ocr-candidate7');p.add_argument('--count',type=int,default=30);a=p.parse_args()
 groups={};failures=[]
 for e in json.loads((ROOT/'data/acceptance/selection.json').read_text(encoding='utf-8'))['entries']:
  if e['ordinal']>a.count:continue
  folder=ROOT/'outputs/acceptance/runs'/e['id'];group=groups.setdefault(e['type'],{'ocr':[],'mapping':[],'sum_separate_stages':[],'ocr_initialization':[]})
  op=folder/a.ocr_version/'ocr-timing.json';mp=folder/a.version/'map-timing.json'
  if not op.exists() or not mp.exists():failures.append({'id':e['id'],'reason':'stage_not_completed'});continue
  o=json.loads(op.read_text());m=json.loads(mp.read_text())
  if m.get('replayed'):raise RuntimeError('Replay timing is not actual model latency')
  group['ocr'].append(o['seconds']);group['mapping'].append(m['seconds']);group['sum_separate_stages'].append(o['seconds']+m['seconds']);group['ocr_initialization'].append(o['initialization_seconds'])
 report={'version':a.version,'ocr_version':a.ocr_version,'scope':'Batch inference, no UI/upload/network/queue latency. Sum of separately measured OCR and mapping is NOT an end-to-end UI measurement. OCR initialization is shared; do not add it once per document. Ollama cold load, if any, is included in mapping.','groups':{k:{stage:stats(values) for stage,values in v.items()} for k,v in groups.items()},'failures':failures}
 out=ROOT/'outputs/acceptance'/('timings-'+a.version+'.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
