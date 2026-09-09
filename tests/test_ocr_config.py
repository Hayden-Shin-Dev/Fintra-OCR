import sys,types
import pytest
from fintraocr.ocr import PaddleEngine
@pytest.mark.parametrize("lang,profile,expected",[("en","medium","PP-OCRv6_medium_rec"),("korean","medium","korean_PP-OCRv5_mobile_rec"),("en","mobile","en_PP-OCRv5_mobile_rec")])
def test_profile_language(monkeypatch,lang,profile,expected):
    captured={}
    monkeypatch.setitem(sys.modules,"paddle",types.SimpleNamespace(is_compiled_with_cuda=lambda:True))
    monkeypatch.setitem(sys.modules,"paddleocr",types.SimpleNamespace(PaddleOCR=lambda **kwargs:captured.update(kwargs)))
    engine=PaddleEngine(lang,"auto",profile)
    assert captured["text_recognition_model_name"]==expected and engine.device=="gpu:0"
