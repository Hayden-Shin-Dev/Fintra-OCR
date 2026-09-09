import io,json
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from fintraocr import web
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(web,"ROOT",tmp_path)
    monkeypatch.setattr(web.POOL,"submit",lambda *a,**k:None)
    monkeypatch.setattr(web,"run_warm_ocr",lambda job:None)
    return TestClient(web.app)
def png():
    f=io.BytesIO();Image.new("RGB",(200,100),"white").save(f,format="PNG");return f.getvalue()
def test_home(client):
    r=client.get("/");assert r.status_code==200 and "FintraOCR" in r.text
def test_upload(client):
    r=client.post("/api/jobs",files={"files":("test.png",png(),"image/png")},data={"settings":json.dumps({"mode":"ocr"})})
    assert r.status_code==200
    jid=r.json()["id"];status=client.get("/api/jobs/"+jid).json()
    assert status["pages"]==1 and status["status"]=="queued"
    assert client.get(f"/api/jobs/{jid}/image/1").status_code==200
    assert client.get(f"/api/jobs/{jid}/image/2").status_code==404
    assert client.get(f"/api/jobs/{jid}/download/result").status_code==404
    assert client.post(f"/api/jobs/{jid}/cancel").status_code==200
def test_bad_file(client):assert client.post("/api/jobs",files={"files":("bad.png",b"fake","image/png")}).status_code==400
def test_bad_settings(client):
    assert client.post("/api/jobs",files={"files":("a.png",png(),"image/png")},data={"settings":'{"profile":"made_up"}'}).status_code==422
def test_origin(client):assert client.post("/api/jobs",headers={"Origin":"https://evil.example"}).status_code==403
def test_missing_job(client):assert client.get("/api/jobs/not-a-job").status_code==404
def test_sample_bounds(client):assert client.post("/api/samples/-1",json={}).status_code==404

def test_schema_contract_is_the_engine_schema(client):
    from fintraocr.schemas import SCHEMAS,ITEM_SCHEMAS
    data=client.get('/api/schemas').json()
    assert data['schema_version']=='2.0'
    for dtype in SCHEMAS:
        assert set(data['documents'][dtype]['fields'])==set(SCHEMAS[dtype])
        assert set(data['documents'][dtype]['items'])==set(ITEM_SCHEMAS[dtype])

def test_worker_failure_is_terminal_and_visible(client,monkeypatch):
    jid=client.post('/api/jobs',files={'files':('x.png',png(),'image/png')}).json()['id']
    def fail(job,stage):raise RuntimeError('model_not_available')
    monkeypatch.setattr(web,'run_stage',fail)
    web.run_job(web.JOBS[jid])
    data=client.get('/api/jobs/'+jid).json()
    assert data['status']=='failed' and data['finished']>=data['created']
    assert data['error']=='model_not_available'

def test_trace_and_separate_timings_are_available(client):
    jid=client.post('/api/jobs',files={'files':('x.png',png(),'image/png')}).json()['id']
    folder=web.ROOT/jid
    (folder/'ocr-timing.json').write_text(json.dumps({'initialization_seconds':2,'ocr_seconds':3}))
    (folder/'mapping-timing.json').write_text(json.dumps({'mapping_seconds':4}))
    (folder/'mapping-trace.json').write_text(json.dumps({'stage':'label_selection','status':'failed'}))
    data=client.get('/api/jobs/'+jid).json()
    assert data['timings']=={'initialization_seconds':2,'ocr_seconds':3,'mapping_seconds':4}
    assert data['trace_available']
    assert client.get(f'/api/jobs/{jid}/download/mapping-trace').status_code==200
