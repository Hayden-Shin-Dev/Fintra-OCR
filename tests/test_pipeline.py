import json
import pytest
from fintraocr.models import OCRDocument, Page, Token, Proposal, Selection, Span
from fintraocr.mapping import MappingEngine
from fintraocr.normalize import normalize
from fintraocr.semantic import payload, OllamaSelector


def document(title="COMMERCIAL INVOICE", number="AZ-729", confidence=.99, scale=1, shift=0):
    return OCRDocument(pages=[Page(page=1,width=1000*scale,height=1500*scale,source="synthetic")],tokens=[
        Token(id="title",page=1,text=title,bbox=[(10*scale,10*scale),(500*scale,10*scale),(500*scale,40*scale),(10*scale,40*scale)],confidence=.99),
        Token(id="value",page=1,text=number,bbox=[((x+shift)*scale,y*scale) for x,y in [(600,200),(800,200),(800,230),(600,230)]],confidence=confidence)])
def proposal(kind="commercial_invoice",field="invoice_number",text="AZ-729"):
    return Proposal(document_type=kind,type_score=.98,type_evidence=[Span(token_id="title",start=0,end=5)],
        fields={field:Selection(spans=[Span(token_id="value",start=0,end=len(text))],score=.99)})

def test_grounding_and_missing():
    doc=document();result=MappingEngine().map(doc,proposal=proposal())
    assert result.fields["invoice_number"].value=="AZ-729"
    assert result.fields["buyer"].value is None
    ev=result.fields["invoice_number"].evidence[0]
    assert ev.text==doc.tokens[1].text and ev.bbox==doc.tokens[1].bbox
    assert ev.confidence==.99
@pytest.mark.parametrize("scale,shift",[(1,0),(2,0),(3,-400)])
def test_no_absolute_coordinate_dependency(scale,shift):
    result=MappingEngine().map(document(scale=scale,shift=shift),proposal=proposal())
    assert result.fields["invoice_number"].value=="AZ-729"
@pytest.mark.parametrize("title,text",[("상업송장","새거래-42"),("FACTURE COMMERCIALE","FR-991"),("商业发票","CN-19")])
def test_unicode_evidence(title,text):
    doc=document(title,text);p=proposal(text=text);p.type_evidence[0].end=len(title)
    assert MappingEngine().map(doc,proposal=p).fields["invoice_number"].value==text

def test_unknown_token_rejected():
    p=proposal();p.fields["invoice_number"].spans[0].token_id="made_up"
    f=MappingEngine().map(document(),proposal=p).fields["invoice_number"]
    assert f.value is None and f.status=="review"
def test_invented_value_not_in_contract():
    with pytest.raises(ValueError): Selection.model_validate({"spans":[],"score":1,"value":"invented"})
def test_out_of_bounds():
    p=proposal();p.fields["invoice_number"].spans[0].end=100
    assert MappingEngine().map(document(),proposal=p).fields["invoice_number"].value is None
@pytest.mark.parametrize("mode",["ambiguous","score","ocr"])
def test_abstention(mode):
    d=document(confidence=.4 if mode=="ocr" else .99);p=proposal()
    if mode=="ambiguous":p.fields["invoice_number"].ambiguous=True
    if mode=="score":p.fields["invoice_number"].score=.2
    f=MappingEngine().map(d,proposal=p).fields["invoice_number"]
    assert f.value is None and f.raw_text=="AZ-729" and f.evidence

def test_reuse_rejected():
    p=proposal();p.fields["purchase_order_number"]=p.fields["invoice_number"].model_copy(deep=True)
    r=MappingEngine().map(document(),proposal=p)
    assert r.fields["invoice_number"].value is None
    assert r.fields["purchase_order_number"].value is None

def test_wrong_type():
    assert MappingEngine().map(document(),"packing_list",proposal()).document_type=="unknown"
@pytest.mark.parametrize("kind,field",[("commercial_invoice","invoice_number"),("packing_list","packing_list_number"),("bill_of_lading","bill_of_lading_number")])
def test_schema(kind,field):
    r=MappingEngine().map(document(),proposal=proposal(kind,field))
    assert field in r.fields
    assert r.fields[field].value=="AZ-729"
@pytest.mark.parametrize("raw,kind,expected",[("1,234.56","number","1234.56"),("1.234,56","number","1234.56"),("1234","number","1234"),("1 234,56","number","1234.56"),("(25.50)","number","-25.50"),("2026-09-08","date","2026-09-08"),("08 Sep 2026","date","2026-09-08"),("USD","currency","USD"),("kgs","unit","kg"),("  Acme   Ltd. ","party","Acme Ltd.")])
def test_normalize(raw,kind,expected): assert normalize(raw,kind)[0]==expected
@pytest.mark.parametrize("raw,kind",[("1,234","number"),("1.234","number"),("03/04/2026","date"),("2026-02-30","date"),("$","currency"),("USD 200","number"),("1,2,3.00","number")])
def test_ambiguous_normalize(raw,kind): assert normalize(raw,kind)[0] is None

def test_explicit_locale():
    assert normalize("1,234","number",decimal_separator=".")[0]=="1234"
    assert normalize("03/04/2026","date",date_order="DMY")[0]=="2026-04-03"
def test_duplicate_ids():
    d=document().model_dump();d["tokens"].append(d["tokens"][0])
    with pytest.raises(ValueError):OCRDocument.model_validate(d)
def test_relative_payload():
    assert payload(document())["tokens"]==payload(document(scale=2))["tokens"]
def test_no_remote_upload():
    with pytest.raises(ValueError):OllamaSelector("test","https://example.com")
def test_round_trip():
    r=MappingEngine().map(document(),proposal=proposal())
    assert json.loads(r.model_dump_json())["fields"]["invoice_number"]["evidence"][0]["text"]=="AZ-729"
def test_preprocess(tmp_path):
    import cv2,numpy as np
    from fintraocr.ocr import preprocess
    path=tmp_path/"sample.png";cv2.imwrite(str(path),np.full((201,101,3),255,dtype=np.uint8))
    image,size,meta=preprocess(path,100,True)
    assert size==(101,201) and image.shape[:2]==(100,50)
    assert meta["scale_x"]==50/101 and meta["scale_y"]==100/201

def test_rows_and_repeated_header():
    d=document(number="10 20");p=proposal(text="10")
    p.fields={}
    p.items=[{"quantity":Selection(spans=[Span(token_id="value",start=0,end=2)],score=.99)},
             {"quantity":Selection(spans=[Span(token_id="value",start=3,end=5)],score=.99)}]
    r=MappingEngine().map(d,proposal=p)
    assert [row["quantity"].value for row in r.items]==["10","20"]


def test_ollama_contract(monkeypatch):
    import fintraocr.semantic as semantic
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self):
            if "Classify the document" in captured["messages"][0]["content"]:
                content={"document_type":"commercial_invoice","score":.99,"evidence":["COMMERCIAL INVOICE"]}
            else: content={"fields":{"invoice_number":{"refs":[{"id":"value","quote":None}],"labels":[],"score":.99,"ambiguous":False}},"items":[]}
            return json.dumps({"message":{"content":json.dumps(content)}}).encode()
    def open_request(req,timeout):
        captured.update(json.loads(req.data));return Response()
    monkeypatch.setattr(semantic,"urlopen",open_request)
    selected=OllamaSelector("test").select(document())
    assert selected.document_type=="commercial_invoice"
    assert captured["format"]["additionalProperties"] is False
    assert captured["messages"][0]["role"]=="system"
    assert "UNTRUSTED" in captured["messages"][0]["content"]
    assert "tokens" in json.loads(captured["messages"][1]["content"])

def test_context_limit_before_network(monkeypatch):
    import fintraocr.semantic as semantic
    def fail(*args,**kwargs): raise AssertionError("Network must not be called")
    monkeypatch.setattr(semantic,"urlopen",fail)
    with pytest.raises(ValueError,match="context budget"):
        OllamaSelector("test",max_chars=1).select(document())

def test_preprocessed_bbox_back_to_original(tmp_path):
    import cv2,numpy as np
    from fintraocr.ocr import PaddleEngine
    path=tmp_path/"image.png";cv2.imwrite(str(path),np.full((200,100,3),255,dtype=np.uint8))
    class FakeResult:
        json={"res":{"rec_texts":["example"],"rec_scores":[.9],"rec_polys":[[[5,10],[20,10],[20,20],[5,20]]]}}
    class FakeModel:
        def predict(self,image): return [FakeResult()]
    engine=object.__new__(PaddleEngine);engine.model=FakeModel()
    doc=engine.extract([path],max_side=100)
    assert doc.tokens[0].bbox==[(10,20),(40,20),(40,40),(10,40)]
    assert doc.pages[0].width==100


def test_truncated_model_output(monkeypatch):
    import fintraocr.semantic as semantic
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return json.dumps({"done":True,"done_reason":"length","message":{"content":proposal().model_dump_json()}}).encode()
    monkeypatch.setattr(semantic,"urlopen",lambda *args,**kwargs: Response())
    with pytest.raises(ValueError,match="truncated"):
        OllamaSelector("test").select(document())
