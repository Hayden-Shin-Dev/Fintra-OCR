# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""One deadline and cancellation signal shared by nested answer calls."""
import time
from contextvars import ContextVar
from contextlib import contextmanager

CURRENT = ContextVar('answer_budget', default=None)

@contextmanager
def scope(cancel=None, seconds=90):
    token = CURRENT.set((time.monotonic()+seconds, cancel))
    try: yield
    finally: CURRENT.reset(token)

def remaining(default=150):
    value = CURRENT.get()
    if value is None: return default
    deadline, cancel = value
    if cancel and cancel.is_set(): raise InterruptedError('답변 생성을 중지했습니다.')
    left = deadline-time.monotonic()
    if left <= 0: raise TimeoutError('답변 준비 시간이 길어져 중단했습니다. 질문 범위를 좁혀 다시 시도해 주세요.')
    return min(default, left)

def receive(endpoint, payload, headers, opener, request_type):
    """Close local streaming response when cancelled, including thinking tokens."""
    import json
    local = endpoint == 'http://127.0.0.1:18434/api/chat'
    streaming = local and CURRENT.get() is not None
    sent = dict(payload, stream=True) if streaming else payload
    with opener(request_type(endpoint,json.dumps(sent).encode(),headers),timeout=remaining()) as response:
        if not streaming:
            value=json.load(response);remaining();return value
        content=[];last=None
        for line in response:
            remaining()
            if not line.strip():continue
            last=json.loads(line)
            if last.get('error'):raise RuntimeError(last['error'])
            content.append(last.get('message',{}).get('content',''))
            if last.get('done'):break
        remaining()
        if not last or not last.get('done'):raise ValueError('AI 연결이 종료되어 답변을 완료하지 못했습니다.')
        return dict(last,message={'content':''.join(content)})
