"""Extract target images only, without trusting ZIP paths or document instructions."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile

TARGETS = {"1.상업송장":"commercial_invoice", "2.포장명세서":"packing_list", "3.선하증권":"bill_of_lading"}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("zip");parser.add_argument("--output",default="data/sample")
    args=parser.parse_args();root=Path(args.output).resolve();manifest=[]
    with ZipFile(args.zip) as archive:
        for entry in archive.infolist():
            parts=entry.filename.split("/")
            kind=next((v for k,v in TARGETS.items() if k in parts),None)
            if not kind or "01.원천데이터" not in parts or not entry.filename.lower().endswith((".png",".jpg",".jpeg")): continue
            # Only generated directory + basename are used. Do not extractall.
            name=Path(parts[-1]).name
            target=(root/kind/name).resolve()
            if not target.is_relative_to(root): raise ValueError("Unsafe archive path")
            if entry.file_size > 50_000_000: raise ValueError("Oversized sample")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.read(entry))
            manifest.append({"path":str(target),"expected_type":kind,"archive_entry":entry.filename})
    (root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Extracted {len(manifest)} images")
if __name__ == "__main__": main()
