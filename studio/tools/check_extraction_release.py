# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Fail a release gate on regression, missing evidence, or failed held-out checks."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def assess(equivalence,holdout):
    reasons=[]
    if not equivalence.get('comparison') or not equivalence.get('equal'):reasons.append('Extraction or evidence changed across scheduling modes')
    if not holdout.get('total') or not holdout.get('all_passed'):reasons.append('External-layout extraction checks failed or are missing')
    if holdout.get('run',{}).get('wall_seconds',float('inf'))>=60:reasons.append('External-layout batch exceeded 60 seconds')
    return {'release_ready':not reasons,'reasons':reasons}
if __name__=='__main__':
    eq=json.loads(Path(sys.argv[1]).read_text('utf-8'));hold=json.loads(Path(sys.argv[2]).read_text('utf-8'))
    result=assess(eq,hold)
    (ROOT/'tests/extraction-release-gate.json').write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(result));sys.exit(0 if result['release_ready'] else 1)
