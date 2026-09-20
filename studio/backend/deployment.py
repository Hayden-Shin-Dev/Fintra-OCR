# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Exact public-origin allowlist; forwarded headers never grant access."""
import os,json,time,re
from pathlib import Path
from urllib.parse import urlsplit

def public_origin():
    value=os.environ.get('FINTRA_PUBLIC_ORIGIN','').rstrip('/')
    if value:
        u=urlsplit(value)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.path or u.query or u.fragment:
            raise ValueError('FINTRA_PUBLIC_ORIGIN must be an HTTPS origin')
    return value

def comparison_origin():
    # Only the local comparison launcher may authorize one temporary hostname.
    folder=os.environ.get('FINTRA_WORKSPACE_DATA')
    if not folder or not public_origin():return None
    try:
        record=json.loads((Path(folder)/'comparison-origin.json').read_text('utf-8'))
        origin=record['origin']
        if record['expires']>time.time() and re.fullmatch(r'https://[a-z0-9-]+\.trycloudflare\.com',origin):return origin
    except (OSError,ValueError,KeyError,TypeError):pass
    return None

def allowed_hosts(port):
    origins={x for x in (public_origin(),comparison_origin()) if x}
    return {f'127.0.0.1:{port}',f'localhost:{port}'} | {urlsplit(x).netloc for x in origins}

def valid_origin(origin,port):
    public=public_origin()
    if public:return origin==public or (origin is not None and origin==comparison_origin())
    return origin in {None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
