from pathlib import Path
import subprocess,sys,time,webbrowser,json,os
from urllib.request import urlopen
root=Path(__file__).resolve().parent
port=int(os.environ.get("FINTRA_PORT","8768"))
url=f"http://127.0.0.1:{port}"
def ready():
    try:
        with urlopen(url+"/api/health",timeout=2) as r:return "default_profile" in json.load(r)
    except Exception:return False
if not ready():
    logs=root/"outputs";logs.mkdir(exist_ok=True)
    with (logs/"ui.stdout.log").open("a") as out,(logs/"ui.stderr.log").open("a") as err:
        process=subprocess.Popen([sys.executable,"-m","uvicorn","fintraocr.web:app","--host","127.0.0.1","--port",str(port)],cwd=root,stdout=out,stderr=err,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    for _ in range(30):
        if ready():break
        if process.poll() is not None:raise SystemExit("UI failed to start. See outputs/ui.stderr.log")
        time.sleep(1)
if ready():webbrowser.open(url)
else:raise SystemExit("UI startup timed out. See outputs/ui.stderr.log")
