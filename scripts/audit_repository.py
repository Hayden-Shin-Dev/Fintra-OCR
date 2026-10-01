# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Bounded public-repository checks; never print matched secret values."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    'github_token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})'),
    'aws_access_key': re.compile(rb'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'provider_key': re.compile(rb'sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{40,}'),
}
FORBIDDEN = re.compile(r'(^|/)(?:\.env(?:\..+)?|credentials\.json|account\.json|users\.sqlite3|team-preview|node_modules|\.venv)(?:/|$)|\.(?:pem|key|sqlite3?|db|gguf|safetensors|pdf|hwp|hwpx)$', re.I)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def findings(data):
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(data)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    paths = [p for p in git('ls-files', '-z').decode('utf-8').split('\0') if p]
    problems = []
    for path in paths:
        if FORBIDDEN.search(path) and not path.endswith('.env.example'):
            problems.append({'path': path, 'reason': 'private_or_restricted_file'})
        for kind in findings((ROOT / path).read_bytes()):
            problems.append({'path': path, 'reason': kind})
    count = 0
    if args.history:
        objects = git('rev-list', '--objects', '--all').splitlines()
        names = {line.split(b' ', 1)[0]: line.split(b' ', 1)[-1].decode('utf-8', errors='replace') for line in objects}
        process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output, _ = process.communicate(b'\n'.join(names) + b'\n')
        if process.returncode:
            raise RuntimeError('Cannot inspect Git history')
        offset = 0
        while offset < len(output):
            end = output.index(b'\n', offset)
            oid, kind, size = output[offset:end].split()
            start = end + 1
            data = output[start:start + int(size)]
            offset = start + int(size) + 1
            if kind == b'blob':
                count += 1
                for finding in findings(data):
                    problems.append({'object': oid.decode(), 'path': names[oid], 'reason': finding})
    print(json.dumps({'tracked_files': len(paths), 'history_blobs_scanned': count, 'findings': problems,
                      'scope': 'Selected credential patterns and current tracked private-file paths only; not a security certification.'}, ensure_ascii=False, indent=2))
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
