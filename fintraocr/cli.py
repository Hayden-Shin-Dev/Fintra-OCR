import argparse
import json
from pathlib import Path
from .models import OCRDocument, Proposal
from .mapping import MappingEngine
from .schemas import catalog

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="FintraOCR: OCR -> grounded semantic mapping")
    sub = parser.add_subparsers(dest="command",required=True)
    schema = sub.add_parser("schemas"); schema.add_argument("--output",required=True)
    for command in ("ocr","run","map"):
        p = sub.add_parser(command)
        p.add_argument("inputs",nargs="+")
        p.add_argument("--output",required=True)
        if command != "map":
            p.add_argument("--lang",default="en")
            p.add_argument("--device",default="auto")
            p.add_argument("--profile",choices=["mobile","medium"],default="medium")
            p.add_argument("--max-side",type=int,default=3000)
            p.add_argument("--enhance",action="store_true")
        if command != "ocr":
            p.add_argument("--model",help="Installed local Ollama model name")
            p.add_argument("--proposal",help="Replay saved span proposal without calling a model")
            p.add_argument("--document-type",choices=list(catalog()))
            p.add_argument("--date-order",choices=["DMY","MDY"])
            p.add_argument("--decimal-separator",choices=[".",","])
            p.add_argument("--min-score",type=float,default=0.85)
            p.add_argument("--min-ocr",type=float,default=0.70)
    args = parser.parse_args()
    try:
        if args.command == "schemas": write(args.output,catalog()); return
        if args.command != "ocr" and not args.model and not args.proposal:
            parser.error("Specify --model (local Ollama) or --proposal (replay)")
        if args.command == "map":
            if len(args.inputs) != 1: parser.error("map takes exactly one OCR JSON")
            doc = OCRDocument.model_validate_json(Path(args.inputs[0]).read_text(encoding="utf-8"))
        else:
            from .ocr import PaddleEngine
            doc = PaddleEngine(args.lang,args.device,args.profile).extract(args.inputs,args.max_side,args.enhance)
        if args.command == "ocr": write(args.output,doc.model_dump()); return
        # Save OCR before model calls, so an unavailable model never loses extraction work.
        if args.command == "run": write(str(Path(args.output).with_suffix(".ocr.json")),doc.model_dump())
        proposal, selector = None, None
        if args.proposal: proposal = Proposal.model_validate_json(Path(args.proposal).read_text(encoding="utf-8"))
        else:
            from .compact import CompactSelector
            selector = CompactSelector(args.model)
        result = MappingEngine(selector,args.min_score,args.min_ocr,args.date_order,args.decimal_separator).map(doc,args.document_type,proposal)
        write(args.output,result.model_dump())
    except Exception as e:
        parser.exit(1,f"fintraocr: {type(e).__name__}: {e}\n")
if __name__ == "__main__": main()
