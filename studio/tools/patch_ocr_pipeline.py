# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Install only scheduling changes; preserve the model and extraction code."""
import os
from pathlib import Path
root=Path(os.environ['LOCALAPPDATA'])/'Fintra/versions/0.6.1-preview/FintraOCR/fintraocr'
p=root/'web.py'
original=p.read_text('utf-8')
backup=Path(__file__).resolve().parents[1]/'tests/runtime-baseline/web.py'
backup.parent.mkdir(parents=True,exist_ok=True)
if 'MAPPING_POOL' in original:raise SystemExit('Scheduling patch already installed')
backup.write_text(original,'utf-8')
source=original.replace('POOL = ThreadPoolExecutor(max_workers=1)','POOL = ThreadPoolExecutor(max_workers=1)\nMAPPING_POOL = ThreadPoolExecutor(max_workers=1)')
source=source.replace('def run_job(job, mapping_only=False):', '''def finish_mapping(job):
    try:
        if job["cancel"].is_set(): raise RuntimeError("Cancelled")
        run_stage(job, "mapping")
        update(job,status="complete",finished=time.time())
    except Exception as e:
        update(job,status="cancelled" if job["cancel"].is_set() else "failed",error=str(e),finished=time.time())


def run_job(job, mapping_only=False):''')
source=source.replace('            stop_warm_ocr()  # Release VRAM before Ollama inference.', '            MAPPING_POOL.submit(lambda: None).result()  # Drain shared-GPU mappings before changing model policy.\n            stop_warm_ocr()  # Release VRAM before Ollama inference.')
source=source.replace('        if job["settings"]["mode"]=="full": run_stage(job,"mapping")', '''        if job["settings"]["mode"]=="full":
            if job["settings"].get("model")=="qwen3.5:4b" and os.environ.get("FINTRA_OCR_PIPELINE","1")=="1":
                update(job,status="mapping_queued")
                MAPPING_POOL.submit(finish_mapping,job)
                return
            MAPPING_POOL.submit(lambda: None).result()
            run_stage(job,"mapping")''')
compile(source,str(p),'exec')
p.write_text(source,'utf-8')
print('Installed OCR/mapping scheduling pipeline; model, resolution, prompts and grounding unchanged.')
