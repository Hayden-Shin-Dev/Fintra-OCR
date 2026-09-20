# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Serve only explicitly verified transaction manifests; never construct random groups."""
import hashlib,json,os
from pathlib import Path

ROOT=Path(os.environ.get('FINTRA_AUDIT_TESTSET',str(Path(__file__).resolve().parent.parent/'FintraAuditTestDataset'))).resolve()
TYPES=('commercial_invoice','packing_list','bill_of_lading')

def manifest():
    path=ROOT/'manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'sets':[],'status':'not_prepared'}

def resolve(row,dtype):
    source=row['documents'][dtype]
    path=(ROOT/source['local_path']).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('검증된 원본 이미지가 없습니다.')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:raise ValueError('검증 이후 이미지가 변경되었습니다.')
    return path

def catalog():
    data=manifest();rows=[]
    for row in data.get('sets',[]):
        if row.get('verification_status')!='verified' or row.get('confidence')!='high' or not row.get('matching_evidence'):continue
        try:
            if not row.get('documents') or set(row['documents'])-set(TYPES):continue
            if set(row['documents'])!=set(TYPES) and not row.get('ground_truth_path'):continue
            images=[{'document_type':t,'name':resolve(row,t).name,'url':f"/api/verified-sets/{row['set_id']}/{t}/image"} for t in TYPES if t in row['documents']]
        except (ValueError,KeyError):continue
        rows.append({'set_id':row['set_id'],'label':row.get('label',row['set_id']),'last_run_id':row.get('last_run_id'),'source_split':row['source_split'],'images':images,'matching_evidence':row['matching_evidence']})
    return {'sets':rows,'status':data.get('status'),'message':data.get('message','검증된 동일 거래 세트만 표시합니다.')}

def selected(set_id):
    if set_id not in {r['set_id'] for r in catalog()['sets']}:raise ValueError('검증된 동일 거래 세트가 아닙니다.')
    return next(r for r in manifest()['sets'] if r['set_id']==set_id)

def image(set_id,dtype):
    if dtype not in TYPES:raise ValueError('지원하지 않는 문서 유형입니다.')
    return resolve(selected(set_id),dtype)

def uploads(set_id):
    row=selected(set_id)
    files=[('documents',resolve(row,t).name,resolve(row,t).read_bytes()) for t in TYPES if t in row['documents']]
    if row.get('ledger_path'):
        p=asset(row['ledger_path']);files.insert(0,('ledger','ledger.csv',p.read_bytes()))
    return files

def asset(relative):
    p=(ROOT/relative).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():raise ValueError('테스트 자료 경로가 잘못되었습니다.')
    return p

def ground_truth(set_id):
    row=selected(set_id)
    return json.loads(asset(row['ground_truth_path']).read_text(encoding='utf-8')) if row.get('ground_truth_path') else None
