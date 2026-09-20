# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Run each existing module in its own environment; exchange JSON only."""
import json,sys
from pathlib import Path
kind,request_path,output_path=sys.argv[1:]
request=json.loads(Path(request_path).read_text(encoding='utf-8'))
if kind=='audit':
    from fintra_audit import analyze
    result=analyze(request['ledger'],request['documents'],config=request['config'])
elif kind=='report':
    from fintra_standards.report import create_report
    result=create_report(request['result'],request['path'],request['analysis_id'])
else:raise ValueError('Unknown stage')
Path(output_path).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
