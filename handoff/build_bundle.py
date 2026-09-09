"""Build a minimal teammate bundle from tested source; no datasets or fonts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "handoff-dist"
BUNDLE = OUT / "FintraOCR_Team_Handoff"
SOURCE_SHA = "86f6668468d1ce65c6249ebfc8dfd3889d670cdd"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def fixture(dtype, title, values):
    from fintraocr.models import Page, Token, OCRDocument, Span, Selection, Proposal
    from fintraocr.mapping import MappingEngine
    tokens = [Token(id="title", page=1, text=title, bbox=[(20,20),(550,20),(550,50),(20,50)], confidence=1)]
    selections = {}
    for index, (name, label, value) in enumerate(values):
        text = label + ": " + value
        y = 80 + index * 45
        tid = "field" + str(index)
        tokens.append(Token(id=tid, page=1, text=text, bbox=[(20,y),(650,y),(650,y+30),(20,y+30)], confidence=1))
        selections[name] = Selection(spans=[Span(token_id=tid, start=len(label)+2, end=len(text))], label_spans=[Span(token_id=tid, start=0, end=len(label))], score=1, method="integration_fixture")
    doc = OCRDocument(pages=[Page(page=1,width=800,height=1200,source="synthetic-contract-fixture")],tokens=tokens,engine="synthetic:no-ocr-inference")
    proposal = Proposal(document_type=dtype,type_score=1,type_evidence=[Span(token_id="title",start=0,end=len(title))],fields=selections,items=[])
    result = MappingEngine().map(doc,proposal=proposal)
    for name in selections:
        assert result.fields[name].status == "accepted", (dtype, name, result.fields[name])
    write_json(BUNDLE / "examples" / f"{dtype}.ocr.json", doc.model_dump())
    write_json(BUNDLE / "examples" / f"{dtype}.proposal.json", proposal.model_dump())
    write_json(BUNDLE / "examples" / f"{dtype}.result.json", result.model_dump())


def test_counts(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {name: sum(int(s.attrib.get(name, "0")) for s in suites) for name in ("tests", "failures", "errors", "skipped")}


def main():
    OUT.mkdir(exist_ok=True)
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)  # generated staging directory only, never user data
    BUNDLE.mkdir()
    for name in ("fintra_ocr_client.py", "setup_handoff.py", "doctor.py"):
        shutil.copy2(ROOT / "handoff" / name, BUNDLE / name)
    shutil.copy2(ROOT / "handoff/README_TEAM.md", BUNDLE / "README_TEAM.md")
    shutil.copy2(ROOT / "docs/CURRENT_VALIDATION.md", BUNDLE / "SOURCE_VALIDATION.md")
    source = BUNDLE / "source"
    source.mkdir()
    shutil.copytree(ROOT / "fintraocr", source / "fintraocr", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "pyproject.toml", source / "pyproject.toml")
    shutil.copytree(ROOT / "dist", BUNDLE / "dist")
    shutil.copytree(ROOT / "handoff-validation", BUNDLE / "validation")
    (BUNDLE / "runtime-constraints.txt").write_text("# Selected versions recorded by the original GPU environment, not a CI inference claim.\npaddleocr==3.7.0\npaddlex==3.7.2\nnumpy==2.2.6\ntokenizers==0.23.2\npydantic==2.13.5\n", encoding="utf-8")
    (BUNDLE / "Install-GPU.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\npython setup_handoff.py --runtime gpu-cu126 --pull-model\r\nif errorlevel 1 (echo Setup failed. Read the error above. & pause & exit /b 1)\r\npause\r\n', encoding="ascii")
    (BUNDLE / "Install-CPU.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\npython setup_handoff.py --runtime cpu --pull-model\r\nif errorlevel 1 (echo Setup failed. Read the error above. & pause & exit /b 1)\r\npause\r\n', encoding="ascii")
    (BUNDLE / "Start-Review.cmd").write_text('@echo off\r\ncd /d "%~dp0"\r\nif not exist ".fintra-venv\\Scripts\\python.exe" (echo Run installation first. & pause & exit /b 1)\r\nset "FINTRA_DATA_DIR=%~dp0jobs-ui"\r\necho Open http://127.0.0.1:8768 after server startup.\r\n".fintra-venv\\Scripts\\python.exe" -m uvicorn fintraocr.web:app --host 127.0.0.1 --port 8768\r\nif errorlevel 1 pause\r\n', encoding="ascii")
    from fintraocr.schemas import catalog, ALIASES
    from fintraocr.models import Result, OCRDocument, Proposal
    write_json(BUNDLE / "schemas/field_catalog.json", catalog())
    write_json(BUNDLE / "schemas/compatibility_aliases.json", ALIASES)
    write_json(BUNDLE / "schemas/result.schema.json", Result.model_json_schema())
    write_json(BUNDLE / "schemas/ocr_document.schema.json", OCRDocument.model_json_schema())
    write_json(BUNDLE / "schemas/proposal.schema.json", Proposal.model_json_schema())
    fixture("commercial_invoice", "COMMERCIAL INVOICE", [("invoice_number","Invoice Number","DEMO-I-001"),("issue_date","Issue Date","2026-01-31"),("seller","Seller","Example Seller Ltd"),("buyer","Buyer","Example Buyer Ltd"),("currency","Currency","EUR"),("total_amount","Total Amount","1250.50")])
    fixture("packing_list", "PACKING LIST", [("packing_list_number","Packing List Number","DEMO-P-001"),("issue_date","Issue Date","2026-01-31"),("exporter","Exporter","Example Exporter Ltd"),("consignee","Consignee","Example Receiver Ltd"),("gross_weight","Gross Weight","125.50"),("weight_unit","Weight Unit","kg"),("total_packages","Total Packages","10")])
    fixture("bill_of_lading", "BILL OF LADING", [("bill_of_lading_number","Bill of Lading Number","DEMO-B-001"),("shipper","Shipper","Example Shipper Ltd"),("consignee","Consignee","Example Receiver Ltd"),("notify_party","Notify Party","Example Notify Ltd"),("vessel","Vessel","Example Vessel"),("gross_weight","Gross Weight","125.50")])
    (BUNDLE / "examples/README.txt").write_text("All three examples are synthetic contract fixtures. Proposal replay does not run OCR or a language model and is not evidence of extraction accuracy. Empty items arrays do not test table recognition. Actual field definitions are in schemas/field_catalog.json.\n", encoding="utf-8")
    smoke = '''from pathlib import Path
import tempfile
from fintra_ocr_client import FintraOCRClient
root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="fintra-offline-smoke-") as work:
    client = FintraOCRClient(work_root=work)
    for dtype in ("commercial_invoice", "packing_list", "bill_of_lading"):
        run = client.map_saved(root / "examples" / (dtype + ".ocr.json"), proposal_json=root / "examples" / (dtype + ".proposal.json"))
        assert run.result["document_type"] == dtype
        assert run.result["schema_version"] == "2.0"
        assert any(v["status"] == "accepted" for v in run.result["fields"].values())
        print(dtype, "contract replay PASS")
print("OFFLINE ONLY: real OCR, GPU and live Ollama were not tested by this command.")
'''
    (BUNDLE / "smoke_handoff.py").write_text(smoke, encoding="utf-8")
    wheels = list((BUNDLE / "dist").glob("*.whl"))
    assert len(wheels) == 1
    # Install built wheel outside the checkout, proving assets and imports do
    # not accidentally depend on editable-install source paths.
    with tempfile.TemporaryDirectory(prefix="fintra-wheel-test-") as temporary:
        base = Path(temporary)
        envdir = base / "env"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(envdir)
        py = envdir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(py), "-m", "pip", "install", "--no-deps", "--force-reinstall", str(wheels[0])], check=True, cwd=base)
        probe = "import fintraocr,sys; from pathlib import Path; from tokenizers import Tokenizer; p=Path(fintraocr.__file__).resolve(); assert str(p).startswith(str(Path(sys.prefix).resolve())), p; Tokenizer.from_file(str(p.parent/'assets/qwen35-tokenizer.json')); print('wheel package and tokenizer PASS',p)"
        subprocess.run([str(py), "-c", probe], check=True, cwd=base)
        subprocess.run([str(py), str(BUNDLE / "smoke_handoff.py")], check=True, cwd=base)
    counts = test_counts(ROOT / "handoff-validation/tests.xml")
    integration = test_counts(ROOT / "handoff-validation/integration.xml")
    assert counts["failures"] == counts["errors"] == integration["failures"] == integration["errors"] == 0
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    write_json(BUNDLE / "validation/summary.json", {
        "source_commit": SOURCE_SHA, "handoff_commit": commit,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "repository_tests": counts, "integration_tests": integration,
        "wheel_install_and_tokenizer": "passed", "three_document_contract_replay": "passed",
        "actual_gpu_ocr_rerun": False, "actual_ollama_inference_rerun": False,
        "new_document_accuracy_measured_here": False,
        "decision": "integration_candidate_not_generalization_certified",
        "field_counts": {k:{"document":len(v["fields"]),"item":len(v["items"])} for k,v in catalog().items()},
    })
    # Transparent, non-exhaustive static scan. Domain vocabularies and relative
    # geometry thresholds are allowed; this is not a generalization proof.
    import re
    findings = []
    for name in ("compact.py", "grounded.py", "mapping.py", "layout.py", "domain.py", "normalize.py", "schemas.py"):
        for number, line in enumerate((ROOT / "fintraocr" / name).read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"IMG_OCR_|semantic_gold|C:\\\\Users|sample_id|case_id", line):
                findings.append({"file":name,"line":number,"text":line.strip()})
    write_json(BUNDLE / "validation/static_scan.json", {"scope":"selected runtime modules only","findings":findings,"warning":"No matches would not prove absence of hardcoding or guarantee generalization. Domain vocabulary and heuristic thresholds remain."})
    for file in BUNDLE.rglob("*"):
        if file.is_file():
            assert file.suffix.lower() not in {".ttf", ".otf", ".woff", ".woff2", ".env"}
    hashes = {p.relative_to(BUNDLE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(BUNDLE.rglob("*")) if p.is_file()}
    write_json(BUNDLE / "MANIFEST_SHA256.json", hashes)
    target = OUT / "FintraOCR_Team_Handoff.zip"
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(BUNDLE.rglob("*")):
            if path.is_file():archive.write(path,path.relative_to(OUT))
    (OUT / "FintraOCR_Team_Handoff.sha256").write_text(hashlib.sha256(target.read_bytes()).hexdigest()+"  "+target.name+"\n",encoding="ascii")
    print(json.dumps({"bundle":str(target),"bytes":target.stat().st_size,"source":SOURCE_SHA,"tests":counts,"integration":integration},indent=2))


if __name__ == "__main__":
    main()
