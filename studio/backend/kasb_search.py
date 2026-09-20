# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Hybrid search over licensed paragraph records; exact lookup never imports this."""
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import threading
import time
from kasb_kb import Store

_lock=threading.Lock()

@lru_cache(maxsize=1)
def local_embedder():
    home=Path(os.environ.get('LOCALAPPDATA',''))/'Fintra'
    candidates=sorted((home/'versions').glob('*/FintraStandards/fintra_standards/search.py'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not candidates:raise FileNotFoundError('installed_fintra_standards_embedding_runtime_missing')
    package=candidates[0].parents[1]
    sys.path.insert(0,str(package))
    from fintra_standards.search import embedder
    return embedder(package/'data/processed',download=False)

def vector(text):
    with _lock:return next(iter(local_embedder().embed([text]))).tolist()

def prepare(paragraphs):
    """Split only an overlong paragraph, retaining its identity and section."""
    model=local_embedder();out=[]
    for p in paragraphs:
        pending=[p['content']];pieces=[]
        while pending:
            text=pending.pop(0)
            # CPUEmbedding explicitly rejects >512 tokens. Retry by splitting, not truncating.
            try:v=vector('passage: '+text)
            except ValueError as exc:
                if '512' not in str(exc) or len(text)<2:raise
                middle=len(text)//2;pending[:0]=[text[:middle],text[middle:]];continue
            pieces.append((text,v))
        offset=sum(1 for row in out if row['paragraph']==p['paragraph'])
        out.extend(dict(p,content=text,chunk_index=offset+i,vector=v,embedding_model='multilingual-e5-small-fp16') for i,(text,v) in enumerate(pieces))
    return out

def search(question,filters=None,store=None,embed=vector):
    from chat_retrieval import tokens,rerank
    from rank_bm25 import BM25L
    from standards_metadata import matches
    import numpy as np
    t=time.perf_counter();store=store or Store();filters=filters or {};rows=[]
    with store.connect() as db:
        for record in db.execute('SELECT d.metadata AS doc,p.metadata AS para FROM documents d JOIN paragraphs p ON p.doc_id=d.id'):
            row=dict(json.loads(record['doc']),**json.loads(record['para']))
            candidate=dict(row,standard_id=row.get('standard_number'),text=row['content'],title=row.get('standard_name',''),topic=row.get('topic',row.get('section','')))
            candidate['_standards_metadata']={key:candidate.get(key) for key in ('standard_id','standard_name','paragraph','section','topic')}
            if matches(candidate,filters) and row.get('vector'):rows.append(candidate)
    if not rows:return {'passages':[],'method':'official_hybrid','candidate_count':0,'retrieval_seconds':time.perf_counter()-t,'reranking_seconds':0,'filters':filters}
    bm25=BM25L([tokens(r['text']) for r in rows]);lexical=bm25.get_scores(tokens(question))
    query=np.asarray(embed('query: '+question),dtype='float32');vectors=np.asarray([r['vector'] for r in rows],dtype='float32')
    dense=vectors@query;score={}
    for ranks in (np.argsort(-lexical)[:30],np.argsort(-dense)[:30]):
        for rank,i in enumerate(ranks):score[int(i)]=score.get(int(i),0)+1/(60+rank+1)
    candidates=[]
    for i in sorted(score,key=score.get,reverse=True)[:30]:
        row=rows[i];candidates.append(dict(row,id=row['id']+':'+row['paragraph']+':'+str(row['chunk_index']),scores={'cosine':float(dense[i])}))
    retrieval=time.perf_counter()-t;t=time.perf_counter();ranked=rerank(question,candidates,5)
    # Relevance gate precedes authority ordering: an unrelated standard cannot outrank a relevant Q&A.
    rank={'kifrs_standard':0,'kasb_qna':1,'internal_accounting_case':2}
    ranked.sort(key=lambda r:(rank.get(r['source_type'],3),-r['rerank_score']))
    passages=[]
    for row in ranked:
        md={k:v for k,v in row.items() if k not in ('vector','text','content','scores')}
        passages.append({'id':row['id'],'title':f"K-IFRS 제{row.get('standard_number','')}호 {row.get('standard_name','')} · 문단 {row['paragraph']}",
            'text':row['text'],'metadata':md,'source':row['source_url'],'source_type':row['source_type'],'framework':'K-IFRS','score':row['rerank_score']})
    return {'passages':passages,'candidate_count':len(candidates),'method':'official_hybrid','filters':filters,'retrieval_seconds':retrieval,'reranking_seconds':time.perf_counter()-t}
