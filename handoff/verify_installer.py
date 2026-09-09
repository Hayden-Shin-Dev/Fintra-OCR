"""Exercise the actual teammate installer without installing OCR or LLM models."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    started = time.perf_counter()
    wheel = list((ROOT / "dist").glob("fintraocr-*.whl"))
    if len(wheel) != 1:
        raise RuntimeError("Expected one built engine wheel")
    with tempfile.TemporaryDirectory(prefix="fintra-installer-") as temporary:
        package = Path(temporary) / "installer with spaces"
        (package / "dist").mkdir(parents=True)
        shutil.copy2(wheel[0], package / "dist" / wheel[0].name)
        shutil.copy2(ROOT / "handoff/setup_handoff.py", package / "setup_handoff.py")
        shutil.copy2(ROOT / "handoff/fintra_ocr_client.py", package / "fintra_ocr_client.py")
        shutil.copytree(ROOT / "examples", package / "examples")
        subprocess.run([sys.executable, str(package / "setup_handoff.py"), "--runtime", "none"], cwd=package, check=True, timeout=300)
        py = package / ".fintra-venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        code = "from pathlib import Path; import fintraocr,sys; from fintra_ocr_client import FintraOCRClient; from tokenizers import Tokenizer; p=Path(fintraocr.__file__).resolve(); assert str(p).startswith(str(Path(sys.prefix).resolve())); Tokenizer.from_file(str(p.parent/'assets/qwen35-tokenizer.json')); c=FintraOCRClient(work_root='jobs'); r=c.map_saved('examples/synthetic.ocr.json',proposal_json='examples/synthetic.proposal.json'); assert r.result['document_type']=='commercial_invoice'; assert r.result['fields']['invoice_number']['status']=='accepted'; assert r.result['schema_version']=='2.0'; print('ACTUAL INSTALLER + INSTALLED WHEEL + CONTRACT REPLAY PASS')"
        subprocess.run([str(py), "-c", code], cwd=package, check=True, timeout=90)
        # Startup outside the source checkout must not depend on the original
        # user's filesystem or local datasets. UI is not exposed to a network.
        api = "from fastapi.testclient import TestClient; from fintraocr.web import app; from fintraocr.schemas import catalog; c=TestClient(app); r=c.get('/api/schemas'); assert r.status_code==200 and r.json()['documents']==catalog(); assert c.get('/').status_code==200; print('INSTALLED UI/SCHEMA API PASS')"
        subprocess.run([str(py), "-c", api], cwd=package, check=True, timeout=90)
    summary = {"platform": sys.platform, "actual_installer_runtime_none": "passed", "fresh_venv": True,
               "installed_wheel_replay": "passed", "installed_ui_and_schema_api": "passed",
               "source_directory_dependency": False, "gpu_installation_or_inference_tested": False,
               "live_ollama_inference_tested": False, "seconds": round(time.perf_counter()-started, 3)}
    path = ROOT / "handoff-validation/installer.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
