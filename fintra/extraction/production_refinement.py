"""Standalone typed and reading-order refinement for the production kernel."""
from dataclasses import replace
import re
from fintra.domain.schema import evidence, missing
from fintra.normalization.values import normalize_date
from .layout import Layout
def date_value(text):
    return text.strip() if normalize_date(text) is not None else None

def numeric_value(text):
    return text.strip() if re.fullmatch(r'\s*(?:(?:USD|EUR|GBP|JPY|CNY|KRW|US\$)\s*)?[$¥₩]?\s*[+-]?\d[\d,.]*(?:\s*(?:KG|KGS|G|PKG|PKGS|PCS|BOX|CTNS|CTN|EA))?\s*', text, re.I) and __import__('fintra.normalization.values', fromlist=['parse_amount']).parse_amount(text) is not None else None

def identifier_value(text):
    text = text.strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./-]*', text) or not re.search(r'\d', text) or date_value(text):
        return None
    if re.fullmatch(r'\d{2,5}-\d{3,5}-\d{3,5}', text):
        return None
    return text


def typed_refinement(result, document):
    layout=Layout(result)
    updates={}
    for name in ('invoice_number','bl_number','packing_list_number'):
        if not hasattr(document,name):continue
        field=getattr(document,name)
        if field.status!='extracted' or not field.value:continue
        text=str(field.value)
        if identifier_value(text):continue
        # Strip only demonstrable label contamination, not arbitrary identifiers.
        if not re.search(r'\b(?:NO|NUMBER|INVOICE|INV|BILL|BWL|LADING|LADIN|LADNG|INOOICE)\b',text,re.I):continue
        candidates=[token for token in text.split() if identifier_value(token)]
        if len(candidates)==1:
            updates[name]=replace(field,value=candidates[0],extraction_method='typed_identifier_from_existing_evidence')
    if hasattr(document,'weight_unit'):
        existing=document.weight_unit
        if existing.status!='extracted':
            gross=getattr(document,'gross_weight',None)
            sources=[]
            if gross and gross.value:sources=[(str(gross.value),gross)]
            for c in layout.cells:
                if re.fullmatch(r'(?:\d[\d.,]*\s*)?(?:KG|KGS|G|GRAM|GRAMS)',c.text,re.I):sources.append((c.text,layout.evidence([c])))
            candidates=[]
            for text,field in sources:
                match=re.search(r'(KG|KGS|G|GRAM|GRAMS)$',text,re.I)
                if match:
                    unit={'KGS':'KG','GRAM':'G','GRAMS':'G'}.get(match[1].upper(),match[1].upper())
                    candidates.append((unit,field))
            if candidates and len({u for u,_ in candidates})==1:
                unit,source=candidates[0]; updates['weight_unit']=replace(source,value=unit,extraction_method='explicit_weight_suffix')
    return replace(document,**updates)


def ordered_refinement(result,document):
    layout=Layout(result);updates={}
    # Keep the same duplicate-fragment suppression used by the document
    # layouts.  Re-reading a field bbox from the unfiltered Layout would
    # otherwise reintroduce Paddle's overlapping partial regions.
    from .production_engine import _regions
    retained_indices={region.index for region in _regions(result)}
    def reorder(field):
        if field.status!='extracted' or not field.bbox:return field
        # An inline label has already been removed from this value. Re-reading
        # its whole region would incorrectly put the label back into the value.
        if field.source_text is not None and str(field.value)!=field.source_text:return field
        xs=[p[0] for p in field.bbox];ys=[p[1] for p in field.bbox]
        box=(min(xs)/layout.width,min(ys)/layout.height,max(xs)/layout.width,max(ys)/layout.height)
        cells=[c for c in layout.cells if c.index in retained_indices and box[0]<=c.cx<=box[2] and box[1]<=c.cy<=box[3]]
        return layout.evidence(cells) if cells else field
    for name in ('seller','buyer','exporter','consignee','shipper','notify_party','goods_description','vessel','port_of_loading','port_of_discharge'):
        if hasattr(document,name):updates[name]=reorder(getattr(document,name))
    if hasattr(document,'items'):
        updates['items']=[replace(item,description=reorder(item.description)) for item in document.items]
    return replace(document,**updates)



