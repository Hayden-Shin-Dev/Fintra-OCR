# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Verify the running preview through its public HTTPS address without exposing credentials."""
import http.cookiejar
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'team-preview'
url = json.loads((ROOT / 'state.json').read_text())['url']
credentials = json.loads((ROOT / 'credentials.json').read_text())
jar = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def call(path, data=None, origin=None, authenticated=True):
    headers = {'X-Fintra-Request': '1'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if origin:
        headers['Origin'] = origin
    req = urllib.request.Request(url + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
    try:
        opener = client if authenticated else urllib.request.build_opener()
        with opener.open(req, timeout=40) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())

checks = {}
checks['anonymous_analyses'] = call('/api/analyses', authenticated=False)[0]
checks['wrong_origin'] = call('/api/login', credentials, 'https://wrong.invalid')[0]
checks['missing_origin'] = call('/api/login', credentials)[0]
checks['login'] = call('/api/login', credentials, url)[0]
checks['cookie_secure'] = bool(list(jar)) and all(cookie.secure for cookie in jar)
checks['session'] = call('/api/session')
checks['readiness'] = call('/api/readiness')
checks['analyses'] = call('/api/analyses')
(ROOT / 'deployment-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
assert checks['anonymous_analyses'] == 401, checks
assert checks['wrong_origin'] == checks['missing_origin'] == 403, checks
assert checks['login'] == 200 and checks['cookie_secure'], checks
assert checks['session'][1]['authenticated'], checks
assert checks['readiness'][0] == checks['analyses'][0] == 200, checks
print(json.dumps(checks, ensure_ascii=True))
