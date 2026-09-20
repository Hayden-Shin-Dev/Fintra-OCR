# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Versioned paragraph store. No network or model calls during exact lookup."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

SOURCE_TYPES = ('kifrs_standard', 'kasb_qna', 'internal_accounting_case')

def default_path():
    return Path(os.environ.get('FINTRA_KASB_DB', str(Path(__file__).resolve().parents[1] / 'data' / 'accounting-kb' / 'kasb.sqlite3')))

def exact_reference(question):
    match = re.search(r'(?<!\d)(1\d{3}|2\d{3})(?:\s*호\s*|\s+|\s*문단\s*)(?:의\s*)?(?:문단\s*)?([A-Z]{0,2}\d{1,3}[A-Z]?)(?!\d)', question, re.I)
    return (match[1], match[2].upper()) if match else None

def split_paragraphs(text, max_chars=1800):
    """Accept explicitly numbered lines; duplicate numbers fail closed (TOC/BC ambiguity)."""
    text = re.sub(r'(?m)^\s*-\s*\d+\s*-\s*$', '', text)
    lines = text.splitlines(); paragraphs=[]; current=None; section=''; seen=set()
    for line in lines:
        s=line.strip()
        if not s: continue
        # Preserve appendix prefixes. Do not interpret inline references as paragraphs.
        m=re.match(r'^((?:[A-Z]{1,2})?\d{1,3}[A-Z]?)\s{2,}(\S.*)$', line.lstrip())
        if not m: m=re.fullmatch(r'((?:[A-Z]{1,2})?\d{1,3}[A-Z]?)', s)
        if m:
            number=m[1]
            if number in seen: raise ValueError('ambiguous_duplicate_paragraph:'+number)
            if current: paragraphs.append(current)
            seen.add(number); current={'paragraph':number,'section':section,'content':m[2] if m.lastindex==2 else ''}
        elif current:
            current['content'] += '\n'+s
        elif len(s)<60 and not re.search(r'목차|저작권|Copyright|IFRS Foundation|제\d+호',s,re.I):
            section=s
    if current: paragraphs.append(current)
    result=[]
    for p in paragraphs:
        body=p['content'].strip()
        if not body: raise ValueError('empty_paragraph:'+p['paragraph'])
        for part,start in enumerate(range(0,len(body),max_chars)):
            result.append(dict(p, content=body[start:start+max_chars], chunk_index=part))
    if not result: raise ValueError('no_unambiguous_numbered_paragraphs')
    return result

class Store:
    def __init__(self,path=None):
        self.path=Path(path or default_path());self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, source_type TEXT NOT NULL, standard_number TEXT,
                version TEXT NOT NULL, content_hash TEXT NOT NULL, metadata TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS paragraphs (
                doc_id TEXT NOT NULL REFERENCES documents(id), paragraph TEXT NOT NULL,
                chunk_index INTEGER NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL,
                PRIMARY KEY(doc_id,paragraph,chunk_index));
              CREATE INDEX IF NOT EXISTS doc_number ON documents(standard_number,source_type);
              CREATE TABLE IF NOT EXISTS failures (created_at TEXT DEFAULT CURRENT_TIMESTAMP, document_id TEXT, reason TEXT);
            ''')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row;return db
    def document(self,identity):
        with self.connect() as db:
            row=db.execute('SELECT * FROM documents WHERE id=?',(identity,)).fetchone()
            return dict(row) if row else None
    def replace(self,document,paragraphs,content_hash):
        if document['source_type'] not in SOURCE_TYPES: raise ValueError('invalid_source_type')
        if not paragraphs: raise ValueError('empty_document')
        # One transaction: parsing/index preparation must finish before this method.
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?)',
                (document['id'],document['source_type'],document.get('standard_number'),document['version'],content_hash,json.dumps(document,ensure_ascii=False)))
            db.execute('DELETE FROM paragraphs WHERE doc_id=?',(document['id'],))
            for p in paragraphs:
                db.execute('INSERT INTO paragraphs VALUES(?,?,?,?,?)',(document['id'],p['paragraph'],p.get('chunk_index',0),p['content'],json.dumps(p,ensure_ascii=False)))
    def failure(self,identity,reason):
        with self.connect() as db:db.execute('INSERT INTO failures(document_id,reason) VALUES(?,?)',(identity,str(reason)[:2000]))
    def exact(self,number,paragraph):
        with self.connect() as db:
            rows=db.execute('''SELECT d.metadata AS doc,p.metadata AS para,p.content,p.chunk_index
                FROM documents d JOIN paragraphs p ON p.doc_id=d.id
                WHERE d.source_type='kifrs_standard' AND d.standard_number=? AND p.paragraph=?
                ORDER BY p.chunk_index''',(str(number),str(paragraph).upper())).fetchall()
        return [dict(json.loads(r['doc']),**json.loads(r['para'])) for r in rows]
    def counts(self):
        with self.connect() as db:
            return {'documents':db.execute('SELECT count(*) FROM documents').fetchone()[0],
                'paragraphs':db.execute('SELECT count(*) FROM (SELECT DISTINCT doc_id,paragraph FROM paragraphs)').fetchone()[0],
                'chunks':db.execute('SELECT count(*) FROM paragraphs').fetchone()[0],
                'failures':[dict(r) for r in db.execute('SELECT * FROM failures ORDER BY created_at DESC LIMIT 100')]}

def exact_lookup(question,path=None):
    ref=exact_reference(question)
    if not ref:return None
    rows=Store(path).exact(*ref)
    passages=[]
    for row in rows:
        passages.append({'id':row['id']+':'+row['paragraph']+':'+str(row['chunk_index']),
            'title':f"K-IFRS 제{row['standard_number']}호 {row['standard_name']} · 문단 {row['paragraph']}",
            'text':row['content'],'metadata':{k:v for k,v in row.items() if k not in ('vector','content')},'source':row['source_url'],'source_type':'kifrs_standard',
            'framework':'K-IFRS','score':1.0})
    return {'passages':passages,'method':'exact_metadata_lookup','filters':{'standard_id':ref[0],'paragraph':ref[1]},
            'retrieval_failure':not bool(rows),'retrieval_seconds':0,'reranking_seconds':0,'candidate_count':len(rows)}
