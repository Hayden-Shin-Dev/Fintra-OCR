# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Role-based local structured inference; no external API or weight download."""
import json,time,os
from urllib.request import Request,urlopen
from model_config import local_model
from answer_budget import remaining,scope,CURRENT,receive

def role_model(role):
    return os.environ.get('FINTRA_'+role.upper()+'_MODEL') or local_model()

def structured(role,system,data,schema):
    import inference_cache
    model=role_model(role)
    options={'temperature':0,'num_ctx':8192,'num_predict':100 if role=='router' else 180 if role=='validator' else 500}
    # Keep the small classifier off the constrained GPU; it must not evict the reasoning model.
    if role=='router' and model != local_model():options['num_gpu']=0
    payload={'model':model,'stream':False,'think':False,'keep_alive':'30m','format':schema,'options':options,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(data,ensure_ascii=False)}]}
    key=inference_cache.key({'policy':'conversation-v2','role':role,'payload':payload})
    hit=inference_cache.get(key)
    if hit is not None:return hit
    limit=remaining(10 if role=='router' else 10 if role=='validator' else 27)
    current=CURRENT.get();cancel=current[1] if current else None
    with scope(cancel,seconds=limit):
        r=receive('http://127.0.0.1:18434/api/chat',payload,{'Content-Type':'application/json'},urlopen,Request)
    if r.get('done_reason')=='length':raise ValueError('structured_output_truncated')
    value=json.loads(r['message']['content'])
    if not isinstance(value,dict):raise ValueError('invalid_structured_output')
    inference_cache.put(key,value);return value
