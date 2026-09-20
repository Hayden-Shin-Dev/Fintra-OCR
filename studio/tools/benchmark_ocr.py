# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Real inference benchmark. No expected values are passed to the engine."""
import argparse,json,os,sys,time,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('FINTRA_OCR_URL','http://127.0.0.1:18768')
os.environ.setdefault('FINTRA_WEB_DATA',str(ROOT/'tests/speed-runs'))
sys.path.insert(0,str(ROOT/'backend'))
import engine
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('images',nargs='+');args=p.parse_args()
settings={'lang':'en','audit':{}}
t=time.perf_counter()
jid=engine.new_job([('documents',Path(f).name,Path(f).read_bytes()) for f in args.images],settings)
while engine.JOBS[jid]['status'] in ('queued','running'):time.sleep(.25)
job=engine.JOBS[jid];folder=engine.DATA/jid
record={'label':args.label,'job_id':jid,'wall_seconds':round(time.perf_counter()-t,3),'status':job['status'],'timings':job['timings'],'failures':job['failures']}
(ROOT/'tests'/('speed-'+args.label+'.json')).write_text(json.dumps(record,indent=2,ensure_ascii=False),'utf-8')
print(json.dumps(record,ensure_ascii=False),flush=True)
