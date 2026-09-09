"""Reproducible image OCR comparison and grounded field evaluation. Gold is used ONLY after inference."""
import argparse,json,time,hashlib,sys,subprocess,unicodedata,re
from pathlib import Path
from decimal import Decimal,InvalidOperation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def clean(text):return re.sub(r"\s+","",unicodedata.normalize("NFKC",str(text))).casefold()
def distance(a,b):
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        row=[i]
        for j,cb in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=row
    return prev[-1]
def rect(poly):return min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)
def contained(cx,cy,b):return b[0]-4<=cx<=b[2]+4 and b[1]-4<=cy<=b[3]+4

def ocr_metrics(entry,doc):
    oracle=Path(entry["image"]).parent/"oracle.ocr.json"
    if not oracle.exists():return None  # Sample labels are sparse and cannot support full-document CER.
    refs=read(oracle)["tokens"];used=set();errors=0;chars=0;matched=0
    for t in doc["tokens"]:
        box=rect(t["bbox"]);chosen=[]
        for i,g in enumerate(refs):
            b=rect(g["bbox"])
            if i not in used and contained((b[0]+b[2])/2,(b[1]+b[3])/2,box):chosen.append((i,g))
        if not chosen:continue
        chosen.sort(key=lambda x:rect(x[1]["bbox"])[0]);expected=clean(" ".join(x[1]["text"] for x in chosen));actual=clean(t["text"])
        errors+=distance(expected,actual);chars+=len(expected);matched+=len(chosen);used.update(i for i,g in chosen)
    for i,g in enumerate(refs):
        if i not in used:errors+=len(clean(g["text"]));chars+=len(clean(g["text"]))
    return {"region_character_errors":errors,"reference_characters":chars,"region_cer":errors/chars if chars else None,"reference_regions":len(refs),"matched_regions":matched}

def score(gold,result):
    pairs=[]
    for k,v in gold["fields"].items():pairs.append(("fields."+k,v,result.get("fields",{}).get(k,{}).get("value")))
    for i,row in enumerate(gold.get("items",[])):
        actual=result.get("items",[]);actual=actual[i] if i<len(actual) else {}
        for k,v in row.items():pairs.append((f"items.{i}.{k}",v,actual.get(k,{}).get("value")))
    expected=sum(a is not None for _,a,b in pairs);predicted=sum(b is not None for _,a,b in pairs)
    correct=sum(a==b and a is not None for _,a,b in pairs)
    return {"type_correct":gold["document_type"]==result.get("document_type"),"annotated_fields":len(pairs),
        "expected_non_null":expected,"predicted_non_null":predicted,"correct_non_null":correct,
        "precision":correct/predicted if predicted else None,"recall":correct/expected if expected else None,
        "exact_match_including_null":sum(a==b for _,a,b in pairs)/len(pairs),
        "false_non_null":sum(a is None and b is not None for _,a,b in pairs),
        "extra_rows":max(0,len(result.get("items",[]))-len(gold.get("items",[]))),
        "errors":[{"field":k,"expected":a,"actual":b} for k,a,b in pairs if a!=b]}

def main():
    p=argparse.ArgumentParser();p.add_argument("stage",choices=["ocr","map","report"]);p.add_argument("--profile",default="medium",choices=["medium","mobile"])
    p.add_argument("--model",default="qwen2.5:7b");p.add_argument("--ids",nargs="*");args=p.parse_args()
    entries=read(ROOT/"data/holdout/manifest.json");entries=[e for e in entries if not args.ids or e["id"] in args.ids]
    out=ROOT/"outputs/benchmark";out.mkdir(parents=True,exist_ok=True)
    if args.stage=="ocr":
        from fintraocr.ocr import PaddleEngine
        started=time.monotonic();engine=PaddleEngine("en","gpu:0",args.profile);init=time.monotonic()-started
        engines={"en":engine}
        for e in entries:
            lang=e.get("language","en")
            if lang not in engines:engines[lang]=PaddleEngine(lang,"gpu:0",args.profile)
            engine=engines[lang]
            dest=out/e["id"];dest.mkdir(exist_ok=True);started=time.monotonic()
            try:
                doc=engine.extract([e["image"]],max_side=2400);secs=time.monotonic()-started
                (dest/(args.profile+".ocr.json")).write_text(doc.model_dump_json(indent=2),encoding="utf-8")
                metrics={"profile":args.profile,"gpu":"RTX 4050 Laptop 6GB","init_seconds":init,"inference_seconds":secs,"tokens":len(doc.tokens),"quality":ocr_metrics(e,doc.model_dump())}
                (dest/(args.profile+".metrics.json")).write_text(json.dumps(metrics,indent=2),encoding="utf-8")
                print(e["id"],args.profile,round(secs,2),flush=True)
            except Exception as exc:
                (dest/(args.profile+".error.txt")).write_text(str(exc),encoding="utf-8");print(e["id"],"ERROR",str(exc),flush=True)
    if args.stage=="map":
        from fintraocr.models import OCRDocument
        from fintraocr.semantic import OllamaSelector
        from fintraocr.mapping import MappingEngine
        engine=MappingEngine(OllamaSelector(args.model))
        for e in entries:
            dest=out/e["id"];doc=OCRDocument.model_validate(read(dest/(args.profile+".ocr.json")));started=time.monotonic()
            tag=args.profile+"."+args.model.replace(":","-")
            try:
                result=engine.map(doc);seconds=time.monotonic()-started
                (dest/(tag+".result.json")).write_text(result.model_dump_json(indent=2),encoding="utf-8")
                metrics=score(read(e["gold"]),result.model_dump());metrics["mapping_seconds"]=seconds;metrics["model"]=args.model
                metrics["engine_sha256"]=hashlib.sha256((ROOT/"fintraocr/semantic.py").read_bytes()).hexdigest()
                (dest/(tag+".score.json")).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
                print(e["id"],"precision",metrics["precision"],"recall",metrics["recall"],round(seconds,1),flush=True)
            except Exception as exc:
                (dest/(tag+".error.txt")).write_text(str(exc),encoding="utf-8");print(e["id"],"ERROR",str(exc),flush=True)
    if args.stage=="report":
        result={"cases":[],"warning":"Small synthetic challenge + reserved Sample.zip images; not population accuracy. Exact field values including case/punctuation. Region CER removes case/whitespace and is synthetic-only."}
        for e in entries:
            dest=out/e["id"];case={"id":e["id"],"family":e["family"],"split":e.get("split","unspecified")}
            for path in dest.glob("*.metrics.json"):case[path.stem]=read(path)
            for path in dest.glob("*.score.json"):case[path.stem]=read(path)
            for path in dest.glob("*.error.txt"):case[path.stem]=path.read_text(encoding="utf-8")
            result["cases"].append(case)
        (out/"report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
