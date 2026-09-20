# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Restore complete source paragraphs around indexed character slices."""
import re

def expand(source,request,cache):
    origin=source.get('source',{});record=origin.get('record_id')
    pointer=re.fullmatch(r'/document/content/(\d+)/content_text',origin.get('json_pointer',''))
    if not record or not pointer:return source
    if record not in cache:cache[record]=request('/source',{'record_id':record})
    text=cache[record]['document']['content'][int(pointer.group(1))]['content_text']
    start,end=origin['char_start'],origin['char_end']
    if text[start:end]!=source['text']:
        raise ValueError('검색 문단과 보관 원문의 위치가 일치하지 않습니다.')
    if len(text)<=200000:
        # Ranking operates on complete numbered paragraphs in audit_research.
        # A nearby-only window can omit the governing rule earlier in the same
        # standard and leave only disclosure or exception paragraphs.
        return dict(source,text=text,source=dict(origin,char_start=0,char_end=len(text)),
                    retrieved_span={'char_start':start,'char_end':end})
    # Expand at real paragraph boundaries, never at a fixed character cut.
    left=text.rfind('\n\n',0,max(0,start-1200))
    left=0 if left<0 else left+2
    right=text.find('\n\n',min(len(text),end+1600))
    right=len(text) if right<0 else right
    if right-left>14000:
        left=text.rfind('\n\n',0,start);left=0 if left<0 else left+2
        right=text.find('\n\n',end);right=len(text) if right<0 else right
    return dict(source,text=text[left:right],source=dict(origin,char_start=left,char_end=right),
                retrieved_span={'char_start':start,'char_end':end})
