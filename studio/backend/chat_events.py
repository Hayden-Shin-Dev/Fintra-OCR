# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Bounded replayable SSE event journals. Ownership is checked by HTTP handlers."""
import threading,time,json
LOCK=threading.Condition();JOURNALS={}
def publish(key,event,data):
    with LOCK:
        if key not in JOURNALS:
            if len(JOURNALS)>=200:JOURNALS.pop(next(iter(JOURNALS)))
            JOURNALS[key]=[]
        rows=JOURNALS[key]
        rows.append((len(rows)+1,event,data));LOCK.notify_all()
def read(key,after=0,timeout=1):
    with LOCK:
        rows=[r for r in JOURNALS.get(key,[]) if r[0]>after]
        if not rows:LOCK.wait(timeout);rows=[r for r in JOURNALS.get(key,[]) if r[0]>after]
        return rows
def serve(handler,key,state):
    from urllib.parse import urlparse,parse_qs
    query=parse_qs(urlparse(handler.path).query)
    if 'after' in query:
        try:cursor=max(0,int(query['after'][0]))
        except ValueError:return handler.reply({'error':'Invalid event cursor'},400)
        rows=read(key,cursor,timeout=0)
        task=state() or {}
        return handler.reply({'events':[{'id':seq,'event':event,'data':data} for seq,event,data in rows],
                              'done':task.get('status') not in ('queued','running'),'status':task.get('status')})
    handler.protocol_version='HTTP/1.1'
    handler.send_response(200)
    handler.send_header('Content-Type','text/event-stream; charset=utf-8')
    handler.send_header('Cache-Control','no-cache, no-transform')
    handler.send_header('X-Accel-Buffering','no');handler.send_header('Transfer-Encoding','chunked');handler.send_header('Connection','close');handler.end_headers()
    def send(payload):
        handler.wfile.write(f'{len(payload):X}\r\n'.encode()+payload+b'\r\n');handler.wfile.flush()
    try:
        send(b': connected\n\n')
        try:cursor=max(0,int(handler.headers.get('Last-Event-ID','0')))
        except ValueError:cursor=0
        deadline=time.monotonic()+65
        while time.monotonic()<deadline:
            for seq,event,data in read(key,cursor):
                send(f'id: {seq}\nevent: {event}\ndata: {json.dumps(data,ensure_ascii=False)}\n\n'.encode());cursor=seq
            task=state()
            if task and task.get('status') not in ('running','queued'):
                send(('event: done\ndata: '+json.dumps(task,ensure_ascii=False)+'\n\n').encode());return
            send(b': heartbeat\n\n')
    except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError,OSError):pass
    finally:
        try:handler.wfile.write(b'0\r\n\r\n');handler.wfile.flush()
        except OSError:pass
        handler.close_connection=True
