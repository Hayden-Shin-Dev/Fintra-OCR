# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Authenticated public SSE smoke check, no browser session extraction."""
import json,time,sys
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
base=json.loads((ROOT/'team-preview/state.json').read_text('utf-8'))['url']
credentials=json.loads((ROOT/'team-preview/credentials.json').read_text('utf-8'))
headers={'Content-Type':'application/json','X-Fintra-Request':'1','Origin':base}
with urlopen(Request(base+'/api/login',json.dumps({'name':credentials['name'],'password':credentials['password']}).encode(),headers),timeout=15) as r:
    headers['Cookie']=r.headers['Set-Cookie'].split(';')[0];r.read()
start=time.perf_counter()
question=sys.argv[1] if len(sys.argv)>1 else '지금 무슨 단계야?'
with urlopen(Request(base+'/api/support',json.dumps({'question':question}).encode(),headers),timeout=15) as r:task=json.load(r)
events=[];event=None
with urlopen(Request(base+'/api/support/'+task['id']+'/events',headers=headers),timeout=65) as r:
    mime=r.headers['Content-Type']
    for line in r:
        text=line.decode('utf-8').strip()
        if text.startswith('event:'):event=text[6:].strip()
        elif text.startswith('data:'):
            data=json.loads(text[5:]);events.append({'event':event,'seconds':time.perf_counter()-start,'data':data})
            if event=='done':break
out={'question':question,'content_type':mime,'events':events,'total_seconds':time.perf_counter()-start}
target=ROOT/'tests/chat-architecture/http-stream.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'content_type':mime,'token_events':sum(e['event']=='token' for e in events),'first_token':next((e['seconds'] for e in events if e['event']=='token'),None),'total_seconds':out['total_seconds'],'final_status':events[-1]['data'].get('status') if events else None},ensure_ascii=False))
