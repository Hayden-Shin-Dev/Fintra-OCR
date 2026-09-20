# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""HTTP transfer optimizations without changing application payloads."""
import gzip
import hashlib

def encode_payload(body, mime, accept_encoding):
    encodings = {}
    for entry in accept_encoding.lower().split(','):
        parts = entry.strip().split(';')
        quality = 1.0
        for part in parts[1:]:
            if part.strip().startswith('q='):
                try: quality = float(part.strip()[2:])
                except ValueError: quality = 0.0
        encodings[parts[0]] = quality
    compressible = mime.startswith('text/') or any(t in mime for t in ('json', 'javascript', 'svg'))
    if len(body) >= 1024 and compressible and encodings.get('gzip', encodings.get('*', 0)) > 0:
        compressed = gzip.compress(body, compresslevel=1, mtime=0)
        if len(compressed) < len(body):
            return compressed, 'gzip'
    return body, None

def content_etag(body):
    return 'W/"' + hashlib.sha256(body).hexdigest() + '"'
