from pathlib import Path
import json
import subprocess
import sys
import pytest
from handoff.fintra_ocr_client import FintraOCRClient, FintraOCRError, OCRConfig

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "examples/synthetic.ocr.json"
PROPOSAL = ROOT / "examples/synthetic.proposal.json"


@pytest.mark.parametrize("changes", [
    {"device": "cuda"}, {"profile": "unknown"}, {"lang": "automatic"},
    {"max_side": 1}, {"max_side": True}, {"model": ""}, {"model": "bad\nmodel"},
    {"date_order": "YMD"}, {"decimal_separator": ";"},
    {"ocr_timeout": 0}, {"mapping_timeout": float("inf")},
])
def test_configuration_rejects_invalid_input(changes):
    with pytest.raises(ValueError):
        OCRConfig(**changes)


def test_real_cli_replay_preserves_contract_and_source(tmp_path):
    before = OCR.read_bytes()
    client = FintraOCRClient(work_root=tmp_path / "한글 공백 작업")
    run = client.map_saved(OCR, proposal_json=PROPOSAL)
    assert run.result["document_type"] == "commercial_invoice"
    assert run.result["schema_version"] == "2.0"
    assert run.result["fields"]["invoice_number"]["status"] == "accepted"
    assert run.result["fields"]["invoice_number"]["evidence"]
    assert "items" in run.result
    assert run.result_path.is_file()
    assert (run.job_dir / "mapping.log").is_file()
    assert not (run.job_dir / "ocr.log").exists()
    assert OCR.read_bytes() == before == run.ocr_path.read_bytes()
    from fintraocr.models import Result
    Result.model_validate(run.result)


def test_independent_jobs_do_not_overwrite(tmp_path):
    client = FintraOCRClient(work_root=tmp_path)
    a = client.map_saved(OCR, proposal_json=PROPOSAL)
    b = client.map_saved(OCR, proposal_json=PROPOSAL)
    assert a.job_dir != b.job_dir
    assert a.result == b.result


def test_unknown_requested_document_type_is_not_accepted(tmp_path):
    client = FintraOCRClient(work_root=tmp_path)
    with pytest.raises(ValueError):
        client.map_saved(OCR, document_type="invoice")


def test_requested_document_mismatch_is_explicit(tmp_path):
    client = FintraOCRClient(work_root=tmp_path)
    result = client.map_saved(OCR, proposal_json=PROPOSAL, document_type="packing_list").result
    assert result["document_type"] == "unknown"
    assert "requested_type_mismatch" in result["issues"]


def test_missing_input_creates_no_job(tmp_path):
    client = FintraOCRClient(work_root=tmp_path / "jobs")
    with pytest.raises(FileNotFoundError):
        client.map_saved(tmp_path / "absent.json")
    assert not client.work_root.exists()


@pytest.mark.parametrize("paths", [[], "one.png"])
def test_image_page_list_required(paths, tmp_path):
    client = FintraOCRClient(work_root=tmp_path)
    with pytest.raises(ValueError):
        client.extract(paths)


def test_bad_json_is_error_not_silent_missing(tmp_path):
    invalid = tmp_path / "broken.json"
    invalid.write_text("not json", encoding="utf-8")
    client = FintraOCRClient(work_root=tmp_path / "jobs")
    with pytest.raises(FintraOCRError) as caught:
        client.map_saved(invalid, proposal_json=PROPOSAL)
    error = caught.value
    assert error.stage == "mapping"
    assert (error.job_dir / "ocr.json").is_file()
    assert (error.job_dir / "error.json").is_file()


def test_timeout_preserves_ocr_and_records_failure(tmp_path, monkeypatch):
    client = FintraOCRClient(work_root=tmp_path)
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(FintraOCRError) as caught:
        client.map_saved(OCR)
    assert caught.value.reason == "timeout"
    assert (caught.value.job_dir / "ocr.json").read_bytes() == OCR.read_bytes()


def test_exact_executable_no_shell_and_stage_order(tmp_path, monkeypatch):
    image = tmp_path / "page with spaces.png"
    image.write_bytes(b"stub: decoder is mocked only in this test")
    client = FintraOCRClient(work_root=tmp_path / "jobs", config=OCRConfig(device="gpu:0"))
    calls = []
    def fake_run(args, **kwargs):
        assert args[:3] == [str(Path(sys.executable).resolve()), "-m", "fintraocr"]
        assert kwargs["shell"] is False
        output = Path(args[args.index("--output") + 1])
        calls.append(args[3])
        if args[3] == "ocr":
            output.write_bytes(OCR.read_bytes())
            assert args[args.index("--device") + 1] == "gpu:0"
        else:
            assert calls == ["ocr", "map"]
            output.write_text(json.dumps({"schema_version": "2.0", "document_type": "unknown", "fields": {}, "items": []}))
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(subprocess, "run", fake_run)
    run = client.extract([image])
    assert calls == ["ocr", "map"]
    assert run.result["document_type"] == "unknown"


def test_ocr_only_does_not_call_mapping(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"stub")
    def fake_run(args, **kwargs):
        assert args[3] == "ocr"
        Path(args[args.index("--output") + 1]).write_bytes(OCR.read_bytes())
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(subprocess, "run", fake_run)
    run = FintraOCRClient(work_root=tmp_path / "jobs").extract([image], ocr_only=True)
    assert run.result is None and run.result_path is None and run.ocr_path.is_file()


def test_schema_ui_matches_engine_catalog():
    from fastapi.testclient import TestClient
    from fintraocr.web import app
    from fintraocr.schemas import catalog
    from fintraocr.models import Result, OCRDocument
    with TestClient(app) as client:
        response = client.get("/api/schemas")
        assert response.status_code == 200
        assert response.json()["documents"] == catalog()
    assert Result.model_json_schema()["type"] == "object"
    assert OCRDocument.model_json_schema()["type"] == "object"
