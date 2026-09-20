# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Start the web workspace; reuse the existing engines without copying model weights."""
import os,json,sys,subprocess,time
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parent
home=Path(os.environ.get('FINTRA_HOME',str(Path(os.environ['LOCALAPPDATA'])/'Fintra')))
config=json.loads((home/'current.json').read_text('utf-8'))
release=home/'versions'/config['version'];runtime=home/'runtimes'/config['runtime_id']/'python.exe'
os.environ.update(FINTRA_WEB_PORT=os.environ.get('FINTRA_WEB_PORT','8780'),FINTRA_WEB_DATA=os.environ.get('FINTRA_WEB_DATA',str(ROOT/'data'/'analyses')),FINTRA_OCR_URL='http://127.0.0.1:18768',FINTRA_STANDARDS_URL='http://127.0.0.1:18769',FINTRA_AUDIT_HOME=str(release/'FintraAudit'),FINTRA_AUDIT_PYTHON=str(runtime),FINTRA_STANDARDS_PYTHON=str(runtime),FINTRA_RELEASE_ROOT=str(release),FINTRA_AUDIT_TESTSET=str(release/'samples'),PYTHONUTF8='1')
try:urlopen('http://127.0.0.1:18773/state',timeout=2)
except Exception:
    subprocess.Popen([str(runtime),str(home/'launch.py')],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
sys.path.insert(0,str(ROOT/'backend'))
from server import serve
serve()
