# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Exact public-origin allowlist; forwarded headers never grant access."""
import os
from urllib.parse import urlsplit

def public_origin():
    value=os.environ.get('FINTRA_PUBLIC_ORIGIN','').rstrip('/')
    if value:
        u=urlsplit(value)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.path or u.query or u.fragment:
            raise ValueError('FINTRA_PUBLIC_ORIGIN must be an HTTPS origin')
    return value

def allowed_hosts(port):
    public=public_origin()
    return {f'127.0.0.1:{port}',f'localhost:{port}'} | ({urlsplit(public).netloc} if public else set())

def valid_origin(origin,port):
    public=public_origin()
    if public:return origin==public
    return origin in {None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
