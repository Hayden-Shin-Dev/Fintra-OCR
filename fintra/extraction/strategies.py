"""Document-specific, evidence-only extraction candidates for parity evaluation.

The explicit layout strategy is experimental until independently reviewed gold
validates it. No recognition, checkpoint, document-id or filename dependencies.
"""
from __future__ import annotations
import re
from decimal import Decimal
from statistics import median

from fintra.domain.schema import CommercialInvoice,PackingList,BillOfLading,DocumentMetadata,LineItem,missing
from fintra.normalization.values import normalize_date, normalize_currency, parse_amount
from .layout import Layout, Span, canonical

ALIASES={
 'invoice_number':('INVOICE NO','INVOICE NUMBER','INV NO','NO AND DATE OF INVOICE'),
 'invoice_date':('INVOICE DATE','NO AND DATE OF INVOICE','DATE'),
 'packing_list_number':('PACKING LIST NO','PACKING LIST NUMBER'),
 'date':('DATE','PACKING DATE'),
 'seller':('SELLER','SHIPPER','SHIPPER EXPORTER','EXPORTER'),
 'buyer':('BUYER','CONSIGNEE','BUYER AND ADDRESS','FOR ACCOUNT'),
 'exporter':('EXPORTER','SELLER','SHIPPER'),
 'consignee':('CONSIGNEE','CONSIGNEE NOT NEGOTIABLE','BUYER'),
 'shipper':('SHIPPER','SHIPPER EXPORTER','EXPORTER'),
 'notify_party':('NOTIFY PARTY','NOTIFY'),
 'bl_number':('BILL OF LADING NO','BILL OF LADING NUMBER','BL NO','B L NO'),
 'shipment_date':('DATE SHIPPED','SHIPPED ON BOARD','ON BOARD DATE','SHIPMENT DATE'),
 'vessel':('VESSEL','OCEAN VESSEL','EXPORT CARRIER VESSEL'),
 'port_of_loading':('PORT OF LOADING','LOADING PORT'),
 'port_of_discharge':('PORT OF DISCHARGE','DISCHARGE PORT'),
 'total_amount':('GRAND TOTAL','TOTAL AMOUNT','INVOICE TOTAL','TOTAL VALUE','TOTAL'),
 'currency':('CURRENCY','CURRENCY CODE'),
 'package_count':('TOTAL PACKAGES','NO OF PKGS','NUMBER OF PACKAGES','TOTAL PKGS'),
 'gross_weight':('GROSS WEIGHT','TOTAL GROSS WEIGHT','G W'),
 'net_weight':('NET WEIGHT','TOTAL NET WEIGHT','N W'),
 'description':('DESCRIPTION OF GOODS','DESCRIPTION','COMMODITY','GOODS DESCRIPTION'),
 'quantity':('QUANTITY','QTY'), 'unit':('UNIT',),
 'unit_price':('UNIT PRICE','PRICE'), 'amount':('AMOUNT','VALUE'),
}

def date_value(text):
    return text.strip() if normalize_date(text) is not None else None

def numeric_value(text):
    # Reject arbitrary prose containing numbers; never concatenate separate values.
    if not re.fullmatch(r'\s*(?:(?:USD|EUR|GBP|JPY|CNY|KRW|US\$)\s*)?[$€£¥₩]?\s*[+-]?\d[\d,.]*(?:\s*(?:KG|KGS|G|PKG|PKGS|PCS|BOX|CTNS|CTN|EA))?\s*',text,re.I):return None
    return text.strip() if parse_amount(text) is not None else None

def identifier_value(text):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./-]*',text.strip()):return None
    if not re.search(r'\d',text) or date_value(text):return None
    # Three long numeric groups are usually a telephone/reference, not an invoice id.
    if re.fullmatch(r'\d{2,5}-\d{3,5}-\d{3,5}',text):return None
    return text.strip()


class DocumentExtractor:
    kind='Unknown'
    party_fields=()
    scalar_fields=()
    def __init__(self,result):
        self.result=result; self.layout=Layout(result)
        relevant=set(self.party_fields)|set(self.scalar_fields)|{'description','quantity','unit','unit_price','amount','gross_weight','net_weight','package_count','total_amount','notify_party','vessel','port_of_loading','port_of_discharge'}
        self.anchors=self.layout.anchors({k:v for k,v in ALIASES.items() if k in relevant})
        self.trace=[]

    def metadata(self):return DocumentMetadata(self.result.document_id,self.kind,source_file=self.result.source_file,extraction_status='extracted')

    def scalar(self,field):
        predicate=date_value if 'date' in field else identifier_value if field.endswith('number') else numeric_value if field in ('total_amount','gross_weight','net_weight','package_count') else lambda t:t.strip() if any(c.isalpha() for c in t) else None
        candidates=[]
        for anchor in self.anchors:
            if anchor.field!=field:continue
            if field=='total_amount' and anchor.span.cy<.35:continue
            for score,span,value in self.layout.candidates(anchor,self.anchors,predicate):
                if field=='total_amount':
                    # Footer totals outrank row-level totals, but not unit prices.
                    score+=span.cy+ (1.5 if canonical(anchor.alias)!='TOTAL' else 0)
                candidates.append((score,span,value,anchor.alias))
        self.trace.append({'field':field,'candidates':[{'score':round(c[0],4),'value':c[2],'region_indices':[r.index for r in c[1].cells],'anchor':c[3]} for c in sorted(candidates,key=lambda c:c[0],reverse=True)[:5]]})
        if candidates:
            _,span,value,_=max(candidates,key=lambda c:c[0]);return self.layout.evidence(span.cells,value)
        if field=='currency':
            codes=[(c,normalize_currency(c.text)) for c in self.layout.cells if re.fullmatch(r'USD|EUR|GBP|JPY|CNY|KRW|US\$',c.text,re.I)]
            if codes:
                # Repeated same codes are confirming evidence. Prefer footer when competing.
                cell,code=max(codes,key=lambda v:v[0].cy);return self.layout.evidence([cell],code)
        # Date fallback is constrained to upper document header and valid date type.
        if 'date' in field:
            spans=[s for s in self.layout.spans if s.box[0]>.48 and s.cy<.36 and date_value(s.text)]
            if spans:
                span=min(spans,key=lambda s:s.cy);return self.layout.evidence(span.cells)
        return missing()

    def party(self,field):
        anchors=[a for a in self.anchors if a.field==field and a.span.cy<.6]
        if not anchors:return missing()
        # Telephone subheadings are not the start of a party's organization block.
        anchors=[a for a in anchors if not any('PHONE' in c.text.upper() or 'FAX' in c.text.upper() for c in self.layout.cells if abs(c.cy-a.span.cy)<self.layout.line_height and a.span.box[0]-.02<c.cx<a.span.box[2]+.18)]
        if not anchors:return missing()
        anchor=max(anchors,key=lambda a:a.strength-a.span.cy*.2)
        x1=anchor.span.box[0]-.015
        competing=[a.span.box[0] for a in self.anchors if abs(a.span.cy-anchor.span.cy)<.15 and a.span.box[0]>anchor.span.box[2]+.06]
        x2=min(competing) if competing else min(1,x1+.46)
        lower=[a.span.cy for a in self.anchors if a.field!=field and a.span.cy>anchor.span.cy+self.layout.line_height and x1<=a.span.box[0]<x2-.03]
        bottom=min(lower) if lower else min(.65,anchor.span.box[3]+.16)
        label_ids={c.index for a in self.anchors for c in a.span.cells}
        cells=[c for c in self.layout.cells if c.page==anchor.span.cells[0].page and c.index not in label_ids and c.box[0]>=x1 and c.box[2]<=x2 and anchor.span.box[3]<=c.cy<bottom]
        lines=self.layout.group_lines(cells)
        if not lines:return missing()
        # Company canonical value excludes address/contact lines. Full block remains source_text/bbox.
        company=[]
        for line in lines:
            text=' '.join(c.text for c in line)
            if re.search(r'\bTEL|\bFAX|\bPHONE|\bSTREET|\bROAD|\bAVENUE|\bDRIVE|\bROOM|\bPOST|^\d',text,re.I):break
            if not company or re.search(r'\bCO\b|\bLTD\b|\bINC\b|\bLIMITED\b',text,re.I):company.extend(line)
            else:break
        if not company:company=lines[0]
        return self.layout.evidence(cells,self.layout.read(company),method='party_name_with_full_block_evidence')

    def table(self):
        fields={'description','quantity','unit','unit_price','amount'}
        headers=[a for a in self.anchors if a.field in fields and .25<a.span.cy<.8]
        if not headers:return []
        bands=[]
        for a in headers:
            band=next((b for b in bands if abs(median(x.span.cy for x in b)-a.span.cy)<self.layout.line_height*2.5),None)
            if band is None:bands.append([a])
            else:band.append(a)
        band=max(bands,key=lambda b:len({a.field for a in b}))
        chosen={}
        for a in sorted(band,key=lambda a:a.strength,reverse=True):chosen.setdefault(a.field,a)
        if 'description' not in chosen or not ({'quantity','amount'} & chosen.keys()):return []
        columns=sorted(chosen,key=lambda k:chosen[k].span.cx)
        centers=[chosen[k].span.cx for k in columns]
        cuts=[max(0,chosen[columns[0]].span.box[0]-.03)]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[min(1,centers[-1]+.16)]
        top=max(a.span.box[3] for a in chosen.values())
        totals=[a.span.box[1] for a in self.anchors if a.field=='total_amount' and a.span.box[1]>top]
        bottom=min(totals) if totals else .88
        cells=[c for c in self.layout.cells if top<c.cy<bottom and cuts[0]<=c.cx<=cuts[-1]]
        row_keys=[]
        quantity_idx=columns.index('quantity') if 'quantity' in columns else columns.index('amount')
        for c in cells:
            if cuts[quantity_idx]<=c.cx<cuts[quantity_idx+1] and numeric_value(c.text):
                if not row_keys or all(abs(c.cy-y)>self.layout.line_height*1.5 for y in row_keys):row_keys.append(c.cy)
        row_keys.sort()
        rows=[]
        for i,y in enumerate(row_keys):
            y1=top if i==0 else (row_keys[i-1]+y)/2
            y2=bottom if i==len(row_keys)-1 else (y+row_keys[i+1])/2
            values={}
            for j,name in enumerate(columns):
                selected=[c for c in cells if y1<=c.cy<y2 and cuts[j]<=c.cx<cuts[j+1]]
                if name in ('quantity','unit_price','amount'):
                    selected=[c for c in selected if numeric_value(c.text)]
                    if len(selected)>1:selected=[min(selected,key=lambda c:abs(c.cy-y))]
                values[name]=self.layout.evidence(selected)
            rows.append(LineItem(**values))
        return rows


class CommercialInvoiceExtractor(DocumentExtractor):
    kind='Commercial Invoice';party_fields=('seller','buyer');scalar_fields=('invoice_number','invoice_date','currency','total_amount')
    def extract(self):
        return CommercialInvoice(self.metadata(),**{f:self.scalar(f) for f in self.scalar_fields},**{f:self.party(f) for f in self.party_fields},items=self.table())

class PackingListExtractor(DocumentExtractor):
    kind='Packing List';party_fields=('exporter','consignee');scalar_fields=('packing_list_number','date','package_count','gross_weight','net_weight')
    def extract(self):
        values={f:self.scalar(f) for f in self.scalar_fields}
        gross=values['gross_weight']
        unit=missing()
        if gross.value:
            found=re.search(r'\b(KGS?|G)\b',str(gross.value),re.I)
            if found:
                from fintra.domain.schema import evidence
                unit=evidence(found[1].upper(),source_text=gross.source_text,bbox=gross.bbox)
        return PackingList(self.metadata(),**values,**{f:self.party(f) for f in self.party_fields},weight_unit=unit,items=self.table())

class BillOfLadingExtractor(DocumentExtractor):
    kind='B/L';party_fields=('shipper','consignee','notify_party');scalar_fields=('bl_number','vessel','port_of_loading','port_of_discharge','shipment_date','package_count','gross_weight')
    def extract(self):
        rows=self.table()
        from fintra.domain.schema import evidence
        descriptions=[i.description for i in rows if i.description.value]
        goods=evidence(' '.join(str(d.value) for d in descriptions),source_text=' '.join(str(d.source_text) for d in descriptions)) if descriptions else missing()
        return BillOfLading(self.metadata(),**{f:self.scalar(f) for f in self.scalar_fields},**{f:self.party(f) for f in self.party_fields},goods_description=goods)

STRATEGIES={'Commercial Invoice':CommercialInvoiceExtractor,'Packing List':PackingListExtractor,'B/L':BillOfLadingExtractor}
