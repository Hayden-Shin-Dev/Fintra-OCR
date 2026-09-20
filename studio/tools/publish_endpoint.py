# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Publish only a public endpoint using the local Git credential manager."""
import base64,json,os,re,subprocess,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError
REPO='Hayden-Shin-Dev/Fintra-OCR'
BRANCH='fintra-live'
PUBLIC_URL='https://hayden-shin-dev.github.io/Fintra-OCR/'

def github_token():
    env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
    process=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,timeout=20,env=env)
    values=dict(line.split('=',1) for line in process.stdout.splitlines() if '=' in line)
    if process.returncode or not values.get('password'):raise RuntimeError('GitHub login is required in Git Credential Manager')
    return values['password']

def github(path,body=None,method=None,token=None):
    token=token or github_token()
    request=Request('https://api.github.com/repos/'+REPO+'/'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'Fintra-link-publisher'})
    with urlopen(request,timeout=20) as response:
        data=response.read()
        return json.loads(data) if data else {}

def endpoint_record(origin,online=True):
    if not re.fullmatch(r'https://[a-z0-9-]+\.trycloudflare\.com',origin):raise ValueError('Only a Cloudflare Quick Tunnel origin is allowed')
    return {'origin':origin,'online':bool(online),'updated_at':int(time.time())}

def publish(origin,online=True):
    record=endpoint_record(origin,online);token=github_token()
    path='contents/endpoint.json'
    current=github(path+'?ref='+BRANCH,token=token)
    previous=json.loads(base64.b64decode(current['content']))
    if previous.get('origin')==origin and previous.get('online')==online:return PUBLIC_URL
    payload={'branch':BRANCH,'sha':current['sha'],'message':'Update Fintra public connection','content':base64.b64encode(json.dumps(record).encode()).decode()}
    github(path,payload,'PUT',token)
    return PUBLIC_URL
