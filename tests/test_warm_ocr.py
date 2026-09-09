import io
import json
from types import SimpleNamespace
from fintraocr import warm_ocr, web


def test_worker_reuses_model_and_reports_failure(tmp_path,monkeypatch):
    import fintraocr.ocr
    initialized=[]
    class FakeEngine:
        def __init__(self,*args): initialized.append(args)
        def extract(self,files,*args):
            if files==['bad']: raise ValueError('decode failure')
            return SimpleNamespace(model_dump_json=lambda **kwargs:'{}')
    monkeypatch.setattr(fintraocr.ocr,'PaddleEngine',FakeEngine)
    paths=[]
    for i in range(3):
        folder=tmp_path/str(i);folder.mkdir()
        request=folder/'request.json'
        request.write_text(json.dumps({'folder':str(folder),'files':['bad'] if i==2 else ['valid'],'settings':{'lang':'en','device':'cpu','profile':'medium','max_side':2400,'enhance':False}}))
        paths.append(json.dumps(str(request)))
    monkeypatch.setattr(warm_ocr.sys,'stdin',io.StringIO('\n'.join(paths)))
    warm_ocr.main()
    assert len(initialized)==1
    assert not json.loads((tmp_path/'0/ocr-timing.json').read_text())['model_reused']
    assert json.loads((tmp_path/'1/ocr-timing.json').read_text())['model_reused']
    failure=json.loads((tmp_path/'2/ocr-done.json').read_text())
    assert not failure['ok'] and 'decode failure' in failure['error']


def test_semantic_job_releases_warm_gpu_before_mapping(monkeypatch):
    import threading
    calls=[]
    monkeypatch.setattr(web,'stop_warm_ocr',lambda:calls.append('release'))
    monkeypatch.setattr(web,'run_stage',lambda job,stage:calls.append(stage))
    monkeypatch.setattr(web,'update',lambda *args,**kwargs:None)
    web.run_job({'cancel':threading.Event(),'settings':{'mode':'full','mapping_strategy':'semantic'}})
    assert calls==['release','ocr','mapping']


def test_fast_job_uses_warm_ocr_and_same_mapping_worker(monkeypatch):
    import threading
    calls=[]
    monkeypatch.setattr(web,'run_warm_ocr',lambda job:calls.append('warm'))
    monkeypatch.setattr(web,'run_stage',lambda job,stage:calls.append(stage))
    monkeypatch.setattr(web,'update',lambda *args,**kwargs:None)
    web.run_job({'cancel':threading.Event(),'settings':{'mode':'full','mapping_strategy':'fast'}})
    assert calls==['warm','mapping']
