# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Isolated password-protected team preview, with an explicitly stoppable tunnel."""
import hashlib,json,os,re,secrets,socket,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent))
from preview_health import exclusive_socket, require_free_port, check_health, tunnel_revoked
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'team-preview';DATA.mkdir(exist_ok=True)
if '--stop' in sys.argv:
    (DATA/'stop.request').touch();print('Team preview stop requested.');raise SystemExit
if '--reload' in sys.argv:
    (DATA/'reload.request').touch();print('Team preview app reload requested.');raise SystemExit
guard=exclusive_socket()
try:guard.bind(('127.0.0.1',8788));guard.listen(1)
except OSError:print('Team preview already running. Read team-preview/access.txt');raise SystemExit
(DATA/'stop.request').unlink(missing_ok=True)
(DATA/'reload.request').unlink(missing_ok=True)
account=DATA/'account.json';credentials=DATA/'credentials.json'
if not account.exists():
    password=secrets.token_urlsafe(20);salt=secrets.token_hex(16)
    account.write_text(json.dumps({'name':'FintraTeam','salt':salt,'hash':hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()}),'utf-8')
    credentials.write_text(json.dumps({'name':'FintraTeam','password':password}),'utf-8')
children=[];logs=[];origin=None;link_published=False
publish_link=os.environ.get('FINTRA_PUBLISH_LINK')=='1'
try:
    require_free_port(8781)
    fixed_origin=os.environ.get('FINTRA_FIXED_ORIGIN','').strip()
    if fixed_origin:
        from urllib.parse import urlsplit
        parsed=urlsplit(fixed_origin)
        if (parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.ts.net')
                or parsed.username or parsed.password or parsed.port or parsed.path or parsed.query or parsed.fragment):
            raise ValueError('Invalid Tailscale public origin')
        origin=fixed_origin
    else:
        tunnel_log=DATA/'tunnel.log';log=tunnel_log.open('w',encoding='utf-8');logs.append(log)
        tunnel=subprocess.Popen([str(ROOT/'tools/bin/cloudflared.exe'),'--no-autoupdate','tunnel','--url','http://127.0.0.1:8781'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);children.append(tunnel)
        deadline=time.monotonic()+90;origin=None
        while time.monotonic()<deadline:
            if tunnel.poll() is not None:raise RuntimeError('Tunnel stopped; inspect team-preview/tunnel.log')
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',tunnel_log.read_text('utf-8',errors='replace'))
            if match:origin=match.group();break
            time.sleep(.5)
        if not origin:raise RuntimeError('Tunnel did not return a URL')
    env={**os.environ,'FINTRA_PUBLIC_ORIGIN':origin,'FINTRA_WEB_PORT':'8781',
         'FINTRA_WORKSPACE_DATA':str(DATA),'FINTRA_WEB_DATA':str(DATA/'analyses'),'FINTRA_ACCOUNT_FILE':str(account)}
    log=(DATA/'app.log').open('w',encoding='utf-8');logs.append(log)
    app=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'run.py')],cwd=str(ROOT),env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);children.append(app)
    for _ in range(60):
        if app.poll() is not None:raise RuntimeError('App stopped; inspect team-preview/app.log')
        try:
            check_health(origin)
            break
        except OSError:time.sleep(.5)
    else:raise RuntimeError('App startup timed out')
    c=json.loads(credentials.read_text('utf-8'))
    (DATA/'access.txt').write_text('Fintra 팀 테스트\n\nURL: '+origin+'\n이름: '+c['name']+'\n비밀번호: '+c['password']+'\n\n회원가입으로 개인 검토 공간을 만들 수 있습니다. 공용 계정 사용자는 기존 팀 자료를 함께 봅니다.\n기존 로컬 문서와 대화는 이 공간에 포함되지 않습니다.\nPC가 켜져 있고 이 실행이 유지되는 동안 사용 가능합니다.\n주소 유지 조건은 사용 중인 연결 방식에 따라 다릅니다.\n중지: 프로젝트의 서버끄기.cmd 실행\n','utf-8')
    (DATA/'state.json').write_text(json.dumps({'url':origin,'provider':'tailscale' if fixed_origin else 'cloudflare','status':'running','manager_pid':os.getpid(),'app_pid':app.pid,'tunnel_pid':None if fixed_origin else tunnel.pid}),'utf-8')
    if publish_link:
        sys.path.insert(0,str(ROOT/'tools'))
        from publish_endpoint import publish,PUBLIC_URL
        (DATA/'public-url.txt').write_text(PUBLIC_URL+'\n','utf-8')
        try:
            publish(origin);link_published=True
            print('Public link: '+PUBLIC_URL,flush=True)
        except Exception as exc:print('Public link update pending: '+type(exc).__name__,flush=True)
    next_publish=time.monotonic()+30
    next_health=time.monotonic()+30
    health_failures=0
    print(origin,flush=True)
    while not (DATA/'stop.request').exists():
        if (DATA/'reload.request').exists():
            (DATA/'reload.request').unlink()
            app.terminate()
            try:app.wait(timeout=10)
            except subprocess.TimeoutExpired:app.kill();app.wait()
            children.remove(app)
            app=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'run.py')],cwd=str(ROOT),env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);children.append(app)
            (DATA/'state.json').write_text(json.dumps({'url':origin,'provider':'tailscale' if fixed_origin else 'cloudflare','status':'running','manager_pid':os.getpid(),'app_pid':app.pid,'tunnel_pid':None if fixed_origin else tunnel.pid}),'utf-8')
        if publish_link and not link_published and time.monotonic()>=next_publish:
            try:publish(origin);link_published=True;print('Public link updated',flush=True)
            except Exception as exc:print('Public link update pending: '+type(exc).__name__,flush=True)
            next_publish=time.monotonic()+30
        if any(p.poll() is not None for p in children):raise RuntimeError('Preview process exited')
        if time.monotonic()>=next_health:
            if not fixed_origin and tunnel_revoked(tunnel_log.read_text('utf-8',errors='replace')):
                raise RuntimeError('Cloudflare tunnel expired; restarting via the Windows service task')
            try:
                check_health(origin,public=True)
                health_failures=0
            except Exception as exc:
                health_failures+=1
                print('Public health failure '+str(health_failures)+': '+type(exc).__name__,flush=True)
                if health_failures>=4:raise RuntimeError('Public connection unavailable; restarting via the Windows service task')
            next_health=time.monotonic()+30
        time.sleep(1)
finally:
    for p in children:
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
    if publish_link and link_published and origin:
        try:publish(origin,online=False)
        except Exception as exc:print('Offline status update failed: '+type(exc).__name__,flush=True)
    for log in logs:log.close()
    (DATA/'state.json').write_text(json.dumps({'status':'stopped'}),'utf-8')
    guard.close()
