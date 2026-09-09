"""Local test UI and asynchronous inference jobs. Cloud inference can replace worker boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from typing import Literal

ROOT = Path(os.environ.get("FINTRA_DATA_DIR", Path.cwd()/"data"/"ui")).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
SAMPLE_ROOT = Path(__file__).resolve().parents[1]/"data"/"sample"
app = FastAPI(title="FintraOCR", version="0.2.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
POOL = ThreadPoolExecutor(max_workers=1)
JOBS = {}
WARM_PROCESS = None
WARM_KEY = None
WARM_LOG = None
LOCK = threading.Lock()

class Settings(BaseModel):
    profile: Literal["medium","mobile"] = "medium"
    device: Literal["auto","gpu:0","cpu"] = "auto"
    lang: Literal["en","korean"] = "en"
    mode: Literal["full","ocr"] = "full"
    mapping_strategy: Literal['fast','semantic'] = 'semantic'
    model: str = Field(default="qwen3.5:4b",min_length=1,max_length=100)
    max_side: int = Field(default=2400,ge=640,le=4000)
    enhance: bool = False
    date_order: Literal["DMY","MDY"] | None = None
    decimal_separator: Literal[".",","] | None = None

@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin=request.headers.get("origin")
    if request.method not in {"GET","HEAD","OPTIONS"} and origin and origin != str(request.base_url).rstrip("/"):
        return JSONResponse({"detail":"Cross-origin writes are not allowed"},status_code=403)
    return await call_next(request)

@app.get("/")
def index(): return FileResponse(Path(__file__).parent/"static"/"index.html")

@app.get("/api/health")
def health():
    try:
        with urlopen("http://127.0.0.1:11434/api/tags",timeout=3) as r: models=[m["name"] for m in json.load(r)["models"]]
        ollama=True
    except Exception: models=[];ollama=False
    return {"ollama":ollama,"models":models,"default_model":"qwen3.5:4b","default_profile":"medium"}

@app.get('/api/schemas')
def schemas():
    from .schemas import catalog,ALIASES
    return {'schema_version':'2.0','documents':catalog(),'aliases':ALIASES}

@app.get("/api/samples")
def samples():
    manifest=SAMPLE_ROOT/"manifest.json"
    if not manifest.exists(): return []
    return [{"id":i,"name":Path(e["path"]).name,"type":e["expected_type"]} for i,e in enumerate(json.loads(manifest.read_text(encoding="utf-8")))]

def get_job(jid):
    if jid not in JOBS: raise HTTPException(404,"Job not found")
    return JOBS[jid]

def update(job, **values):
    with LOCK:
        job.update(values)
        public={k:v for k,v in job.items() if k not in {"process","cancel"}}
        (ROOT/job["id"]/"job.json").write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding="utf-8")

def run_stage(job, stage):
    folder=ROOT/job["id"]
    update(job,status=stage,stage_started=time.time())
    with (folder/(stage+".log")).open("w",encoding="utf-8") as log:
        process=subprocess.Popen([sys.executable,"-m","fintraocr.worker",str(folder/"request.json"),stage],stdout=log,stderr=log,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        job["process"]=process
        started=time.monotonic()
        while process.poll() is None:
            if job["cancel"].is_set() or time.monotonic()-started > 900:
                process.terminate();process.wait(timeout=15)
                raise RuntimeError("Cancelled" if job["cancel"].is_set() else "Inference exceeded 15 minute limit")
            time.sleep(.3)
        job["process"]=None
        if process.returncode: raise RuntimeError((folder/(stage+".log")).read_text(encoding="utf-8",errors="replace")[-1800:])

def stop_warm_ocr():
    global WARM_PROCESS, WARM_KEY, WARM_LOG
    if WARM_PROCESS is not None:
        if WARM_PROCESS.poll() is None:
            WARM_PROCESS.terminate()
            try: WARM_PROCESS.wait(timeout=15)
            except subprocess.TimeoutExpired:
                WARM_PROCESS.kill(); WARM_PROCESS.wait(timeout=5)
        if WARM_PROCESS.stdin: WARM_PROCESS.stdin.close()
    if WARM_LOG is not None: WARM_LOG.close()
    WARM_PROCESS = WARM_KEY = WARM_LOG = None


def run_warm_ocr(job):
    global WARM_PROCESS, WARM_KEY, WARM_LOG
    folder = ROOT/job["id"]
    settings = job["settings"]
    key = tuple(settings[k] for k in ("lang", "device", "profile"))
    update(job, status="ocr", stage_started=time.time())
    if WARM_PROCESS is None or WARM_PROCESS.poll() is not None or WARM_KEY != key:
        stop_warm_ocr()
        WARM_LOG = (ROOT/"warm-ocr.log").open("a", encoding="utf-8")
        WARM_PROCESS = subprocess.Popen([sys.executable, "-m", "fintraocr.warm_ocr"],
            stdin=subprocess.PIPE, stdout=WARM_LOG, stderr=WARM_LOG, text=True,
            encoding="utf-8", creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        WARM_KEY = key
    job["process"] = WARM_PROCESS
    try:
        WARM_PROCESS.stdin.write(json.dumps(str(folder/"request.json"))+"\n")
        WARM_PROCESS.stdin.flush()
        started = time.monotonic()
        done = folder/"ocr-done.json"
        while not done.exists():
            if job["cancel"].is_set(): raise RuntimeError("Cancelled")
            if time.monotonic()-started > 900: raise RuntimeError("Inference exceeded 15 minute limit")
            if WARM_PROCESS.poll() is not None: raise RuntimeError("OCR worker exited; inspect data/ui/warm-ocr.log")
            time.sleep(.1)
        outcome = json.loads(done.read_text(encoding="utf-8"))
        if not outcome["ok"]: raise RuntimeError(outcome["error"])
    except Exception:
        stop_warm_ocr()
        raise
    finally:
        job["process"] = None


def run_job(job, mapping_only=False):
    try:
        if job["cancel"].is_set(): raise RuntimeError("Cancelled")
        if job["settings"].get("mapping_strategy", "semantic") == "semantic" and job["settings"].get("model","qwen2.5:7b") != "qwen3.5:4b":
            stop_warm_ocr()  # Release VRAM before Ollama inference.
            if not mapping_only: run_stage(job,"ocr")
        elif not mapping_only:
            run_warm_ocr(job)
        if job["settings"]["mode"]=="full": run_stage(job,"mapping")
        update(job,status="complete",finished=time.time())
    except Exception as e: update(job,status="cancelled" if job["cancel"].is_set() else "failed",error=str(e),finished=time.time())

def new_job(settings):
    jid=uuid.uuid4().hex;folder=ROOT/jid;folder.mkdir()
    job={"id":jid,"status":"queued","created":time.time(),"settings":settings.model_dump(),"files":[],"error":None,"cancel":threading.Event(),"process":None}
    JOBS[jid]=job
    return job,folder

def submit(job):
    folder=ROOT/job["id"]
    (folder/"request.json").write_text(json.dumps({"folder":str(folder),"settings":job["settings"],"files":job["files"]}),encoding="utf-8")
    update(job,status="queued");POOL.submit(run_job,job)
    return {"id":job["id"]}

@app.post("/api/jobs")
async def upload(files: list[UploadFile]=File(...), settings: str=Form("{}")):
    try: config=Settings.model_validate_json(settings)
    except ValueError as e: raise HTTPException(422,str(e))
    if not 1 <= len(files) <= 10: raise HTTPException(400,"Upload 1 to 10 pages of one document")
    # Validate all files before creating an inference job.
    import cv2,numpy as np
    validated=[];total=0
    for f in files:
        blob=await f.read(32*1024*1024+1);total+=len(blob)
        if total > 32*1024*1024: raise HTTPException(413,"Maximum upload size is 32 MB")
        decoded=cv2.imdecode(np.frombuffer(blob,np.uint8),cv2.IMREAD_COLOR)
        if decoded is None: raise HTTPException(400,"Only PNG/JPEG/BMP/WebP images are supported")
        if decoded.shape[0]*decoded.shape[1] > 40_000_000: raise HTTPException(413,"Image exceeds 40 megapixels")
        validated.append(cv2.imencode(".png",decoded)[1].tobytes())
    job,folder=new_job(config)
    for i,blob in enumerate(validated):
        path=folder/f"page-{i+1}.png";path.write_bytes(blob);job["files"].append(str(path))
    return submit(job)

@app.post("/api/samples/{sample_id}")
def run_sample(sample_id: int, settings: Settings):
    manifest=SAMPLE_ROOT/"manifest.json"
    if not manifest.exists(): raise HTTPException(404,"Samples are not installed")
    entries=json.loads(manifest.read_text(encoding="utf-8"))
    if not 0 <= sample_id < len(entries): raise HTTPException(404,"Sample not found")
    source=Path(entries[sample_id]["path"]).resolve()
    if not source.is_relative_to(SAMPLE_ROOT.resolve()): raise HTTPException(400,"Invalid sample path")
    job,folder=new_job(settings);path=folder/"page-1.png";path.write_bytes(source.read_bytes());job["files"]=[str(path)]
    return submit(job)

@app.get("/api/jobs/{jid}")
def status(jid: str):
    job=get_job(jid);folder=ROOT/jid
    result={k:v for k,v in job.items() if k not in {"process","cancel","files"}}
    result["pages"]=len(job["files"])
    result['trace_available']=(folder/'mapping-trace.json').exists()
    result['timings']={}
    for timing in folder.glob('*-timing.json'):
        try: result['timings'].update(json.loads(timing.read_text(encoding='utf-8')))
        except ValueError: pass
    for key,name in [("ocr","ocr.json"),("result","result.json")]:
        if (folder/name).exists(): result[key]=json.loads((folder/name).read_text(encoding="utf-8"))
    return result

@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: str):
    job=get_job(jid)
    if job["status"] not in {"complete","failed","cancelled"}: job["cancel"].set()
    return {"status":"cancellation_requested"}

@app.post("/api/jobs/{jid}/remap")
def remap(jid: str, settings: Settings):
    old=get_job(jid)
    if not (ROOT/jid/"ocr.json").exists(): raise HTTPException(409,"OCR has not completed")
    config=settings.model_copy(update={"mode":"full"})
    job,folder=new_job(config)
    for i,file in enumerate(old["files"]):
        dst=folder/f"page-{i+1}.png";dst.write_bytes(Path(file).read_bytes());job["files"].append(str(dst))
    (folder/"ocr.json").write_bytes((ROOT/jid/"ocr.json").read_bytes())
    (folder/"request.json").write_text(json.dumps({"folder":str(folder),"settings":job["settings"],"files":job["files"]}),encoding="utf-8")
    update(job,status="queued");POOL.submit(run_job,job,True)
    return {"id":job["id"]}

@app.get("/api/jobs/{jid}/image/{page}")
def page_image(jid: str,page:int):
    job=get_job(jid)
    if not 1<=page<=len(job["files"]): raise HTTPException(404,"Page not found")
    return FileResponse(job["files"][page-1],media_type="image/png")

@app.get("/api/jobs/{jid}/download/{kind}")
def download(jid: str,kind:str):
    get_job(jid)
    if kind not in {"ocr","result","mapping-trace"}: raise HTTPException(404,"Unknown output")
    path=ROOT/jid/(kind+".json")
    if not path.exists(): raise HTTPException(404,"Output is not ready")
    return FileResponse(path,media_type="application/json",filename=f"fintra-{jid[:8]}-{kind}.json")

# Restore completed jobs; a stopped application never claims old work is still running.
for saved in ROOT.glob("*/job.json"):
    try:
        job=json.loads(saved.read_text(encoding="utf-8"))
        if job["status"] not in {"complete","failed","cancelled"}: job.update(status="failed",error="Application restarted during processing")
        job.update(cancel=threading.Event(),process=None);JOBS[job["id"]]=job
    except (ValueError,KeyError): pass
