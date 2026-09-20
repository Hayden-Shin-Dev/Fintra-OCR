# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Official KASB catalogue adapter. Downloads require recorded source-use rights."""
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from kasb_kb import Store, split_paragraphs

LIST_URL='https://www.kasb.or.kr/front/board/ingAccountingList.do'
QNA_URL='https://www.kasb.or.kr/front/board/List016005.do'
JS_URL='https://www.kasb.or.kr/common/admmgr/js/file/CtitFile-custom.js'

def fetch(url,data=None):
    if urlparse(url).hostname not in ('www.kasb.or.kr','kasb.or.kr'):raise ValueError('non_official_host')
    req=Request(url,data=data,headers={'User-Agent':'Fintra-Knowledge-Sync/1.0','Referer':LIST_URL})
    with urlopen(req,timeout=45) as response:
        if urlparse(response.url).hostname not in ('www.kasb.or.kr','kasb.or.kr'):raise ValueError('unexpected_redirect')
        if 'ipLooker' in response.url:raise PermissionError('KASB_geographic_access_restriction')
        body=response.read(50*1024*1024+1)
        if len(body)>50*1024*1024:raise ValueError('document_too_large')
        return body

def catalogue(html,script):
    # Discover action from the published JS; never assume or synthesize a new API.
    function=re.search(r'function\s+fileDownload\([^)]*\)(.*?)(?=/\*|\Z)',script,re.S)
    action=re.search(r'action\s*:\s*[\"\']([^\"\']+)',function[1] if function else '')
    if not action or not re.search(r'method\s*:\s*[\"\']POST',function[1],re.I):raise ValueError('download_contract_changed')
    endpoint=urljoin(LIST_URL,action[1]); entries={}
    for anchor in re.findall(r'<a\b[^>]*onclick=[\"\'][^>]*fileDownload\(.*?</a>',html,re.S):
        params=re.search(r"fileDownload\('(-?\d+)'\s*,\s*'(\d+)'\)",anchor)
        label=unescape(re.sub('<[^>]+>','',anchor)).strip()
        number=re.search(r'제(\d{4})호_(.+?)\(',label)
        if not params or not number or not label.lower().endswith(('.pdf','.hwp','.hwpx')):continue
        n=number[1];fmt=label.rsplit('.',1)[1].lower()
        row={'id':'kasb:standard:'+n,'source_type':'kifrs_standard','standard_number':n,
            'standard_name':number[2].replace('_',' '),'authority':'KASB','version':label.rsplit('.',1)[0],
            'source_url':LIST_URL,'download_url':endpoint,'download_method':'POST',
            'download_parameters':{'fileNo':params[1],'fileSeq':params[2]},'filename':label,'format':fmt}
        if n not in entries or fmt=='pdf':entries[n]=row
    if len(entries)<3:raise ValueError('standards_catalogue_unrecognized')
    return sorted(entries.values(),key=lambda r:r['standard_number'])

def rights_for(document,rights):
    grant=(rights or {}).get(document['source_type'],{})
    if not grant.get('reference') or not all(grant.get(k) is True for k in ('automated_download','indexing','service_use')):
        raise PermissionError('source_license_not_confirmed:'+document['source_type'])
    return grant

def extract_pdf(blob,executable):
    if not blob.startswith(b'%PDF-'):raise ValueError('expected_pdf_received_html_or_other_content')
    with tempfile.TemporaryDirectory(prefix='fintra-kasb-') as directory:
        src=Path(directory)/'source.pdf';out=Path(directory)/'text.txt';src.write_bytes(blob)
        subprocess.run([str(executable),'-layout','-enc','UTF-8',str(src),str(out)],check=True,timeout=90,capture_output=True)
        return out.read_text(encoding='utf-8')

def sync_documents(documents,store,rights,extractor,download=fetch,indexer=None):
    result={'indexed':[],'skipped':[],'failed':[]}
    for doc in documents:
        try:
            rights_for(doc,rights)
            # Hash is checked as well as version: silently replaced files are detected.
            raw=download(doc['download_url'],urlencode(doc['download_parameters']).encode())
            digest=hashlib.sha256(raw).hexdigest();old=store.document(doc['id'])
            if old and old['content_hash']==digest and old['version']==doc['version']:
                result['skipped'].append(doc['id']);continue
            if doc['format']!='pdf':raise ValueError('hwp_extractor_not_configured')
            paragraphs=split_paragraphs(extractor(raw))
            if indexer:paragraphs=indexer(paragraphs)
            store.replace(doc,paragraphs,digest)
            result['indexed'].append({'id':doc['id'],'paragraphs':len({p['paragraph'] for p in paragraphs})})
        except Exception as exc:
            reason=type(exc).__name__+':'+str(exc);store.failure(doc['id'],reason)
            result['failed'].append({'id':doc['id'],'reason':reason})
    return result

def discover():
    html=fetch(LIST_URL).decode('utf-8');script=fetch(JS_URL).decode('utf-8')
    return catalogue(html,script)

def qna_catalogue(html):
    # fn_Detail builds this path in the actual published page; fail if its contract changes.
    if not re.search(r'"/front/board/View"\s*\+\s*ctgCd\s*\+\s*"\.do"',html):
        raise ValueError('qna_navigation_contract_changed')
    rows=[]
    for seq,category,title in re.findall(r'fn_Detail\(\s*\'(\d+)\'\s*,\s*\'(\d+)\'\s*\);?[^>]*>(.*?)</a>',html,re.S):
        if category!='016005':continue
        rows.append({'id':'kasb:qna:'+seq,'source_type':'kasb_qna','title':unescape(re.sub('<[^>]+>','',title)),
            'authority':'KASB staff expedited response','authority_level':'non_formal_interpretation',
            'source_url':urljoin(QNA_URL,'View'+category+'.do')+'?'+urlencode({'seq':seq,'ctgCd':category}),
            'notice':'신속처리질의: 정규 절차를 거치지 않아 한국회계기준원의 공식 의견과 일치하지 않을 수 있습니다.'})
    return rows

def parse_qna(html,document):
    match=re.search(r'<div class="board_view_cont[^\"]*">(.*?)<strong><span style="color:#0000FF;">',html,re.S)
    if not match:raise ValueError('qna_body_contract_changed')
    text=unescape(re.sub('<[^>]+>','',re.sub(r'<br\s*/?>','\n',match[1]))).strip()
    if not text:raise ValueError('empty_qna')
    # Q&A references are not the Q&A's own normative paragraph identifiers.
    return [dict(document,paragraph='qna',section='질의와 회신',content=text,chunk_index=0)]
