import pytest
from fintraocr.semantic import OllamaSelector,wire_schema
from fintraocr.mapping import MappingEngine
from test_pipeline import document
@pytest.mark.parametrize("quote,expected",[(None,"AZ-729"),("AZ-729","AZ-729"),("fabricated",None)])
def test_exact_quotes(monkeypatch,quote,expected):
    replies=iter([{"document_type":"commercial_invoice","score":.99,"evidence":["COMMERCIAL INVOICE"]},{"fields":{"invoice_number":{"refs":[{"id":"value","quote":quote}],"labels":[],"score":.99,"ambiguous":False}},"items":[]}])
    selector=OllamaSelector("fake");monkeypatch.setattr(selector,"request",lambda *a:next(replies))
    r=MappingEngine(selector).map(document());assert r.fields["invoice_number"].value==expected
def test_wire_ids_constrained():
    s=wire_schema("commercial_invoice",["a","b"])
    ref=s["properties"]["fields"]["properties"]["invoice_number"]["anyOf"][0]["properties"]["refs"]
    assert ref["minItems"]==1 and ref["items"]["properties"]["id"]["enum"]==[None,"a","b"]


def test_empty_document_abstains(monkeypatch):
    d=document();d.tokens=[]
    selector=OllamaSelector("fake")
    monkeypatch.setattr(selector,"request",lambda *a:(_ for _ in ()).throw(AssertionError("No model call needed")))
    assert selector.select(d).document_type=="unknown"

def test_repeated_quote_abstains(monkeypatch):
    d=document();d.tokens.append(d.tokens[1].model_copy(update={"id":"another"}))
    replies=iter([{"document_type":"commercial_invoice","score":.99,"evidence":["COMMERCIAL INVOICE"]},{"fields":{"invoice_number":{"refs":[{"id":None,"quote":"AZ-729"}],"labels":["COMMERCIAL INVOICE"],"score":.99,"ambiguous":False}},"items":[]}])
    selector=OllamaSelector("fake");monkeypatch.setattr(selector,"request",lambda *a:next(replies))
    assert MappingEngine(selector).map(d).fields["invoice_number"].value is None

def test_duplicate_quote_hint(monkeypatch):
    d=document();d.tokens.append(d.tokens[1].model_copy(update={"id":"another"}))
    replies=iter([{"document_type":"commercial_invoice","score":.99,"evidence":["COMMERCIAL INVOICE"]},{"fields":{"invoice_number":{"refs":[{"id":2,"quote":"AZ-729"}],"labels":["COMMERCIAL INVOICE"],"score":.99,"ambiguous":False}},"items":[]}])
    selector=OllamaSelector("fake");monkeypatch.setattr(selector,"request",lambda *a:next(replies))
    field=MappingEngine(selector).map(d).fields["invoice_number"]
    assert field.value=="AZ-729" and field.evidence[0].token_id=="another"
