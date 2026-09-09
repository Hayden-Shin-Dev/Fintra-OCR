"""Complete table-caption spans, grounded by independent neighboring headers."""
import re
from .domain import semantic_label
from .layout import center,box,value_spans
PARTS=[('unit_price', 'unit\\s*[- ]?\\s*price'), ('description', 'description(?:\\s+of\\s+goods)?'), ('package_count', '(?:packages?|pkgs?\\.?)'), ('quantity', "(?:quantity|q[’']?ty)"), ('amount', '(?:amount|value)'), ('unit', '(?:uom|unit)')]

def complete_column_parts(text):
    if re.search(r'[:：\d]',text):return []
    parts=[];pos=0
    while pos<len(text):
        gap=re.match(r'\s+',text[pos:])
        if gap:pos+=gap.end();continue
        matches=[]
        for role,pattern in PARTS:
            m=re.match(pattern+r'(?!\w)',text[pos:],re.I)
            if m:matches.append((m.end(),role))
        if not matches:return []
        length,role=max(matches);parts.append((role,pos,pos+length));pos+=length
    return parts if len({p[0] for p in parts})>=2 else []

def merged_table_caption(token,document,height):
    parts=complete_column_parts(token.text)
    if not parts:return []
    # Another aligned header supplies independent semantic context. Relative
    # row geometry, not page coordinates, establishes the goods table band.
    peers=[]
    for other in document.tokens:
        if other.id==token.id or other.page!=token.page or abs(center(other)[1]-center(token)[1])>height*.8:continue
        found=semantic_label(other.text)
        peers += [found[0]] if found else [p[0] for p in complete_column_parts(other.text)]
    combined={p[0] for p in parts}|set(peers)
    return parts if peers and len(combined)>=3 and combined&{'quantity','package_count','amount','unit_price'} and combined&{'description','quantity','package_count'} else []

def quantity_column_qualifiers(document,height):
    result=[]
    for token in document.tokens:
        full=re.fullmatch(r"(?i)\s*(?:quantity|qty)\s+(ordered|shipped)\s*",token.text)
        if full:result.append((token,token,full.group(1).lower()));continue
        if not re.fullmatch(r'(?i)\s*(?:quantity|qty)\s*',token.text):continue
        below=[t for t in document.tokens if t.page==token.page and re.fullmatch(r'(?i)\s*(?:ordered|shipped)\s*',t.text) and 0<box(t)[1]-box(token)[1]<height*1.8 and abs(center(t)[0]-center(token)[0])<height]
        if len(below)==1:result.append((token,below[0],below[0].text.strip().lower()))
    paired=[]
    for parent,child,role in result:
        opposite=[p for p,c,r in result if r!=role and p.page==parent.page and abs(center(p)[1]-center(parent)[1])<height]
        if opposite:paired.append((parent,child,role))
    return paired

def package_count_caption(token,document,height):
    if len(token.text)>60 or re.search(r'[:：\d]',token.text):return None
    if not re.match(r'(?i)^\s*(?:no\.?|number|count)\s+of\s+(?:cont(?:ainers?)?\.?|packages?|pkgs?\.?|cartons?)\b',token.text):return None
    if re.search(r'(?i)\b(?:shall|must|should|declared|received|loaded)\b',token.text):return None
    peers={found[0] for other in document.tokens if other.id!=token.id and other.page==token.page and abs(center(other)[1]-center(token)[1])<height*1.2 and (found:=semantic_label(other.text))}
    if not peers&{'marks','description','product_code'} or not peers&{'gross_weight','net_weight','volume'}:return None
    cells=[other for other in document.tokens if other.page==token.page and 0<box(other)[1]-box(token)[3]<height*8 and max(box(other)[0],box(token)[0])<min(box(other)[2],box(token)[2])]
    for cell in cells:
        if not re.fullmatch(r'(?i)\s*\d+(?:[.,]\d+)*\s*(?:packages?|pkgs?\.?|cartons?|ctns?\.?|boxes?|drums?)\s*',cell.text):continue
        if value_spans(cell,'number','package_count') and value_spans(cell,'unit','package_type'):return ('package_count',0,len(token.text))
    return None
