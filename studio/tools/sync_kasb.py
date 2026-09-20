# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Metadata discovery is safe by default; --ingest requires documented rights."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from kasb_sync import discover,sync_documents,extract_pdf,qna_catalogue,fetch,QNA_URL
from kasb_kb import Store
from kasb_search import prepare

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ingest',action='store_true');parser.add_argument('--rights',type=Path)
    parser.add_argument('--pdftotext');parser.add_argument('--output',type=Path,default=Path('data/accounting-kb/catalogue.json'))
    args=parser.parse_args();documents=discover();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(documents,ensure_ascii=False,indent=2),encoding='utf-8')
    qna=qna_catalogue(fetch(QNA_URL).decode('utf-8'))
    args.output.with_name('qna-catalogue.json').write_text(json.dumps(qna,ensure_ascii=False,indent=2),encoding='utf-8')
    result={'catalogued_standards':len(documents),'qna_first_page':len(qna),'mode':'metadata_only','content_downloaded':0}
    if args.ingest:
        rights=json.loads(args.rights.read_text(encoding='utf-8')) if args.rights else {}
        store=Store();result.update(sync_documents(documents,store,rights,lambda blob:extract_pdf(blob,args.pdftotext),indexer=prepare))
        result.update(store.counts());result['mode']='ingestion_attempt'
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
