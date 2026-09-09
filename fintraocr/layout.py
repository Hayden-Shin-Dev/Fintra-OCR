"""Relative geometry and exact character spans. No template or company data."""
import re
import unicodedata
from types import SimpleNamespace
from statistics import median
from functools import lru_cache
from .models import Span, Selection
from .normalize import normalize

def box(t):
    return cached_box(tuple(t.bbox))

@lru_cache(maxsize=65536)
def cached_box(points):
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)
def label_center(t,start,end):
    l,u,r,b=box(t)
    return l+(r-l)*(start+end)/(2*max(1,len(t.text))),(u+b)/2

def center(t):
    l,u,r,b=box(t);return (l+r)/2,(u+b)/2
def span(t,start=0,end=None):
    return Span(token_id=t.id,start=getattr(t,'source_start',0)+start,end=getattr(t,'source_start',0)+(len(t.text) if end is None else end))

NUMBER=re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)*(?![\d])")
UNIT=re.compile(r"(?i)(?<![a-z])(?:m/t|mt|kilograms?|kgs?|lbs?|tonnes?|cbm|m[³3]|pcs|pieces?|sets?|ea|ctns?|ct|pkgs?|packages?|cartons?|boxes|box|bags?|drums?|yards?|feet|foot|meters?|metres?|dozens?|doz|inches|inch|cases?|pounds?|cft|sf|sm)(?![a-z])|킬로그램|개")

def is_voyage_literal(text):
    """An explicit voyage designator, only meaningful with voyage context."""
    return bool(re.fullmatch(r'(?i)\s*(?:v\.?|voy(?:age)?\.?\s*(?:no\.?)?)\s*[-.:]?\s*\d[\w/-]*\s*',text))

def explained_measure_end(raw,key):
    """Literal measure followed by an explicit packing calculation, not a conversion.

    Only select the printed leading measure. Never evaluate the calculation or
    choose one of two alternative measurements in parentheses.
    """
    dimension={'gross_weight':{'kg','g','lb','t'},'net_weight':{'kg','g','lb','t'},
               'volume':{'m3','ft3'},'volume_unit':{'m3','ft3'},
               'gross_weight_unit':{'kg','g','lb','t'},'net_weight_unit':{'kg','g','lb','t'}}.get(key)
    if dimension is None:return None
    m=re.fullmatch(r'(?i)\s*([-+]?\d+(?:[.,]\d+)*)\s*([a-z³3/]+)\s*\(\s*\d+\s+(?:cartons?|ctns?|packages?|pkgs?|bags?|boxes)\s*[x×*]\s*\d+(?:[.,]\d+)*\s*([a-z³3/]+)(?:\s+each)?\s*\)\s*',raw)
    if m and normalize(m[2],'unit')[0] in dimension and normalize(m[2],'unit')[0]==normalize(m[3],'unit')[0]:return m.end(2)
    return None

def value_spans(t,kind,key,start=0,end=None):
    end=len(t.text) if end is None else end
    raw=t.text[start:end]
    dimension={'kg','g','lb','t'} if key in {'gross_weight','net_weight','weight_unit','gross_weight_unit','net_weight_unit'} else {'m3','ft3'} if key in {'volume','volume_unit'} else None
    if dimension and kind in {'number','unit'}:
        units={normalize(m.group(),'unit')[0] for m in UNIT.finditer(raw)}
        known=units&{'kg','g','lb','t','m3','ft3'}
        if known and not known&dimension:return []

    if kind=="number":
        if key in {'package_count','total_packages'}:
            explicit=list(re.finditer(r'(?i)(?<![\w.])([0-9]+)\s*(?:pkgs?|packages?|ctns?|cartons?)\b',raw))
            if len(explicit)==1:return [span(t,start+explicit[0].start(1),start+explicit[0].end(1))]
        # A space grouping separator belongs to one number. Require complete
        # valid groups so two neighboring values such as "12 34" stay unresolved.
        grouped=re.fullmatch(r'\s*[$€£¥₩]?\s*([+-]?\d{1,3}(?: \d{3})+(?:[.,]\d+)?)\s*[$€£¥₩]?\s*',raw)
        if grouped and normalize(grouped.group(1),'number')[0] is not None:
            return [span(t,start+grouped.start(1),start+grouped.end(1))]
        matches=list(NUMBER.finditer(raw))
        if len(matches)!=1:return []
        if key in {'package_count','total_packages'} and matches[0].end()<len(raw) and raw[matches[0].end()].isalnum():return []
        m=matches[0];return [span(t,start+m.start(),start+m.end())]
    if kind=="unit":
        matches=list(UNIT.finditer(raw))
        if len(matches)!=1:
            suffix=re.fullmatch(r'\s*[-+]?\d+(?:[.,]\d+)*\s+([A-Za-z][A-Za-z³3/.]*)\s*',raw) if key=='unit' else None
            return [span(t,start+suffix.start(1),start+suffix.end(1))] if suffix else []
        m=matches[0];return [span(t,start+m.start(),start+m.end())]
    if kind=="date":
        prefix=unambiguous_date_prefix(raw)
        if prefix:return [span(t,start+prefix[0],start+prefix[1])]
        # Do not repair OCR misspellings. Keep the original date for normalization.
        return [span(t,start,end)]
    if kind=='freight_terms':
        literal=re.fullmatch(r'''(?i)\s*["“']?(?:freight\s+)?(prepaid|collect)["”']?\s*''',raw)
        if literal:return [span(t,start+literal.start(1),start+literal.end(1))]
    if kind=='incoterms':
        match=re.match(r'(?i)\s*(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF|DAT|DAF|DES|DEQ|DDU)\b',raw)
        if not match:return []
        stop=re.search(r'(?i)[,;]\s*(?:payment|terms of payment)\b',raw)
        return [span(t,start+match.start(1),start+(stop.start() if stop else len(raw.rstrip())))]
    return [span(t,start,end)] if raw.strip() else []

class LayoutResolver:
    def __init__(self,document):
        self.document=document;self.tokens={t.id:t for t in document.tokens}
        self.height=median(max(1,box(t)[3]-box(t)[1]) for t in document.tokens) if document.tokens else 1
        self.diagnostics=[]
        self.auxiliary_tables=[]

    def declared_value_basis(self,selection):
        """Keep an observed amount reviewable when its valuation basis is unresolved.

        A nearby aligned basis selector is not the general liability paragraph.
        OCR text without a selected checkbox cannot establish shipment scope.
        Never multiply a per-package amount to manufacture a shipment total.
        """
        if not selection or not selection.spans:return
        pattern=r'(?i)^\s*[^\w]*per\s+(?:packages?|pkgs?|kilograms?|kgs?|pounds?|lbs?)\b.{0,100}$'
        references=[]
        for ref in selection.spans:
            origin=self.tokens[ref.token_id]
            for token in self.document.tokens:
                if token.page!=origin.page:continue
                inline=token.id==origin.id and re.search(r'(?i)\bper\s+(?:packages?|pkgs?|kilograms?|kgs?|pounds?|lbs?)\b',token.text[ref.end:])
                adjacent=abs(center(token)[1]-center(origin)[1])<self.height*.8 and 0<=box(token)[0]-box(origin)[2]<self.height*12 and re.fullmatch(pattern,token.text)
                if inline or adjacent:references.append(span(token,ref.end if inline else 0))
        if references:
            selection.reasons.append('declared_value_basis_requires_review')
            seen={(s.token_id,s.start,s.end) for s in selection.reference_spans}
            for ref in references:
                identity=(ref.token_id,ref.start,ref.end)
                if identity not in seen:selection.reference_spans.append(ref);seen.add(identity)

    def port_abbreviations(self):
        """Resolve paired maritime POL/POD captions, not standalone POD statuses.

        Require explicit inline captions, independently typed country-qualified
        locations, a nearby paired route caption and vessel context. These are
        relative geometry checks; no port names or template coordinates occur.
        """
        from .domain import semantic_label,compound_labels
        candidates=[];vessels=[]
        for token in self.document.tokens:
            meanings=compound_labels(token.text) or ([semantic_label(token.text)] if semantic_label(token.text) else [])
            if any(field=='vessel' for field,_,_ in meanings):vessels.append(token)
            match=re.fullmatch(r'(?i)\s*(P\.?O\.?([LD])\.?\s*[:：])\s*(\S.+)',token.text)
            if not match or ',' not in match[3] or normalize(match[3],'country')[0] is None:continue
            if not re.search(r'[A-Za-z]',match[3].split(',',1)[0]) or re.search(r'\d|[$€£¥₩]',match[3]):continue
            candidates.append((token,match))
        result={}
        for token,match in candidates:
            peers=[(other,m) for other,m in candidates if other.page==token.page and m[2].upper()!=match[2].upper() and (
                abs(box(other)[0]-box(token)[0])<self.height*2 and 0<abs(center(other)[1]-center(token)[1])<self.height*4 or
                abs(center(other)[1]-center(token)[1])<self.height and 0<abs(box(other)[0]-box(token)[0])<self.height*24)]
            context=[v for v in vessels if v.page==token.page and abs(center(v)[1]-center(token)[1])<self.height*10 and abs(box(v)[0]-box(token)[0])<self.height*24]
            if len(peers)==1 and context:
                result[token.id]=('port_of_loading' if match[2].upper()=='L' else 'port_of_discharge',match.start(1),match.end(1))
        return result

    def select(self,tokens,spec,key,labels,method="layout",ranges=None):
        if len(tokens)>1 and spec.kind in {'text','party'}:
            lines=[]
            for token in sorted(tokens,key=lambda t:(center(t)[1],box(t)[0])):
                line=next((line for line in lines[-2:] if abs(median(center(t)[1] for t in line)-center(token)[1])<self.height*.65),None)
                if line is None:lines.append([token])
                else:line.append(token)
            tokens=[t for line in lines for t in sorted(line,key=lambda t:box(t)[0])]
        spans=[]
        for i,t in enumerate(tokens):
            bounds=(ranges or {}).get(t.id,(0,len(t.text)))
            if spec.kind=='unit' and method=='table' and key=='unit':
                # An explicit unit column establishes the role. Preserve unfamiliar
                # unit text instead of deleting it through a vocabulary whitelist.
                raw=t.text[bounds[0]:bounds[1]]
                if value_spans(t,'number',key,*bounds):spans+=value_spans(t,'unit',key,*bounds)
                elif raw.strip() and not re.fullmatch(r'[\d\s.,+-]+',raw):spans.append(span(t,*bounds))
            else:spans+=value_spans(t,spec.kind,key,*bounds)
        if spec.kind=='number' and len(tokens)>1 and len(spans)>1:
            raw_parts=[t.text.strip() for t in tokens]
            if len(raw_parts)==2 and re.fullmatch(r'[+-]?\d+[.,]',raw_parts[0]) and re.fullmatch(r'\d+',raw_parts[1]):
                return Selection(spans=[span(t) for t in tokens],label_spans=labels,score=1,method='wrapped_decimal',reasons=[])
        if key=='hs_code' and len(tokens)>1 and all(re.fullmatch(r'[\d.]+',t.text.strip()) for t in tokens) and 6<=sum(len(re.sub(r'\D','',t.text)) for t in tokens)<=10:
            return Selection(spans=spans,label_spans=labels,score=1,method='wrapped_identifier')
        if not spans:return Selection(score=1,method=method,label_spans=labels,reasons=["value_type_not_resolved"])
        if key in {'gross_weight','net_weight','volume'} and len(spans)==1:
            from .domain import semantic_label
            known_measure=any(semantic_label(self.tokens[s.token_id].text[s.start:s.end]) and semantic_label(self.tokens[s.token_id].text[s.start:s.end])[0]==key for s in labels)
            explicit_unit=any(value_spans(t,'unit',key) for t in tokens) or any(value_spans(self.tokens[s.token_id],'unit',key,s.start,s.end) for s in labels)
            if not known_measure and not explicit_unit:
                return Selection(spans=spans,label_spans=labels,score=1,method=method,reasons=['unverified_measure_label_without_unit'])
        if spec.kind in {'number','unit','date'} and len(spans)>1:
            return Selection(spans=spans,label_spans=labels,score=1,method=method,reasons=['multiple_values_in_scalar_cell'])
        reasons=[]
        raw=' '.join(self.tokens[s.token_id].text[s.start:s.end] for s in spans)
        if key in {'document_reference','buyer_reference','forwarding_agent_number'} and re.match(r'(?i)^\s*[^:：]{1,60}\b(?:ref(?:erence)?s?|no\.?|number)\s*[:：]\s*\S',raw):
            reasons.append('nested_reference_caption_is_not_reference_value')

        if key in {'description','product_code'} and spans:
            # A block consisting entirely of empty document-reference captions
            # is not a goods name. Retain it as review evidence rather than
            # filling a redacted description with the surrounding form labels.
            caption=r'(?i)\s*(?:(?:according to\s+)?(?:contract|agreement|loan|project)\s*(?:no\.?|number|name)|name of (?:project|contract)|dated?)\s*[:：]?\s*'
            if all(re.fullmatch(caption,self.tokens[s.token_id].text[s.start:s.end]) for s in spans):
                reasons.append('document_metadata_is_not_goods_description')
        if key=='mode_of_transport' and re.fullmatch(r'(?i)\s*(?:EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DAT|DDP|DAF|DES|DEQ|DDU)(?:\s+.+)?\s*',raw):
            reasons.append('trade_term_is_not_transport_mode')
        if key=='mode_of_transport' and any(re.fullmatch(r'(?i)\s*delivery\s*',self.tokens[s.token_id].text[s.start:s.end]) for s in labels):
            reasons.append('delivery_caption_does_not_establish_transport_mode')
        if key in {'place_of_receipt','place_of_delivery','port_of_loading','port_of_discharge','shipping_origin','issue_place','freight_payable_at'}:
            # An observed monetary amount or payment option is not a place.
            # Keep the selected OCR spans for review instead of searching farther
            # away for an unrelated token that merely resembles a location.
            if re.fullmatch(r'\s*[+−-]?\d[\d., ]*\s*',raw):
                reasons.append('numeric_value_is_not_named_location')
            if re.fullmatch(r'\s*[$€£¥₩]\s*\d[\d., ]*\s*',raw):
                reasons.append('monetary_amount_is_not_named_location')
            if re.fullmatch(r'(?i)\s*(?:(?:ocean|sea|air|road|inland)\s+)?freight(?:\s+charges?)?\s*',raw):
                reasons.append('freight_charge_category_is_not_named_location')
            if re.fullmatch(r'(?i)\s*(?:freight\s+)?(?:prepaid|collect)\s*',raw):
                reasons.append('freight_payment_option_is_not_named_location')
            if re.fullmatch(r'(?i)\s*(?:EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DAT|DDP|DAF|DES|DEQ|DDU)\s*',raw):
                reasons.append('trade_term_is_not_named_location')
        if key in {'place_of_receipt','place_of_delivery','port_of_loading','port_of_discharge','shipping_origin','issue_place'} and re.fullmatch(r'(?i)\s*(?:CY|CFS|DOOR|SD)\s*[/–-]\s*(?:CY|CFS|DOOR|SD)\s*',raw):
            reasons.append('service_mode_is_not_named_location')
        return Selection(spans=spans,label_spans=labels,score=1,method=method,reasons=reasons)

    def header(self,label,spec,key,all_labels,table_ids):
        t=self.tokens[label['token_id']];l,u,r,b=box(t);h=max(1,b-u)
        ls=span(t,label['start'],label['end'])
        refs=[Span.model_validate(s) for s in label.get('fragments',[])] or [ls]
        if len(refs)>1:
            boxes=[box(self.tokens[s.token_id]) for s in refs]
            l,u,r,b=min(v[0] for v in boxes),min(v[1] for v in boxes),max(v[2] for v in boxes),max(v[3] for v in boxes)
        origin_y=(u+b)/2
        if re.search(r'(?i)\b(?:to be (?:completed|filled)|insert your|not provided|left blank)\b',t.text):
            return Selection(label_spans=[ls],score=1,method='layout',reasons=['explicit_blank_placeholder'])
        # Label and value may occupy disjoint character ranges of one token.
        suffix=t.text[label['end']:]
        stripped=suffix.lstrip(' :：#\t-')
        from .domain import compound_labels
        shared_vessel_voyage={f for f,_,_ in compound_labels(t.text)}=={'vessel','voyage'} and len({(a,b) for _,a,b in compound_labels(t.text)})==1
        shared_voyage=key=='voyage' and shared_vessel_voyage and not is_voyage_literal(stripped)
        shared_vessel=key=='vessel' and shared_vessel_voyage and is_voyage_literal(stripped)
        shared_issue_place=key=='issue_place' and {f for f,_,_ in compound_labels(t.text)}=={'issue_place','issue_date'} and normalize(stripped,'date')[0] is not None
        shared_issue_date=key=='issue_date' and {f for f,_,_ in compound_labels(t.text)}=={'issue_place','issue_date'} and stripped and normalize(stripped,'date')[0] is None
        if stripped and not shared_voyage and not shared_vessel and not shared_issue_place and not shared_issue_date:
            start=len(t.text)-len(stripped)
            end=min([v['start'] for v in all_labels if v['token_id']==t.id and v['start']>label['end']]+[len(t.text)])
            if end<len(t.text):end=start+len(t.text[start:end].rstrip(' ,;'))
            inline_selection=self.select([t],spec,key,refs,ranges={t.id:(start,end)})
            if key=='total_amount' and not inline_selection.spans and re.search(r'[A-Za-z]',stripped) and not re.search(r'\d',stripped):
                excluded_ids={v['token_id'] for v in all_labels}|table_ids
                numeric_neighbors=[other for other in self.document.tokens if other.page==t.page and other.id not in excluded_ids and other.id!=t.id and
                    abs(center(other)[1]-origin_y)<max(h,box(other)[3]-box(other)[1])*.65 and 0<=box(other)[0]-r and
                    re.fullmatch(r'\s*[$€£¥₩]?\s*[+-]?\d[\d., ]*\s*',other.text) and value_spans(other,'number',key)]
                if len(numeric_neighbors)==1 and not any(self.tokens[v['token_id']].page==t.page and r<=box(self.tokens[v['token_id']])[0]<box(numeric_neighbors[0])[0] and abs(center(self.tokens[v['token_id']])[1]-origin_y)<h for v in all_labels):
                    chosen=numeric_neighbors[0]
                    return self.select([chosen],spec,key,refs,method='layout')
            return inline_selection
        excluded={v['token_id'] for v in all_labels}|table_ids|{s.token_id for s in refs}
        own_label_ids={s.token_id for s in refs}|{t.id}
        peers=[self.tokens[v['token_id']] for v in all_labels if v['token_id'] not in own_label_ids and self.tokens[v['token_id']].page==t.page]
        from .domain import structural_caption,semantic_label
        boundary_peers=list(peers)
        peer_ids={p.id for p in peers}
        for candidate in self.document.tokens:
            if candidate.page!=t.page or candidate.id in own_label_ids or candidate.id in peer_ids:continue
            meaning=semantic_label(candidate.text)
            if structural_caption(candidate.text) or (meaning and not candidate.text[meaning[2]:].strip(' :：#	')):
                boundary_peers.append(candidate);peer_ids.add(candidate.id)

        # Adjacent label columns provide boundaries; positions are never absolute.
        right=min([box(p)[0] for p in peers if box(p)[0]>r and abs(center(p)[1]-center(t)[1])<h]+[float('inf')])
        candidates=[];measure_ranges={}
        for other in self.document.tokens:
            if other.page!=t.page or other.id==t.id or other.id in excluded:continue
            from .domain import structural_caption,semantic_label
            if structural_caption(other.text):continue
            if re.fullmatch(r'(?i)\s*(?:date|dt\.?)\s*[:：]\s*',other.text):continue
            # A complete caption remains a boundary even if the model omitted it.
            other_role=semantic_label(other.text)
            if other_role and not other.text[other_role[2]:].strip(' :：#\t'):continue
            if re.match(r'(?i)\s*(?:received by|particulars furnished|condition unless|herein|signature|remarks?\b)',other.text):continue
            ol,ou,orr,ob=box(other);cx,cy=center(other)
            if cx>=right:continue
            same_line=abs(cy-origin_y)<=max(h,ob-ou)*.65 and ol>=r-h*.3
            if len(refs)>1 and u-h*.5<=cy<=b+h*.5 and ol>=r-h*.3:same_line=True
            below=ou>=b-h*.65 and ou-b<=h*4 and (ol>=l-h or max(ol,l)<min(orr,r)) and cx<right
            if shared_voyage and ou>=b-h*.65 and ou-b<=h*4 and l-h*4<=ol<right:below=True
            side_party=spec.kind=='party' and len(refs)>1 and 0<=ol-r<=h*4 and u-h*3<=ou<=b+h*2
            role_caption=spec.kind=='party' and re.match(r'(?i)^as\s+',t.text[label['start']:label['end']])
            above=bool(role_caption and 0<=u-ob<h*2 and max(ol,l)<min(orr,r))
            if role_caption and not above:continue
            if not same_line and not below and not above and not side_party:continue
            # A value aligned beneath an earlier heading in the next column
            # belongs to that column, even when its baseline overlaps this label.
            # This catches address continuations beside empty transport cells.
            if ol>r and any(box(p)[0]>r and abs(ol-box(p)[0])<h and
                           box(p)[1]<=u and 0<=ou-box(p)[3]<min(h*4,ol-r)
                           for p in peers):continue
            # Retain an observed service mode for the field validator to flag.
            # Skipping it here incorrectly lets a more distant cell replace it.
            if key in {'place_of_delivery','place_of_receipt','port_of_loading','port_of_discharge','issue_place'} and re.fullmatch(r'(?i)\s*v\.\s*\d[\w/-]*\s*',other.text):continue
            # A closer intervening label owns this region.
            if below and any(box(p)[1]>u+h*.5 and box(p)[1]<ou and abs(box(p)[0]-l)<h*2 for p in boundary_peers):continue
            if spec.kind in ('number','unit'):
                # OCR can wrap a parenthetical calculation over several lines.
                # Require a complete, explicit explanation and relative alignment
                # before separating it from the literal measure preceding it.
                measure_text=other.text
                if '(' in measure_text and ')' not in measure_text:
                    following=sorted([v for v in self.document.tokens if v.page==other.page and v.id not in excluded and
                        0<=box(v)[1]-ob<h*3 and abs(box(v)[0]-ol)<h],key=lambda v:box(v)[1])
                    last_bottom=ob
                    for fragment in following:
                        if box(fragment)[1]-last_bottom>h:break
                        measure_text+=' '+fragment.text;last_bottom=box(fragment)[3]
                        if ')' in fragment.text:break
                measure_end=explained_measure_end(measure_text,key)
                if measure_end is not None and measure_end<=len(other.text):measure_ranges[other.id]=(0,measure_end)
                if not value_spans(other,spec.kind,key,*measure_ranges.get(other.id,(0,len(other.text)))):continue
            if key in {'gross_weight','net_weight','volume'} and re.search(r'[$€£¥₩]',other.text):continue
            # Keep a nearby date-shaped OCR reading as review evidence even
            # when its month cannot be normalized; never repair its characters.
            if spec.kind=='date' and normalize(other.text,'date')[0] is None and not unambiguous_date_prefix(other.text) and not re.fullmatch(r'(?i)\s*\d{1,2}[-/.](?:\d{1,2}|(?=[a-z0-9]*[a-z])[a-z0-9]{3,9})[-/.]\d{4}\s*',other.text):continue
            if spec.kind=='incoterms' and not value_spans(other,'incoterms',key):continue
            if key=='payment_terms' and re.fullmatch(r'(?i)\s*(?:CY|CFS|DOOR)\s*/\s*(?:CY|CFS|DOOR)\s*',other.text):continue
            if key=='payment_terms' and value_spans(other,'incoterms','incoterms') and not re.search(r'(?i)\bpayment\b',other.text):continue
            if key=='payment_terms' and normalize(other.text,'country')[0] is not None and any(value_spans(v,'incoterms','incoterms') and v.page==other.page and abs(center(v)[1]-cy)<self.height*.65 and 0<=ol-box(v)[2]<self.height*6 for v in self.document.tokens):continue
            if spec.kind=='party' and (re.match(r'\s*\d',other.text) or re.match(r'(?i)(tel|fax|zip|phone|address)\b',other.text)):continue
            if key=='forwarding_agent_number' and not re.fullmatch(r'(?=.*\d)[A-Za-z0-9./#-]+',other.text.strip()):continue
            if key=='forwarding_agent_number' and ol>r+h:continue
            if key in {'vessel','voyage'}:
                from .domain import compound_labels
                dual={f for f,_,_ in compound_labels(t.text)}=={'vessel','voyage'}
                voyage_text=is_voyage_literal(other.text)
                if dual and ((key=='voyage' and not voyage_text) or (key=='vessel' and voyage_text)):continue
            if side_party and (normalize(other.text,'country')[0] is not None or re.search(r'(?i)\b(?:road|street|avenue|park|postal|zip)\b',other.text)):continue
            cost=(0 if same_line or above else max(0,ou-b)/h)+abs(ol-l)/(h*10)
            if below and max(ol,l)>=min(orr,r):cost+=2
            if side_party:cost=(ou-(u-h*3))/h
            candidates.append((cost,other))
        if not candidates:return Selection(score=1,method='layout',label_spans=refs,reasons=['label_without_resolvable_value'])
        candidates.sort(key=lambda c:c[0])
        chosen=candidates[0][1]
        if key=='incoterms' and re.fullmatch(r'(?i)\s*(?:EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF|DAT|DAF|DES|DEQ|DDU)\s*',chosen.text):
            locations=[other for other in self.document.tokens if other.page==chosen.page and other.id not in excluded and other.id!=chosen.id and ',' in other.text and normalize(other.text,'country')[0] is not None and abs(center(other)[1]-center(chosen)[1])<self.height*.65 and 0<=box(other)[0]-box(chosen)[2]<self.height*6]
            if len(locations)==1:
                return Selection(spans=[span(chosen),span(locations[0])],label_spans=refs,score=1,method='layout')
        if key=='payment_terms':
            explicit=re.search(r'(?i)\bpayment\s+terms?\s*[:：]\s*',chosen.text)
            if explicit:
                return self.select([chosen],spec,key,refs+[span(chosen,explicit.start(),explicit.end())],ranges={chosen.id:(explicit.end(),len(chosen.text))})
        qualifier=re.match(r'(?i)^\s*[-•]?\s*\(?name\)?\s*[:：]?\s+',chosen.text) if spec.kind=='party' else None
        return self.select([chosen],spec,key,refs,ranges={chosen.id:(qualifier.end(),len(chosen.text))} if qualifier else measure_ranges)

    def fragmented_headers(self,labels,schema):
        from .domain import TERMS
        patterns=[]
        for field,terms in TERMS.items():
            if field not in schema:continue
            for term in terms:
                words=term.split()
                for split in range(1,len(words)):
                    patterns.append((field,re.compile(r'(?i)(?<!\w)'+re.escape(' '.join(words[:split]))+r'\s*$'),re.compile(r'(?i)^\s*'+re.escape(' '.join(words[split:]))+r'(?!\w)')))
        result={}
        for first in self.document.tokens:
            candidates=[(field,left.search(first.text),right) for field,left,right in patterns if left.search(first.text)]
            if not candidates:continue
            following=[t for t in self.document.tokens if t.page==first.page and box(t)[1]>box(first)[1] and 0<=box(t)[1]-box(first)[3]<self.height and abs(box(t)[0]-box(first)[0])<self.height]
            if not following:continue
            second=min(following,key=lambda t:box(t)[1])
            from .domain import compound_labels
            if compound_labels(first.text+' '+second.text):continue
            for field,left,right_pattern in candidates:
                prefix=first.text[:left.start()].strip()
                if prefix and not re.fullmatch(r'\d{1,3}[.)]',prefix):
                    narrative=re.search(r'(?i)\b(?:matches?|matching|shown|appears?|refers?|see|please|will|must|should)\b',prefix)
                    explicit_separator=re.match(r'\s*[:：]',second.text[right_pattern.match(second.text).end():]) if right_pattern.match(second.text) else None
                    if narrative or not explicit_separator:continue
                right=right_pattern.match(second.text)
                if not right:continue
                start=right.end()+len(second.text[right.end():])-len(second.text[right.end():].lstrip(' :：'))
                end=min([l['start'] for l in labels if l['token_id']==second.id and l['start']>start]+[len(second.text)])
                raw=second.text[start:end].strip()
                if not any(c.isalnum() for c in raw) or ':' in raw or '：' in raw:continue
                end=start+len(second.text[start:end].rstrip())
                refs=[span(first,left.start(),left.end()),span(second,right.start(),right.end())]
                result[field]=self.select([second],schema[field],field,refs,method='fragmented_inline',ranges={second.id:(start,end)})
        return result

    def footer_volume(self,fields,rows):
        """A typed volume continuing an explicit document-total weight block.

        Preserve the literal number and its unit; the total caption supplies
        document scope. Never compute volume or borrow a goods-row quantity.
        """
        candidates=[]
        for key in ('gross_weight','net_weight'):
            selection=fields.get(key)
            if not selection or selection.reasons or selection.ambiguous or len(selection.spans)!=1:continue
            caption=[self.tokens[s.token_id] for s in selection.label_spans if re.match(r'(?i)^\s*total\s+(?:gross|net)\s+weight\s*[:：]',self.tokens[s.token_id].text)]
            if len(caption)!=1:continue
            evidence=selection.spans[0];origin=self.tokens[evidence.token_id]
            if origin.id!=caption[0].id:continue
            row_tokens=[self.tokens[s.token_id] for row in rows for v in row.values() if v for s in v.spans if self.tokens[s.token_id].page==origin.page]
            if not row_tokens or box(origin)[1]<=max(box(t)[3] for t in row_tokens)+self.height:continue
            l,u,r,b=box(origin);value_x=l+(r-l)*evidence.start/max(1,len(origin.text))
            for token in self.document.tokens:
                if token.page!=origin.page or not 0<=box(token)[1]-b<self.height*3 or abs(box(token)[0]-value_x)>self.height*3:continue
                match=re.fullmatch(r'(?i)\s*([-+]?\d+(?:[.,]\d+)*)\s*(CBM|m[³3]|CFT|CUFT)\s*',token.text)
                if not match:continue
                candidates.append((token,match,selection.label_spans))
        unique={t.id:(t,m,refs) for t,m,refs in candidates}
        if not unique:return None
        entries=list(unique.values());ambiguous=len(entries)>1
        references=list({(s.token_id,s.start,s.end):s for _,_,refs in entries for s in refs}.values())
        return (
            Selection(spans=[span(t,m.start(1),m.end(1)) for t,m,_ in entries],label_spans=[span(t,m.start(2),m.end(2)) for t,m,_ in entries],reference_spans=references,score=1,method='aggregate_continuation',ambiguous=ambiguous,reasons=['multiple_values_in_total_block'] if ambiguous else []),
            Selection(spans=[span(t,m.start(2),m.end(2)) for t,m,_ in entries],label_spans=references,score=1,method='aggregate_continuation',ambiguous=ambiguous,reasons=['multiple_values_in_total_block'] if ambiguous else []))

    def payment_schedule(self,selection,labels,table_ids):
        selection=self._adjacent_payment_schedule(selection,labels,table_ids)
        if not selection or selection.ambiguous or selection.reasons or len(selection.spans)!=1:return selection
        origin=self.tokens[selection.spans[0].token_id];h=self.height
        # Literal instalment roles plus timing text, supported by a nearby explicit
        # remittance caption; numeric percentage alone never establishes a payment.
        clauses=[]
        for token in self.document.tokens:
            if token.page!=origin.page or token.id in table_ids:continue
            m=re.match(r'(?i)^\s*\d+(?:[.,]\d+)?\s*%\s*(advanced?|deposit|down\s*payment|balance|remaining)\b',token.text)
            if m and re.search(r'(?i)\b(?:with|within|after|before|upon|against|on)\b',token.text[m.end():]):clauses.append((token,m.group(1).lower()))
        groups=[]
        for first,role in clauses:
            if role in {'balance','remaining'}:continue
            second=[t for t,r in clauses if r in {'balance','remaining'} and 0<box(t)[1]-box(first)[3]<h*2 and abs(box(t)[0]-box(first)[0])<h]
            if len(second)!=1:continue
            last=second[0]
            captions=[t for t in self.document.tokens if t.page==origin.page and re.fullmatch(r'(?i)\s*(?:remit(?:tance)?|payment\s+to)\s*[:：]?\s*',t.text) and 0<=box(first)[0]-box(t)[2]<h*8 and box(first)[1]-h<=center(t)[1]<=box(last)[3]+h*4]
            if not captions:continue
            groups.append((first,last,captions))
        if len(groups)!=1:return selection
        first,last,captions=groups[0]
        selected=selection.model_copy(deep=True)
        selected.spans += [span(first),span(last)]
        selected.label_spans += [span(t) for t in captions]
        return selected

    def _adjacent_payment_schedule(self,selection,labels,table_ids):
        """Preserve adjacent instalment clauses under an established payment role."""
        if not selection or len(selection.spans)!=1 or selection.reasons or selection.ambiguous:return selection
        origin=self.tokens[selection.spans[0].token_id]
        l,u,r,b=box(origin);h=self.height
        excluded={v['token_id'] for v in labels}|table_ids
        peers=[self.tokens[v['token_id']] for v in labels if self.tokens[v['token_id']].page==origin.page]
        right=min([box(p)[0] for p in peers if box(p)[0]>r and abs(center(p)[1]-center(origin)[1])<h*2]+[float('inf')])
        candidates=sorted([t for t in self.document.tokens if t.page==origin.page and box(t)[1]>=b-h*.25 and
            l-h<=box(t)[0]<min(right,l+h*5)],key=lambda t:(box(t)[1],box(t)[0]))
        appended=[];previous=origin
        from .domain import structural_caption,semantic_label
        for token in candidates:
            tl,tu,tr,tb=box(token)
            if tu-box(previous)[3]>h*1.2:break
            if token.id in table_ids or structural_caption(token.text) or semantic_label(token.text):break
            instalment=bool(re.match(r'(?i)^\s*\d+(?:[.,]\d+)?\s*%\s*[:：-]?\s*(?:upon|after|before|on|in|within|at|against|payable|due)\b',token.text))
            continuation=bool(appended and tl>l+h and tl<box(previous)[2] and
                re.match(r'^\s*[a-z]',token.text) and not re.search(r'[.;]\s*$',previous.text))
            if token.id in excluded and not continuation:break
            if not instalment and not continuation:break
            # Two neighboring clauses on the same baseline need separate block
            # ownership; never concatenate them simply because both contain %.
            if appended and abs(center(token)[1]-center(previous)[1])<h*.6:break
            appended.append(span(token));previous=token
        if appended:
            selection=selection.model_copy(deep=True)
            selection.spans+=appended
        return selection

    def freight_column(self):
        """Resolve a populated PREPAID/COLLECT charge table, not a bare option."""
        choices=[]
        for paid in self.document.tokens:
            if paid.text.strip().casefold()!='prepaid':continue
            partners=[t for t in self.document.tokens if t.page==paid.page and t.text.strip().casefold()=='collect' and abs(center(t)[1]-center(paid)[1])<self.height*.8]
            if len(partners)!=1:continue
            pair=[paid,partners[0]];top=min(box(t)[1] for t in pair)
            captions=[t for t in self.document.tokens if t.page==paid.page and
                re.fullmatch(r'(?i)\s*freight(?:\s+(?:rates|and|charges|weights|or|measurements))+\s*',re.sub(r'[,/&]+',' ',t.text)) and
                -self.height*1.5<=top-box(t)[3]<self.height*4 and box(t)[0]<max(box(v)[2] for v in pair)]
            # A charge table can name its columns directly instead of placing
            # a separate "Freight and charges" heading above them. The ordered
            # CHARGES/RATE/PREPAID/COLLECT structure establishes the same scope.
            if not captions:
                band=[t for t in self.document.tokens if t.page==paid.page and abs(center(t)[1]-center(paid)[1])<self.height*.8]
                charges=[t for t in band if re.fullmatch(r'(?i)\s*(?:freight\s+)?charges\s*',t.text)]
                rates=[t for t in band if re.fullmatch(r'(?i)\s*rate\s*',t.text)]
                if len(charges)==1 and len(rates)==1 and center(charges[0])[0]<center(rates[0])[0]<min(center(v)[0] for v in pair):
                    captions=charges
            if not captions:continue
            caption=max(captions,key=lambda t:box(t)[1]);populated=[]
            for heading in pair:
                values=[t for t in self.document.tokens if t.page==heading.page and
                    0<=box(t)[1]-box(heading)[3]<self.height*6 and
                    abs(center(t)[0]-center(heading)[0])<abs(center(pair[0])[0]-center(pair[1])[0])*.45 and
                    re.fullmatch(r'\s*[$€£¥₩]?\s*\d[\d,.]*\s*',t.text) and
                    value_spans(t,'number','amount')]
                if values:populated.append((heading,values))
            if len(populated)==1:
                heading,values=populated[0]
                choices.append((Selection(spans=[span(heading)],label_spans=[span(caption)],score=1,method='freight_column'),pair,values))
        return choices[0] if len(choices)==1 else None

    def shared_unit(self,labels):
        chars=[];sources=[]
        for ref in labels:
            token=self.tokens[ref.token_id]
            for i in range(ref.start,ref.end):
                for ch in unicodedata.normalize('NFKC',token.text[i]):
                    if not ch.isspace():chars.append(ch);sources.append((token,i))
        matches=list(UNIT.finditer(''.join(chars)))
        if len(matches)!=1:return None
        chosen=sources[matches[0].start():matches[0].end()];spans=[]
        for token,i in chosen:
            if spans and spans[-1].token_id==token.id and spans[-1].end==i:spans[-1].end=i+1
            else:spans.append(span(token,i,i+1))
        return Selection(spans=spans,label_spans=labels,score=1,method='shared_header')

    def column(self,token,columns,schema):
        explicit=next((c for c in columns if c['field']==getattr(token,'column_field',None)),None)
        if explicit:return explicit
        aligned=[c for c in columns if c.get('left_anchor') is not None and schema.get(c['field']) and schema[c['field']].kind=='text' and abs(box(token)[0]-c['left_anchor'])<self.height*.6]
        if len(aligned)==1:return aligned[0]
        return min(columns,key=lambda c:abs(c['x']-center(token)[0]))

    def tables(self,labels,item_schema,document_type=None):
        if not labels:return [],{},set()
        labels=[dict(l) for l in labels]
        if not any(l['field']=='quantity' for l in labels):
            for label in labels:
                if label['field']!='unit':continue
                t=self.tokens[label['token_id']]
                candidates=[o for o in self.document.tokens if o.page==t.page and 0<box(o)[1]-box(t)[3]<self.height*8 and max(box(o)[0],box(t)[0])<min(box(o)[2],box(t)[2])]
                if any(value_spans(o,'number','quantity') and value_spans(o,'unit','unit') for o in candidates):label['field']='quantity'
        rows=[];totals={};used=set()
        # Cluster column labels by page and near-equal vertical band.
        bands=[]
        for label in sorted(labels,key=lambda x:(self.tokens[x['token_id']].page,box(self.tokens[x['token_id']])[1])):
            t=self.tokens[label['token_id']]
            band=next((g for g in bands if g[0]['page']==t.page and (any(abs(v['y']-box(t)[1])<self.height*1.5 for v in g) or any(v['field']==label['field'] and 0<box(t)[1]-v['y'] and box(t)[1]-box(self.tokens[v['token_id']])[3]<self.height*.8 and abs(center(self.tokens[v['token_id']])[0]-center(t)[0])<self.height*1.8 for v in g))),None)
            entry={**label,'page':t.page,'y':box(t)[1]}
            if band is None:bands.append([entry])
            else:band.append(entry)
        # Adjacent header tiers belong to one table when there are no data cells
        # between them. Keep lower leaf headings over their spanning parent.
        merged=[];parent_header_ids=set()
        for band in bands:
            previous=merged[-1] if merged else None
            top=min(v['y'] for v in band)
            bottom=max(box(self.tokens[v['token_id']])[3] for v in previous) if previous else 0
            between=[t for t in self.document.tokens if previous and t.page==band[0]['page'] and bottom<box(t)[1]<top and re.fullmatch(r'\s*[$€£]?\d[\d,. ]*\s*',t.text)]
            if previous and previous[0]['page']==band[0]['page'] and 0<=top-bottom<self.height*3 and len({v['field'] for v in band})>=2 and len({v['field'] for v in previous})>=2 and not between:
                lower_fields={v['field'] for v in band}
                parent_header_ids.update(v['token_id'] for v in previous if v['field'] in lower_fields)
                merged[-1]=[v for v in previous if v['field'] not in lower_fields]+band
            else:merged.append(band)
        bands=[g for g in merged if len({x['field'] for x in g})>=2 and {x['field'] for x in g}&{'description','product_code','package_count','quantity'}]
        for band in bands:
            fields={x['field'] for x in band}
            if len(fields)<2 or not fields & {'description','product_code','package_count','quantity'}:continue
            if document_type=='commercial_invoice' and not fields & {'description','product_code','quantity','unit_price','amount'}:
                from .domain import semantic_label
                heading_y=median(x['y'] for x in band);page=band[0]['page']
                headings=[t for t in self.document.tokens if t.page==page and abs(box(t)[1]-heading_y)<self.height*1.5]
                roles={found[0] for t in headings if (found:=semantic_label(t.text))}
                if {'container_number','seal_number'}<=roles and any({'description','product_code'}&{x['field'] for x in other} for other in bands if other is not band):
                    next_y=min([g[0]['y'] for g in bands if g[0]['page']==page and g[0]['y']>heading_y+self.height*1.5]+[float('inf')])
                    region=[t for t in self.document.tokens if t.page==page and heading_y-self.height<box(t)[1]<next_y]
                    self.auxiliary_tables.append({'kind':'container_packing_table','status':'review','reason':'separate_container_table_is_not_additional_invoice_goods','header_evidence':[span(t).model_dump() for t in headings],'region_ocr_evidence':[span(t).model_dump() for t in region]})
                    continue
            cols=[]
            for field in fields:
                refs=[x for x in band if x['field']==field]
                ts=[self.tokens[x['token_id']] for x in refs]
                cols.append({'field':field,'left_anchor':median(box(self.tokens[v['token_id']])[0] for v in refs) if all(v['start']==0 and v['end']==len(self.tokens[v['token_id']].text) for v in refs) else None,'left':min(box(t)[0] for t in ts),'right':max(box(t)[2] for t in ts),'x':median(label_center(self.tokens[v['token_id']],v['start'],v['end'])[0] for v in refs),'labels':[span(self.tokens[x['token_id']],x['start'],x['end']) for x in refs]})
            for c in cols:
                if c['field']=='unit':
                    matches=[q for q in cols if q['field']=='quantity' and abs(q['x']-c['x'])<self.height]
                    if len(matches)==1:matches[0]['labels'] += [s for s in c['labels'] if s not in matches[0]['labels']]
            cols=[c for c in cols if not(c['field']=='unit' and any(q['field']=='quantity' and abs(q['x']-c['x'])<self.height for q in cols))]
            # Unmapped headings still delimit columns. Their values must not be
            # swallowed by the nearest recognized semantic column.
            header_ids={x['token_id'] for x in band}
            header_y=median(box(self.tokens[x['token_id']])[1] for x in band)
            for token in self.document.tokens:
                if token.page!=band[0]['page'] or token.id in header_ids or token.id in parent_header_ids:continue
                if abs(box(token)[1]-header_y)>self.height*.8:continue
                if not token.text.strip() or re.fullmatch(r'[\d\s.,+-]+',token.text):continue
                x=center(token)[0]
                if any(abs(c['x']-x)<self.height*1.8 for c in cols):continue
                cols.append({'field':'_unmapped_'+token.id,'x':x,'labels':[]})
            cols.sort(key=lambda c:c['x'])
            top=max(box(self.tokens[x['token_id']])[3] for x in band);page=band[0]['page']
            next_band=min([g[0]['y'] for g in bands if g[0]['page']==page and g[0]['y']>top]+[float('inf')])
            body=[t for t in self.document.tokens if t.page==page and t.id not in header_ids and box(t)[1]>top-self.height*.9 and box(t)[1]<next_band]
            # A total row closes this goods table. Footer charge tables must not
            # create distant row anchors that absorb cargo into the total.
            total_y=min([box(t)[1] for t in body if re.match(r'(?i)^\s*(?:(?:grand|consignment)\s+)?totals?\b',t.text)]+[float('inf')])
            settlements=[]
            if document_type=='commercial_invoice' and any(c['field']=='amount' for c in cols):
                for summary in body:
                    if not re.match(r'(?i)^\s*\d+(?:[.,]\d+)?\s*(?:%|PRC|PCT|PERCENT)\s+OF\s+(?:THE\s+)?(?:TOTAL\s+)?AMOUNT\b',summary.text):continue
                    clauses=[t for t in body if 0<box(t)[1]-box(summary)[3]<self.height*8 and abs(box(t)[0]-box(summary)[0])<self.height and re.match(r'(?i)^\s*\(?\d+(?:[.,]\d+)?\s*(?:%|PRC|PCT|PERCENT)\s+(?:TO\s+BE\s+)?PAID\b',t.text)]
                    aligned=[]
                    for caption in [summary,*clauses]:
                        amounts=[t for t in body if abs(center(t)[1]-center(caption)[1])<self.height*.8 and box(t)[0]>box(caption)[2] and self.column(t,cols,item_schema)['field']=='amount' and value_spans(t,'number','amount')]
                        if amounts:aligned.append((caption,amounts))
                    if len(clauses)>=2 and len(aligned)>=3:
                        settlements.append(box(summary)[1])
                        self.diagnostics.append({'kind':'payment_settlement_section','reason':'payment_schedule_is_not_goods_rows','status':'review','header_evidence':[span(summary).model_dump()],'region_ocr_evidence':[span(t).model_dump() for t in body if box(t)[1]>=box(summary)[1]]})
            body_end_y=min([total_y,*settlements])
            for section in body:
                starts_section=bool(re.match(r'(?i)^\s*(?:(?:I|we)\s+(?:hereby\s+)?(?:declare|certify)\b|reason\s+for\s+return\s*[:：])',section.text))
                if not starts_section:continue
                # Require a preceding populated cargo row and no numeric table cell
                # beside the section caption before treating it as a table boundary.
                previous=[t for t in body if box(t)[3]<box(section)[1] and value_spans(t,'number','quantity')]
                valid_row=any(len({self.column(o,cols,item_schema)['field'] for o in previous if abs(center(o)[1]-center(t)[1])<self.height*.8 and item_schema.get(self.column(o,cols,item_schema)['field']) and item_schema[self.column(o,cols,item_schema)['field']].kind=='number'})>=2 for t in previous)
                beside=any(t.id!=section.id and abs(center(t)[1]-center(section)[1])<self.height*.8 and re.fullmatch(r'\s*[$€£¥₩]?\d[\d., ]*\s*',t.text) for t in body)
                if valid_row and not beside:body_end_y=min(body_end_y,box(section)[1])

            identity=[c for c in cols if c['field'] in {'description','product_code'}]
            if document_type=='commercial_invoice' and identity and any(c['field']=='amount' for c in cols):
                charge_captions=[t for t in body if re.fullmatch(r'(?i)\s*(?:freight|shipping(?:\s+charges?)?|insurance|discount|tax|vat)\s*[:：]\s*',t.text) and box(t)[0]>max(c.get('right',c['x']) for c in identity)+self.height]
                for caption in charge_captions:
                    same_line=[t for t in body if abs(center(t)[1]-center(caption)[1])<self.height*.8 and t.id!=caption.id]
                    has_goods=any(self.column(t,cols,item_schema)['field'] in {'description','product_code'} for t in same_line)
                    has_amount=any(self.column(t,cols,item_schema)['field']=='amount' and value_spans(t,'number','amount') for t in same_line)
                    if has_amount and not has_goods:body_end_y=min(body_end_y,box(caption)[1])
            # Charges close the goods body, but are not aggregate goods rows.
            # Keep the real total boundary separate so a freight value cannot
            # be reintroduced as a new item during aggregate-row handling.
            aggregate_tokens=[t for t in body if abs(box(t)[1]-total_y)<self.height*.8]
            body=[t for t in body if box(t)[1]<body_end_y-self.height*.8]
            expanded=[]
            for token in body:
                # OCR sometimes merges a description and the neighboring weight
                # cell. Split only an explicit measure suffix that geometrically
                # occupies the adjacent measure column; retain exact char offsets.
                tail=re.search(r'\s+(\d+(?:[.,]\d+)*\s*[A-Za-z³3/]+)\s*$',token.text)
                if tail and value_spans(token,'unit','weight',tail.start(1),tail.end(1)):
                    l,u,r,b=box(token);n=max(1,len(token.text));cut=l+(r-l)*tail.start(1)/n
                    left_col=min(cols,key=lambda c:abs(c['x']-(l+cut)/2))
                    right_col=min(cols,key=lambda c:abs(c['x']-(cut+r)/2))
                    unit_spans=value_spans(token,'unit','weight',tail.start(1),tail.end(1))
                    unit=normalize(token.text[unit_spans[0].start:unit_spans[0].end],'unit')[0]
                    unit_matches=unit in {'kg','g','lb','t'} if right_col['field'] in {'gross_weight','net_weight'} else unit in {'m3','ft3'} if right_col['field']=='volume' else False
                    if left_col['field']=='description' and unit_matches and cols.index(right_col)==cols.index(left_col)+1 and cut>left_col['x']:
                        for start,end,col in [(0,tail.start(),left_col),(tail.start(1),tail.end(1),right_col)]:
                            a=l+(r-l)*start/n;z=l+(r-l)*end/n
                            expanded.append(SimpleNamespace(id=token.id,page=token.page,text=token.text[start:end],bbox=[(a,u),(z,u),(z,b),(a,b)],confidence=token.confidence,source_start=start,column_field=col['field']))
                        continue
                matches=list(NUMBER.finditer(token.text))
                if len(matches)>1 and not re.sub(r'[\s$€£¥₩]','',NUMBER.sub('',token.text)):
                    parts=[];destinations=set()
                    for match in matches:
                        l,u,r,b=box(token);width=r-l;n=max(1,len(token.text));left=l+width*match.start()/n;right=l+width*match.end()/n
                        col=min(cols,key=lambda c:max(c.get('left',c['x'])-(left+right)/2,0,(left+right)/2-c.get('right',c['x'])));spec=item_schema.get(col['field'])
                        if not spec or spec.kind!='number':break
                        destinations.add(col['field'])
                        parts.append(SimpleNamespace(id=token.id,page=token.page,text=match.group(),bbox=[(left,u),(right,u),(right,b),(left,b)],confidence=token.confidence,source_start=match.start(),column_field=col['field']))
                    if len(parts)==len(matches) and len(destinations)==len(parts):expanded.extend(parts);continue
                expanded.append(token)
            body=expanded
            # Learn per-document text alignment from repeated rows. Short values
            # must not drift into a neighboring column merely because of width.
            for col in cols:
                spec=item_schema.get(col['field'])
                if not spec or spec.kind!='text':continue
                assigned=[t for t in body if min(cols,key=lambda c:abs(c['x']-center(t)[0]))['field']==col['field']]
                if len(assigned)<2:continue
                starts=[box(t)[0] for t in assigned];anchor=median(starts)
                if median(abs(v-anchor) for v in starts)<self.height*.5:col['left_anchor']=anchor
            lines=[]
            for t in sorted(body,key=lambda t:(center(t)[1],box(t)[0])):
                line=next((line for line in lines[-2:] if abs(median(center(x)[1] for x in line)-center(t)[1])<self.height*.8),None)
                if line is None:lines.append([t])
                else:line.append(t)
            # Complete rows constrain column order independently of word width.
            # Learn alignment only when every heading has a distinct cell and
            # multiple numeric columns corroborate the ordered assignment.
            ordered_starts={c['field']:[] for c in cols}
            for line in lines:
                ordered=sorted(line,key=lambda t:box(t)[0])
                if len(ordered)!=len(cols):continue
                if any(box(a)[2]>box(b)[0]+self.height*.2 for a,b in zip(ordered,ordered[1:])):continue
                numeric=[(t,c) for t,c in zip(ordered,cols) if item_schema.get(c['field']) and item_schema[c['field']].kind=='number']
                if len(numeric)<2 or not all(value_spans(t,'number',c['field']) for t,c in numeric):continue
                for t,c in zip(ordered,cols):ordered_starts[c['field']].append(box(t)[0])
            for c in cols:
                starts=ordered_starts[c['field']]
                if len(starts)>=2 and max(starts)-min(starts)<self.height*.8:
                    c['left_anchor']=median(starts)
            # Numeric cells on both sides can delimit a text column even when
            # OCR splits its first line into several boxes. The header's center
            # alone does not define the left edge of a wide description cell.
            for index,c in enumerate(cols[1:-1],1):
                if c['field']!='description':continue
                left,right=cols[index-1],cols[index+1];starts=[]
                for line in lines:
                    before=[t for t in line if abs(center(t)[0]-left['x'])<self.height*1.5 and re.fullmatch(r'\d+(?:[.,]\d+)?',t.text.strip())]
                    after=[t for t in line if abs(center(t)[0]-right['x'])<self.height*2 and value_spans(t,'number',right['field'])]
                    if len(before)!=1 or len(after)!=1:continue
                    middle=[t for t in line if box(t)[0]>box(before[0])[2] and box(t)[2]<box(after[0])[0] and re.search(r'[A-Za-z]',t.text)]
                    if middle:starts.append(min(box(t)[0] for t in middle))
                if len(starts)>=2 and max(starts)-min(starts)<self.height*.8:c['left_anchor']=median(starts)
            # Stable numeric columns establish row centers. Assign wrapped text
            # to the same row by relative vertical boundaries, not OCR line count.
            from .domain import semantic_label
            for index,line in enumerate(lines):
                aggregate=[t for t in line if semantic_label(t.text) and semantic_label(t.text)[0]=='quantity']
                if not aggregate:continue
                identities=[t for t in line if t not in aggregate and self.column(t,cols,item_schema)['field'] in {'description','product_code'} and not re.fullmatch(r'[\d\s.,+-]+',t.text)]
                if not identities:
                    lines=lines[:index];body=[t for prior in lines for t in prior];break
            anchors=[]
            for line in lines:
                numeric_cols=set();ys=[]
                for t in line:
                    col=self.column(t,cols,item_schema)
                    spec=item_schema.get(col['field'])
                    if spec and spec.kind=='number' and value_spans(t,'number',col['field']):numeric_cols.add(col['field']);ys.append(center(t)[1])
                if len(numeric_cols)>=2:anchors.append(median(ys))
            if anchors:
                groups=[[] for _ in anchors]
                extension=max(self.height*3,median([b-a for a,b in zip(anchors,anchors[1:])])/2 if len(anchors)>1 else self.height*3)
                for token in sorted(body,key=lambda t:(center(t)[1],box(t)[0])):
                    y=center(token)[1]
                    identity_continuation=False
                    role=self.column(token,cols,item_schema)['field']
                    if role in {'container_number','seal_number','marks'} and re.fullmatch(r'(?=.*\d)[A-Za-z0-9/-]+',token.text.strip()):
                        identity_continuation=any(self.column(prior,cols,item_schema)['field']==role and
                            0<y-center(prior)[1]<self.height*2.5 for prior in groups[-1])
                    if y>anchors[-1]+extension and not identity_continuation and not (y<anchors[-1]+self.height*4 and re.fullmatch(r'(?i)\s*\d+\s+(?:pkgs?|packages?|ctns?|cartons?)\s*',token.text)):continue
                    preceding=[i for i,a in enumerate(anchors) if a<=y+self.height*.8]
                    index=preceding[-1] if preceding else 0
                    groups[index].append(token)
                lines=[sorted(group,key=lambda t:(center(t)[1],box(t)[0])) for group in groups if group]
            if aggregate_tokens:lines.append(sorted(aggregate_tokens,key=lambda t:box(t)[0]))
            previous=None
            for line_index,line in enumerate(lines):
                cells={c['field']:[] for c in cols}
                total_tokens=[t for t in line if re.match(r'(?i)^\s*(?:(?:grand|consignment)\s+)?totals?\b',t.text)]
                # A named package/weight total defines its own scope and may use
                # a different grid. Only a bare TOTAL row inherits all columns.
                if total_tokens and not all(re.fullmatch(r'(?i)\s*(?:(?:grand|consignment)\s+)?totals?\s*[:：]?\s*',t.text) for t in total_tokens):break
                # A repeated quantity heading in the body with no product identity
                # is an aggregate row, not another item.
                from .domain import semantic_label
                aggregate=[t for t in line if semantic_label(t.text) and semantic_label(t.text)[0]=='quantity']
                if aggregate and previous:
                    identities=[t for t in line if t not in aggregate and self.column(t,cols,item_schema)['field'] in {'description','product_code'} and not re.fullmatch(r'[\d\s.,+-]+',t.text)]
                    if not identities:break
                for t in line:
                    col=self.column(t,cols,item_schema)
                    cells[col['field']].append(t)
                # A trailing measures-only line does not establish another cargo
                # item or an aggregate. Preserve it as an unassigned row rather
                # than manufacturing product identity or summing its values.
                measure_fields={'gross_weight','net_weight','volume','weight_unit','gross_weight_unit','net_weight_unit','volume_unit'}
                from .domain import structural_caption,semantic_label
                def body_value(token):
                    role=semantic_label(token.text)
                    return not structural_caption(token.text) and not (role and not token.text[role[2]:].strip(' :：#\t'))
                occupied={key for key,values in cells.items() if any(body_value(t) for t in values)}
                identity_fields={'description','product_code','hs_code','quantity','package_count','marks','container_number'}
                if not total_tokens and previous and line_index==len(lines)-1 and occupied and occupied<=measure_fields and any(previous['row'].get(key) and previous['row'][key].spans for key in identity_fields):
                    self.diagnostics.append({'kind':'unassigned_measure_row','status':'review','reason':'trailing_measure_row_without_cargo_identity_or_total_label',
                        'header_evidence':[s.model_dump() for c in cols for s in c['labels']],
                        'region_ocr_evidence':[span(t).model_dump() for t in line]})
                    used.update(t.id for t in line)
                    continue
                # Require a structural row: at least two occupied columns and a numeric cargo cell.
                numeric=sum(bool(value_spans(t,'number',key)) for key,ts in cells.items() if item_schema.get(key) and item_schema[key].kind=='number' for t in ts)
                if not total_tokens and (sum(bool(v) for v in cells.values())<2 or not numeric):
                    unit_cells=cells.get('quantity',[]) or cells.get('unit',[])
                    if previous and unit_cells and all(value_spans(t,'unit','unit') for t in unit_cells) and center(unit_cells[0])[1]-previous['y']<self.height*2.5:
                        col=next(c for c in cols if c['field'] in {'quantity','unit'})
                        if previous['row'].get('quantity') and 'unit' in item_schema:
                            previous['row']['unit']=self.select(unit_cells,item_schema['unit'],'unit',col['labels'],'table')
                            used.update(t.id for t in unit_cells)
                    if previous and len(line)<=2 and all(abs(center(t)[0]-cols[0]['x'])<self.height*5 for t in line) and center(line[0])[1]-previous['y']<self.height*2.5:
                        # Continuation only inside the already established first column.
                        key=cols[0]['field'];old=previous['row'].get(key)
                        if old and item_schema[key].kind=='text':old.spans += [span(t) for t in line];used.update(t.id for t in line)
                    continue
                row={}
                for col in cols:
                    key=col['field'];ts=[t for t in cells[key] if t not in total_tokens]
                    if not ts or key not in item_schema:continue
                    if key=='marks' and 'package_count' in item_schema and not cells.get('package_count'):
                        packaged=[t for t in ts if re.fullmatch(r'(?i)\s*\d+\s+(?:pkgs?|packages?|ctns?|cartons?)\s*',t.text)]
                        if len(packaged)==1:
                            source=packaged[0]
                            units=value_spans(source,'unit','package_type')
                            row['package_count']=self.select(packaged,item_schema['package_count'],'package_count',col['labels']+units,'table')
                            if 'package_type' in item_schema:row['package_type']=self.select(packaged,item_schema['package_type'],'package_type',col['labels'],'table')
                            ts=[t for t in ts if t is not source];used.add(source.id)
                            if not ts:continue
                    row[key]=self.select(ts,item_schema[key],key,col['labels'],"table")
                    if key in {'gross_weight','net_weight','volume'}:
                        heading=' '.join(self.tokens[s.token_id].text[s.start:s.end] for s in col['labels'])
                        if re.search(r'(?i)(?:/|\bper)\s*$',heading):
                            last=self.tokens[col['labels'][-1].token_id]
                            basis=[t for t in self.document.tokens if t.page==last.page and 0<box(t)[1]-box(last)[1]<self.height*2 and -self.height*.3<box(t)[1]-box(last)[3]<self.height and max(box(t)[0],box(last)[0])<min(box(t)[2],box(last)[2]) and re.fullmatch(r'(?i)\s*(?:bags?|cartons?|ctns?|packages?|pkgs?|box(?:es)?|pallets?|drums?|pieces?|pcs?)\s*',t.text)]
                            if len(basis)==1:
                                heading+=' '+basis[0].text
                                row[key].label_spans.append(span(basis[0]))
                        if re.search(r'(?i)(?:/|\bper\s+)\s*(?:bags?|cartons?|ctns?|packages?|pkgs?|box(?:es)?|pallets?|drums?|pieces?|pcs?)\b',heading):
                            row[key].reasons.append('per_package_measure_is_not_row_total')
                    used.update(t.id for t in ts)
                    if key in {'gross_weight','net_weight','volume','package_count','quantity'}:
                        unit_key={'gross_weight':'gross_weight_unit','net_weight':'net_weight_unit','volume':'volume_unit','package_count':'package_type','quantity':'unit'}[key]
                        if unit_key in item_schema:
                            unit_ts=[t for t in ts if value_spans(t,'unit',unit_key)]
                            if key=='quantity' and not unit_ts:
                                from .domain import compound_labels
                                explicit_unit=any(any(f=='unit' for f,_,_ in compound_labels(self.tokens[s.token_id].text)) or (semantic_label(self.tokens[s.token_id].text) or (None,))[0]=='unit' for s in col['labels'])
                                if explicit_unit:
                                    unit_ts=[t for t in ts if re.fullmatch(r'[A-Za-z][A-Za-z³3/.]*',t.text.strip())]
                            header_ts=[self.tokens[s.token_id] for s in col['labels'] if value_spans(self.tokens[s.token_id],'unit',unit_key)]
                            if not unit_ts and not header_ts:
                                shared=self.shared_unit(col['labels'])
                                if shared:row[unit_key]=shared
                            if unit_ts or header_ts:row[unit_key]=self.select(unit_ts or header_ts,item_schema[unit_key],unit_key,col['labels'],"shared_header" if not unit_ts else "table")
                if total_tokens:
                    used.difference_update(t.id for t in line if t not in total_tokens)
                    for key,value in row.items():
                        if key in {'gross_weight','net_weight','weight_unit','gross_weight_unit','net_weight_unit','volume','volume_unit'}:
                            value.label_spans += [span(t) for t in total_tokens];totals[key]=value
                        if key=='package_count':
                            value.label_spans += [span(t) for t in total_tokens];totals['total_packages']=value
                    used.update(t.id for t in total_tokens)
                    break
                identity_cols=[c for c in cols if c['field'] in {'container_number','seal_number','marks'}]
                if any(c['field']=='container_number' for c in identity_cols):
                    container_col=next(c for c in identity_cols if c['field']=='container_number')
                    shared=[c for c in identity_cols if abs(c['x']-container_col['x'])<self.height]
                    if len(shared)>1:
                        sources=list({t.id:t for c in shared for t in cells[c['field']]}.values())
                        containers=[t for t in sources if re.fullmatch(r'[A-Z]{4}\d{7}',t.text.strip())]
                        if len(containers)==1:
                            row['container_number']=self.select(containers,item_schema['container_number'],'container_number',container_col['labels'],'table')
                            remaining=[t for t in sources if t.id!=containers[0].id]
                            for c in shared:
                                if c['field']!='container_number':row.pop(c['field'],None)
                            target=next((c for c in shared if c['field']=='seal_number'),None) if len(remaining)==1 else None
                            target=target or next((c for c in shared if c['field']=='marks'),None)
                            if target and remaining:row[target['field']]=self.select(remaining,item_schema[target['field']],target['field'],target['labels'],'table')
                rows.append(row);previous={'row':row,'y':center(line[0])[1]}
            used.update(x['token_id'] for x in band)
        return rows,totals,used

def unambiguous_date_prefix(text):
    match=re.match(r'\s*(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})\s+(\S.*)$',text)
    if not match or normalize(match.group(1),'date')[0] is None:return None
    suffix=match.group(2)
    if re.match(r'(?i)(?:to|through|until|and)\b|[-–—/]',suffix) or re.search(r'\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}',suffix):return None
    return match.start(1),match.end(1)
