# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Report annotation documents without a corresponding source in a local corpus.

This measures loaded document-name coverage, not completeness of accounting law.
The corpus is opened read-only. Annotation answers are never promoted to sources.
"""
import argparse,json,sqlite3
from pathlib import Path

def audit(corpus):
    with sqlite3.connect(Path(corpus).resolve().as_uri()+'?mode=ro',uri=True) as db:
        sources={Path(m).stem for m, in db.execute("SELECT member FROM records WHERE kind='source'")}
        annotated={Path(m).stem.rsplit('_QA',1)[0] for m, in db.execute("SELECT member FROM records WHERE kind='annotation'")}
    missing=sorted(annotated-sources)
    return {'source_documents':len(sources),'annotated_documents':len(annotated),
            'missing_source_documents':len(missing),'missing_names':missing,
            'definition':'Annotation filename stems without matching source filename stems in the loaded corpus; not a claim that those sources exist in the original archive.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('corpus');parser.add_argument('output');args=parser.parse_args()
    result=audit(args.corpus);Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print({k:v for k,v in result.items() if k not in ('missing_names','definition')})
