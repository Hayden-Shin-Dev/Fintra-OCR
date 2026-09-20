# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Persisted local inference selection; deployment environment takes priority."""
import json,os
from pathlib import Path

def local_model():
    selected=os.environ.get('FINTRA_LOCAL_CHAT_MODEL','').strip()
    if selected:return selected
    path=Path(__file__).resolve().parents[1]/'config'/'ai-runtime.json'
    if path.exists():
        settings=json.loads(path.read_text('utf-8'))
        selected=settings.get('local_model')
        if isinstance(selected,str) and selected.strip():return selected.strip()
    return 'qwen3.5:4b'
