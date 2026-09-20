# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Local SQLite accounts. Passwords are salted scrypt digests, never plaintext."""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager


class Accounts:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, username TEXT NOT NULL UNIQUE, salt TEXT NOT NULL, digest TEXT NOT NULL, created REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def digest(password, salt):
        return hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()

    def migrate(self, legacy_path):
        """Import the shared account once; return its immutable id for old records."""
        with self.connect() as db:
            row = db.execute("SELECT value FROM metadata WHERE key='legacy_owner'").fetchone()
            if row:
                return row['value']
            if not Path(legacy_path).exists():
                return None
            account = json.loads(Path(legacy_path).read_text('utf-8'))
            uid = secrets.token_hex(16)
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', (uid, account['name'], account['name'].casefold(), account['salt'], account['hash'], time.time()))
            db.execute("INSERT INTO metadata VALUES ('legacy_owner',?)", (uid,))
            return uid

    def register(self, name, password):
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{3,32}', name.strip()):
            raise ValueError('아이디는 영문, 숫자, 밑줄, 하이픈으로 3~32자 입력하세요.')
        if not isinstance(password, str) or not 10 <= len(password) <= 128:
            raise ValueError('비밀번호는 10~128자 입력하세요.')
        name = name.strip()
        salt = secrets.token_hex(16)
        uid = secrets.token_hex(16)
        digest = self.digest(password, salt)
        try:
            with self.connect() as db:
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', (uid, name, name.casefold(), salt, digest, time.time()))
        except sqlite3.IntegrityError:
            raise ValueError('이미 사용 중인 아이디입니다.') from None
        return {'user_id': uid, 'name': name}

    def authenticate(self, name, password):
        if not isinstance(name, str) or not isinstance(password, str) or not 1 <= len(password) <= 128 or len(name) > 128:
            return None
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (name.strip().casefold(),)).fetchone()
        digest = self.digest(password, row['salt'] if row else '0' * 32)
        if row and hmac.compare_digest(digest, row['digest']):
            return {'user_id': row['id'], 'name': row['name']}
        return None
