# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Bounded process-local exact-input cache. Never caches errors or partial responses."""
import copy,hashlib,json,threading,time
_lock=threading.RLock();_values={}
def key(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def get(token):
    with _lock:
        entry=_values.get(token)
        if entry and time.monotonic()-entry[0]<1800:return copy.deepcopy(entry[1])
        _values.pop(token,None)
def put(token,value):
    with _lock:
        if len(_values)>=128:_values.pop(next(iter(_values)))
        _values[token]=(time.monotonic(),copy.deepcopy(value))
