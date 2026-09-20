# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Source-heading metadata only. Missing metadata never matches a filter."""
import re
FIELDS={'standard_id','standard_name','paragraph','section','topic'}
def metadata(row):
    if '_standards_metadata' in row:return row['_standards_metadata']
    title=row.get('title') or ''; match=re.search(r'(?:제\s*)?(\d{4})(?:\s*호)?',title)
    text=row.get('text') or ''
    paragraphs=re.findall(r'^\s*((?:[A-Z]{1,3})?\d{1,3}[A-Z]?)\s*$',text,re.M)
    headings=[]
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    for i,line in enumerate(lines[:-1]):
        if re.fullmatch(r'(?:[A-Z]{1,3})?\d{1,3}[A-Z]?',lines[i+1]) and len(line)<65 and line!=title and not line.endswith(('다.','다')):headings.append(line)
    return {'standard_id':match[1] if match else None,'standard_name':title,
        'paragraph':row.get('paragraph') or paragraphs or None,'section':row.get('section') or headings or None, 'topic':row.get('topic')}
def matches(row, filters=None):
    filters=filters or {}
    if set(filters)-FIELDS:raise ValueError('Unsupported standards metadata filter')
    md=metadata(row)
    for k,values in filters.items():
        values=values if isinstance(values,list) else [values]
        if not values or any(not isinstance(v,str) or not v.strip() for v in values):raise ValueError('Metadata filters require nonempty strings')
        actual=md.get(k)
        if not actual:return False
        actual=[str(s).casefold() for s in actual] if isinstance(actual,list) else [str(actual).casefold()]
        if k in ('standard_id','paragraph'):
            if not set(actual)&{v.casefold() for v in values}:return False
        elif not any(v.casefold() in a for v in values for a in actual):return False
    return True
