# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Atomic JSON writes tolerant of brief Windows reader/antivirus file locks."""
import json
import time
import uuid
from pathlib import Path

def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        for attempt in range(21):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 20:
                    raise
                time.sleep(.05)
    finally:
        temporary.unlink(missing_ok=True)
