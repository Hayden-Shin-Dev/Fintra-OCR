# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Temporary second URL for comparing routes to the same authenticated app."""
import json,re,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'team-preview'
guard=socket.socket()
guard.bind(('127.0.0.1',8789));guard.listen(1)
config=DATA/'comparison-origin.json'
stop=DATA/'stop-comparison.request';stop.unlink(missing_ok=True)
logpath=DATA/'comparison-tunnel.log'
with logpath.open('w',encoding='utf-8') as log:
    child=subprocess.Popen([str(ROOT/'tools/bin/cloudflared.exe'),'--no-autoupdate','tunnel','--url','http://127.0.0.1:8781'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline=time.monotonic()+90
        origin=None
        while time.monotonic()<deadline:
            if child.poll() is not None:raise RuntimeError('Comparison tunnel stopped')
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',logpath.read_text('utf-8',errors='replace'))
            if match:origin=match.group();break
            time.sleep(.5)
        if not origin:raise RuntimeError('No comparison URL received')
        expires=time.time()+86400
        temp=config.with_suffix('.tmp')
        temp.write_text(json.dumps({'origin':origin,'expires':expires}),'utf-8');temp.replace(config)
        print(origin,flush=True)
        while child.poll() is None and time.time()<expires and not stop.exists():time.sleep(1)
    finally:
        config.unlink(missing_ok=True)
        child.terminate()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait()
        guard.close()
