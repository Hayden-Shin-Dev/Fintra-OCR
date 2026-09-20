# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Deterministic constraints run before model review of generated prose.

Model approval cannot override these constraints. Semantic review is additional
evidence, not proof that an accounting opinion is correct.
"""
import re
from decimal import Decimal

NUMBER = r'-?\d[\d,]*(?:\.\d+)?'
AMOUNT = re.compile(r'('+NUMBER+r')\s*(USD|KRW|EUR|JPY|GBP|CNY|원|개|PCS|KG|%)(?![A-Za-z])', re.I)
STANDARD = re.compile(r'(?:K-?IFRS|IFRS|IAS|제)\s*(\d{1,4})\s*(?:호|장)?',re.I)

def numeric_claims(text):
    return {(Decimal(n.replace(',','')),u.upper()) for n,u in AMOUNT.findall(text)}

def validate(text, citations, kind='explanation'):
    errors=[]
    sources='\n'.join(str(c.get('relevant_text') or c.get('quote','')) for c in citations if c.get('kind')=='standard')
    allowed=numeric_claims(sources)
    frameworks={re.sub(r'[-\s]','',str(c.get('source',{}).get('framework'))).upper() for c in citations if c.get('kind')=='standard'}
    for c in citations:
        if c.get('kind')!='check':continue
        check=c['check'];unit=check.get('context',{}).get('comparison_unit','')
        difference=check.get('values',{}).get('difference')
        if difference is not None and unit:
            try:
                diff=Decimal(str(difference).replace(',',''))
                allowed.update({(diff,str(unit).upper()),(abs(diff),str(unit).upper())})
            except Exception:pass
        for e in check.get('evidence',[]):
            value=e.get('normalized_value')
            if value is not None:allowed.update(numeric_claims(str(value)+' '+str(unit)))
    if numeric_claims(text)-allowed:errors.append('출처에 없는 수치 또는 단위를 생성했습니다.')
    standard_identity='\n'.join(str(c.get('title',''))+'\n'+str(c.get('source',{}).get('standard') or '') for c in citations if c.get('kind')=='standard')
    if set(STANDARD.findall(text))-set(STANDARD.findall(sources+'\n'+standard_identity)):errors.append('출처에 없는 기준 번호를 생성했습니다.')
    if '일반기업회계기준' in text and '일반기업회계기준' not in frameworks:errors.append('선택한 기준체계와 설명이 다릅니다.')
    if re.search(r'K-?IFRS',text,re.I) and not any(re.sub(r'[-\s]','',str(f)).upper()=='KIFRS' for f in frameworks):errors.append('선택한 기준체계와 설명이 다릅니다.')
    if re.search(r'(?:실사|조회|외부확인|계약서 검토|분개 검토|입금 확인).{0,12}(?:완료했|수행했|완료하였|수행하였)',text):
        errors.append('실행 기록이 없는 감사 절차를 완료했다고 서술했습니다.')
    if re.search(r'재고자산[은는이가].{0,12}매출원가(?:로|라고).{0,8}(?:불리|같|동일|뜻)',text):errors.append('재고자산과 매출원가를 동일한 개념으로 바꿨습니다.')
    if kind=='risk':
        for match in re.finditer(r'(?:부정|횡령|회계\s*오류).{0,8}(?:확정|발생했습니다|입증)',text):
            tail=text[match.end():match.end()+24]
            if not re.match(r'(?:할|될|하였다고|했다고)?\s*(?:수\s*없|하지\s*않|되지\s*않|할\s*수\s*없)',tail):
                errors.append('문서 차이에서 확정할 수 없는 결론을 생성했습니다.')
    return errors
