from pathlib import Path
import sys
import hashlib
import time
import cv2
import numpy as np
from .models import OCRDocument, Page, Token

def preprocess(path, max_side=3000, enhance=False):
    # imdecode handles Windows Unicode filenames. Only uniform scaling changes geometry.
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None: raise ValueError(f"Cannot decode image: {path}")
    h, w = image.shape[:2]
    if max_side < 32: raise ValueError("max_side must be >= 32")
    ratio = min(1.0, max_side / max(h, w))
    if ratio < 1:
        image = cv2.resize(image, (max(1, round(w*ratio)), max(1, round(h*ratio))), interpolation=cv2.INTER_AREA)
    if enhance:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:,:,0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(lab[:,:,0])
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    ph, pw = image.shape[:2]
    return image, (w, h), {"scale_x": pw/w, "scale_y": ph/h, "clahe": enhance,
                           "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}

class PaddleEngine:
    def __init__(self, lang="en", device="auto", profile="medium"):
        from paddleocr import PaddleOCR
        import paddle
        if profile not in {"mobile", "medium"}: raise ValueError("Unknown OCR profile")
        if device == "auto": device = "gpu:0" if paddle.is_compiled_with_cuda() else "cpu"
        if device.startswith("gpu") and not paddle.is_compiled_with_cuda():
            raise RuntimeError("GPU PaddlePaddle is not installed; select CPU or install paddlepaddle-gpu")
        self.profile, self.device = profile, device
        if profile == "medium":
            model_args = {"text_detection_model_name": "PP-OCRv6_medium_det",
                          "text_recognition_model_name": "korean_PP-OCRv5_mobile_rec" if lang == "korean" else "PP-OCRv6_medium_rec"}
        else:
            mobile_rec = {"en": "en_PP-OCRv5_mobile_rec", "korean": "korean_PP-OCRv5_mobile_rec"}
            if lang not in mobile_rec: raise ValueError("mobile profile supports en/korean; use medium for multilingual input")
            model_args = {"text_detection_model_name": "PP-OCRv5_mobile_det", "text_recognition_model_name": mobile_rec[lang]}
        self.model_args = model_args
        self.model = PaddleOCR(**model_args, device=device, cpu_threads=4,
            enable_mkldnn=(sys.platform != "win32"), use_doc_orientation_classify=False,
            use_doc_unwarping=False, use_textline_orientation=True, text_rec_score_thresh=0.0)
    def extract(self, paths, max_side=3000, enhance=False):
        pages, tokens = [], []
        for page_id, path in enumerate(paths, 1):
            image, (w,h), meta = preprocess(path, max_side, enhance)
            meta["models"] = getattr(self,"model_args",{})
            pages.append(Page(page=page_id, width=w, height=h, source=str(Path(path).resolve()), preprocessing=meta))
            results = list(self.model.predict(image))
            if len(results) != 1: raise RuntimeError("Expected one OCR result per input image")
            result = results[0].json
            if isinstance(result, str):
                import json
                result = json.loads(result)
            data = result.get("res", result)
            angles=data.get('textline_orientation_angles',[])
            suspects=[i for i,(angle,score) in enumerate(zip(angles,data['rec_scores'])) if angle==1 and score<0.95]
            audit={'policy':'rotation-disagreement-v1','trigger_count':len(suspects),'seconds':0,'comparisons':[]}
            if suspects:
                started=time.monotonic()
                try:
                    alternate=list(self.model.predict(image,use_textline_orientation=False))[0].json
                    if isinstance(alternate,str):
                        import json
                        alternate=json.loads(alternate)
                    alternate=alternate.get('res',alternate)
                    # Match the same detected polygon, never an array offset or a
                    # document-specific region. Keep both raw recognition outputs.
                    polygon=lambda p:tuple((float(x),float(y)) for x,y in p)
                    alternatives={polygon(p):(text,float(score)) for p,text,score in zip(alternate['rec_polys'],alternate['rec_texts'],alternate['rec_scores'])}
                    for i,angle in enumerate(angles):
                        if angle!=1:continue
                        candidate=alternatives.get(polygon(data['rec_polys'][i]))
                        if candidate is None:continue
                        raw,confidence=candidate
                        take=bool(raw.strip()) and confidence>=float(data['rec_scores'][i])+0.05
                        audit['comparisons'].append({'token_id':f'p{page_id}t{i}','original_text':data['rec_texts'][i],'original_confidence':float(data['rec_scores'][i]),'original_rotation_degrees':180,'alternate_text':raw,'alternate_confidence':confidence,'selected_rotation_degrees':0 if take else 180})
                        if take:data['rec_texts'][i]=raw;data['rec_scores'][i]=confidence
                except Exception as exc:
                    audit['retry_error']={'type':type(exc).__name__,'message':str(exc)}
                audit['seconds']=time.monotonic()-started
            pages[-1].preprocessing['orientation_audit']=audit
            texts, scores, polys = data["rec_texts"], data["rec_scores"], data["rec_polys"]
            if not len(texts) == len(scores) == len(polys): raise RuntimeError("Unaligned OCR output")
            for i, (text, score, poly) in enumerate(zip(texts,scores,polys)):
                tokens.append(Token(id=f"p{page_id}t{i}", page=page_id, text=text,
                    confidence=float(score), bbox=[(float(x)/meta["scale_x"], float(y)/meta["scale_y"]) for x,y in poly]))
        return OCRDocument(pages=pages,tokens=tokens,engine="paddleocr/" + getattr(self,"profile","test") + "/" + getattr(self,"device","test"))
