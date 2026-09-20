# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Connect existing audit results to the independent standards service."""
import json,os,time
from urllib.request import Request,urlopen

def request(path,data=None):
    from answer_budget import remaining
    remaining(15)
    endpoint=os.environ.get('FINTRA_STANDARDS_URL')
    if not endpoint:raise RuntimeError('회계처리기준 서비스가 연결되지 않았습니다.')
    payload=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
    import inference_cache
    token=inference_cache.key({'standards_endpoint':endpoint,'path':path,'data':data})
    cacheable=path in ('/search','/source') or path.startswith('/sources/')
    if cacheable:
        cached=inference_cache.get(token)
        if cached is not None:return cached
    from answer_budget import remaining
    with urlopen(Request(endpoint+path,payload,{'Content-Type':'application/json','X-Fintra-Request':'1'}),timeout=remaining(15)) as r:result=json.load(r)
    remaining(15)
    if cacheable:inference_cache.put(token,result)
    return result

def run(job,result,save,write_result,cancelled):
    cancelled(job)
    from review_rules import build
    result['review_result']=build(result['audit'])
    result['standards_review']={'status':'complete','findings':[],'retrieval_policy':'on_demand_rule_eligibility','note':'증빙 대조에서 회계기준 적용을 자동 확정하지 않습니다. 조서와 질문의 목적에 맞는 기준만 별도로 조회합니다.'}
    write_result(job,result)
