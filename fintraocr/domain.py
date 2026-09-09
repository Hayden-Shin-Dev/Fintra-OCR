"""Auditable trade-label vocabulary: proposes semantics, never selects a value.

All entries describe document concepts, not companies, fixtures or coordinates.
Vocabulary matches require an entire label (or the prefix before a colon).
Final acceptance additionally requires structural association and type validation.
"""
import re
import unicodedata
from functools import lru_cache

@lru_cache(maxsize=32768)
def key(text):
    text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
    return re.sub(r'[^\w]','',text)

TERMS={
 'seller':['seller','sold by','vendor','vendeur','vendedor','판매자','매도인'],
 'exporter':['exporter','exportateur','exportador','수출자'],
 'buyer':['buyer','sold to','purchaser','acheteur','comprador','구매자','매수인'],
 'shipper':['shipper','consignor','cargador','expediteur','송하인'],
 'consignee':['consignee','ship to','consignatario','destinataire','수하인'],
 'notify_party':['notify party','notify','통지처'],
 'delivery_party':['for delivery to','delivery to','for delivery of goods please apply to','party to contact for cargo release'],
 'bill_to_party':['third party bill to','bill to'],
 'quotation_number':['quote no','quotation no','quotation number'],
 'proforma_invoice_number':['proforma invoice number','proforma invoice no','pro forma invoice no','p/i no'],
 'invoice_number':['invoice number','invoice no','invoice reference','related invoice','commercial invoice no','facture numero','numero de facture','numero de factura','송장 번호'],
 'packing_list_number':['packing list number','packing list no','packing reference','packing no','포장명세서 번호'],
 'bill_of_lading_number':['bill of lading number','bill of lading no','b/l no','b/l number','b/l reference','numero b/l','선하증권 번호'],
 'booking_number':['booking no','booking number','booking reference'],
 'purchase_order_number':['purchase order number','purchase order no','p/o no','po number','주문 번호'],
 'buyer_reference':['buyer reference','buyers reference',"buyer's ref"],
 'document_reference':['reference','other references','export references',"shipper's ref","shipper's reference",'shipper reference'],
 'issue_date':['issued on','date of issue','issue date','dated','date emission','date demission','fecha emision','fecha de emision','발행일'],
 'issue_place':['issued at','place of issue'],
 'shipment_date':['date shipped','shipment date'],
 'invoice_date':['invoice date','date of invoice'],
 'packing_date':['packing date','packing list date'],
 'departure_date':['sailing on or about','sailing of or about','departure date','date of departure','출항일'],
 'on_board_date':['shipped on board','laden on board','laden on board the vessel','on board date','shipped on board date','선적일'],
 'currency':['currency','devise','moneda','통화'],
 'total_amount':['total invoice value','grand total','total amount','invoice total','montant total','importe total','total'],
 'subtotal':['subtotal','sub total'], 'tax':['tax','vat','tax amount'],
 'payment_terms':['payment terms','terms / method of payment','terms of payment','terms of delivery and payment','terms of delivery and payment due date','결제 조건'],
 'incoterms':['incoterms','delivery terms','terms of delivery'],
 'vessel':['vessel','vessel name','ocean vessel','vessel / aircraft','export carrier (vessel)','buque','navire','선박명'],
 'voyage':['voyage','voyage no','voyage number','voy. no'],
 'carrier':['trucking co.', 'trucking company','carrier','carrier name','as carrier'],
 'mode_of_transport':['pre carriage by','pre-carriage by','mode of initial carriage','mode of transport','method of dispatch'],
 'routing_instructions':['domestic routing/export instructions'],
 'movement_type':['type of movement','type of shipment'],
 'freight_payable_at':['freight payable at'],
 'forwarding_agent':['forwarding agent'],
 'forwarding_agent_number':['forwarding agent/fmc no','forwarding agent fmc no','fmc no'],
 'declared_value':['declared value'],
 'port_of_loading':['port of loading','port & country of dispatch','from(port of loading)','puerto de carga','선적항'],
 'port_of_discharge':['port of discharge','puerto de descarga','양륙항'],
 'place_of_receipt':['place of receipt','place of initial receipt','place of receipt by pre-carrier'],
 'place_of_delivery':['place of delivery','place of delivery by carrier','final destination',"final destination for the merchant's reference only",'to(final destination)'],
 'freight_terms':['freight terms','freight','flete'],
 'country_of_origin':['country of origin','country of origin of goods','point and country of origin'],
 'country_of_destination':['country of final destination','country of destination'],
 'letter_of_credit_issuing_bank':['l/c issuing bank','letter of credit issuing bank'],
 'letter_of_credit_number':['letter of credit no','letter of credit number','l/c no'],
 'insurance_policy_number':['marine cover policy no','insurance policy number','policy no'],
 'description':['product description','item description','description','description of goods','goods description','goods','cargo description','description of package and goods','description of packages and goods','kind of packages description of goods','designation','descripcion','품명'],
 'quantity':['quantity','qty','unit quantity','q-ty of sets','qty of sets','quantity of sets','quantite','cantidad','수량'],
 'unit':['unit','unit type','unite','unidad','단위','pcs/set/other'],
 'unit_price':['price per unit','unit value','unit price','price','prix unitaire','precio unitario','단가'],
 'amount':['total per item','amount','line amount','montant','importe','금액'],
 'product_size':['size','product size','taille','talla','사이즈'],
 'material':['material','materials','composition','소재'],
 'color':['colour','color','색상'],
 'shipping_origin':['ship from'],
 'product_code':['code','part number','product code','item code','sku'],
 'hs_code':['hs code','tariff code'],
 'marks':['marks and number of','marks and number of pkgs','marks and numbers','marks & numbers','marks & nos.','shipping marks','shipping mark','marks','marks & nos/cont, nos'],
 'package_count':['packages','no of packages','no of pkgs','number of packages','no of pkgs or shipping units','number of packages or shipping units','no & kind of packages','no & kinds of containers or pkgs','no of containers or pkgs','bultos','포장수'],
 'total_packages':['total packages','total number of pkgs','total number of packages','total cartons','total ctns','total number of containers or other packages or units received by the carrier (inwards)','총 포장 수'],
 'gross_weight':['gross weight','gross wt','gross','total gross weight','peso bruto','총중량'],
 'net_weight':['net weight','total net weight','net wt','nett','quantity or net weight','poids net','peso neto','순중량'],
 'weight_unit':['weight unit','중량단위'],
 'volume':['cbm','measurement','measurements','volume','cubic measurement'],
 'volume_unit':['volume unit'],
 'container_number':['container number','container no'],
 'seal_number':['seal number','seal no'],
}
TERM_PREFIXES=[(field,term,re.compile(re.escape(term)+r'(?!\w)',re.I)) for field,terms in TERMS.items() for term in terms]
TERM_MATCHES={field:tuple(re.compile(r'(?<!\w)'+re.escape(term)+r'(?!\w)',re.I) for term in terms) for field,terms in TERMS.items()}
LOOKUP={key(term):field for field,terms in TERMS.items() for term in terms}
TITLE={
 'commercial_invoice':['commercial invoice','invoice','facture commerciale','factura comercial','상업송장'],
 'packing_list':['packing list','packinglist','liste de colisage','lista de empaque','포장명세서','포장명세서/packinglist'],
 'bill_of_lading':['bill of lading','ocean bill of lading','conocimiento de embarque','connaissement','선하증권'],
}
def _basic_structural_caption(text):
    # The count of issued copies is not the transport document identifier.
    if re.fullmatch(r'(?i)\s*(?:no\.?|number)\s+of\s+(?:original\s+)?bills?\s+of\s+lading\s*[:：]?\s*',text):return True
    # Negotiability clauses state document conditions, not a party identity.
    # Require a sentence beginning; a product description mentioning the term
    # elsewhere must not become a structural boundary.
    if re.match(r'(?i)^\s*not\s+negotiable\s+unless\s+consigned\b',text):return True
    if re.fullmatch(r'(?i)\s*(?:add\.?|address)\s*[&/]\s*(?:tel\.?|telephone)\s*',text):return True
    if re.match(r'(?i)^\s*(?:zip\s*code|postal\s*code|(?:tel(?:ephone)?|fax|phone)\s*[:).]|[TF]\)\s*[+\d])',text):return True
    if re.fullmatch(r'(?i)\s*no\.?\s+of\s+originals?\s*(?:b\(?s\)?\s*/\s*l)?\s*[:：]?\s*',text):return True
    return bool(re.fullmatch(r"(?i)\s*(?:remarks?|certification|signed by|by\s+x?|(?:driver['’]?s\s+)?signature|signatory company|name of authorized signatory|bank details|additional info|number of originals|freight class|company name|amount in words)\s*[:：]?\s*",text))

def structural_caption(text):
    if _basic_structural_caption(text) or non_trade_caption(text):return True
    if re.fullmatch(r"(?i)\s*(?:no\.?|number)\s+of\s+originals?\s+(?:bills?\s+of\s+lading|b\s*/\s*l)(?:['’]s|s)?\s*[:：]?\s*",text):return True
    if re.fullmatch(r"(?i)\s*forwarding\s+agent\s+references?\s*[:：]?\s*",text):return True
    if re.fullmatch(r"(?i)\s*(?:ocean\s+)?vessel\s*/\s*voyage\s*/\s*flag\s*[:：]?\s*",text):return True
    return False

def unsupported_reference_caption(text):
    """Known reference roles outside the frozen extraction contract.

    IEC (DGFT), GSTIN (GST portal), and Shipping Bill/SB (ICEGATE) are
    registration/customs references, not L/C, buyer, or B/L references.
    License exceptions describe export authorization, not a vessel voyage
    (https://www.bis.gov/licensing). Only the complete caption is excluded;
    license-related text in a goods description remains ordinary cargo text.
    Match the caption only; identifier shape never determines its role.
    """
    caption=re.split(r'[:：]',text,maxsplit=1)[0].strip()
    return bool(re.fullmatch(r'(?i)(?:IEC(?:\s+(?:no\.?|number|code))?|GSTIN(?:\s+(?:no\.?|number))?|(?:shipping\s+bill|S\s*/\s*B)\s+(?:no\.?|number)|(?:export\s+)?licen[cs]e\s+exception)',caption))

def document_heading_types(text):
    normalized=unicodedata.normalize('NFKC',text).strip()
    # Document-level qualifiers, not company/template identities. A reference
    # number suffix or a prose sentence is deliberately outside this grammar.
    qualifiers=r'(?:(?:sample|original|copy|straight|multimodal|ocean|non[- ]negotiable|master|container|customs|tax)\s+)*'
    return {kind for kind,terms in TITLE.items() if any(re.fullmatch(qualifiers+re.escape(term)+r'(?:\s+from)?\s*[:：]?',normalized,re.I) for term in terms)}

def document_heading(text):
    return bool(document_heading_types(text))
@lru_cache(maxsize=32768)
def semantic_label(text):
    freight_value=re.fullmatch(r'''(?i)\s*["“']?(freight\s*[:：]?\s+)(prepaid|collect)["”']?\s*''',text)
    if freight_value:return 'freight_terms',freight_value.start(1),freight_value.end(1)
    shipment_terms=re.match(r'(?i)^\s*shipment\s+terms\s*[:：]\s*(?=(?:EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\b)',text)
    if shipment_terms:return 'incoterms',0,shipment_terms.end()
    # Incoterm and named place qualify an explicitly labelled total. They are
    # not part of the money value, which still needs its own typed span.
    qualified_total=re.fullmatch(r'(?i)\s*total\s+amount\s+(?:EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\s+[^:：\d\n]{1,80}\s*[:：]\s*[$€£¥₩]?\s*\d[\d., ]*\s*',text)
    if qualified_total:return 'total_amount',0,max(text.find(':'),text.find('：'))
    delivery=re.match(r'(?i)^\s*for delivery of goods\s+(?:\w+\s+)?apply to\s*[:：]?\s*$',text)
    if delivery:return 'delivery_party',0,len(text)
    numbered=re.match(r'^\s*\d{1,3}[.)]\s*(?=[A-Za-z])',text)
    if numbered:
        found=semantic_label(text[numbered.end():])
        if found:return found[0],found[1]+numbered.end(),found[2]+numbered.end()
    for field,term,pattern in TERM_PREFIXES:
        locations={'port_of_loading','port_of_discharge','place_of_delivery','place_of_receipt'}
        if not (field.endswith('_number') or field.endswith('_date') or field in {'issue_place','voyage'}|locations):continue
        match=pattern.match(text)
        if not match:continue
        suffix=text[match.end():]
        gap=re.match(r'[.\s:：#]+',suffix)
        if not gap:continue
        value_start=match.end()+gap.end();value=text[value_start:]
        if field.endswith('_number') and not re.fullmatch(r'(?=.*\d)[\w./-]+',value):continue
        if field=='voyage' and not re.fullmatch(r'(?=.*\d)[\w./-]+',value):continue
        if field in locations:
            from .normalize import normalize
            if normalize(value,'country')[0] is None:continue
        if field.endswith('_date'):
            from .normalize import normalize
            if normalize(value,'date')[0] is None and not re.fullmatch(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',value):continue
        if value:return field,0,value_start
    marker=re.match(r'(?i)^\s*(p\.?o\.?|purchase order|invoice no\.?|b/l no\.?)\s*#\s*(\S.+|\S)$',text)
    if marker:
        role='purchase_order_number' if re.fullmatch(r'(?i)p\.?o\.?|purchase order',marker.group(1)) else ('invoice_number' if marker.group(1).lower().startswith('invoice') else 'bill_of_lading_number')
        return role,0,marker.start(2)
    prefix=re.split(r'[:：]',text,maxsplit=1)[0].strip()
    variants=[prefix,re.sub(r'\s*\([^)]*\)\s*','',prefix).strip()]
    for candidate in variants:
        field=LOOKUP.get(key(candidate))
        if field:return field,0,len(prefix)
    # A country name can follow its label without a colon. Its independent type
    # check prevents narrative text such as 'buyer should...' becoming a label.
    for field in ('country_of_origin','country_of_destination'):
        for term in sorted(TERMS[field],key=len,reverse=True):
            m=re.match(re.escape(term)+r'\s+(.+)$',text,re.I)
            if m:
                from .normalize import normalize
                if normalize(m.group(1),'country')[0] is not None:return field,0,m.start(1)
    return None


@lru_cache(maxsize=32768)
def compound_labels(text):
    """Explicit conjunctions only; no value-based role inference."""
    vessel_voyage=re.fullmatch(r'(?i)\s*(vessel\s*[:：]\s*)([^,;]+)[,;]\s*(voyage(?:\s+(?:no\.?|number))?\s*[:：#]?\s+)(\S[\w./-]*)\s*',text)
    if vessel_voyage:
        return [('vessel',vessel_voyage.start(1),vessel_voyage.end(1)),('voyage',vessel_voyage.start(3),vessel_voyage.end(3))]
    cargo=re.fullmatch(r'(?i)\s*(?:(marks?\s*(?:and|&)\s*(?:numbers?|nos?\.?))\s*)?\(?\s*(?:containers?|cont\.?)\s*(?:numbers?|nos?\.?)\s*(?:and|&|/)\s*seals?\s*(?:numbers?|nos?\.?)\s*\)?\s*',text)
    if cargo:
        roles=['container_number','seal_number']+(['marks'] if cargo.group(1) else [])
        return [(role,0,len(text)) for role in roles]
    if re.fullmatch(r'(?i)\s*marks?\s*(?:and|&)\s*(?:numbers?|nos?\.?)\s*/\s*(?:containers?|cont\.?)\s*[, .]*\s*(?:numbers?|nos?\.?)\s*',text):
        return [('marks',0,len(text)),('container_number',0,len(text))]
    numbered=re.match(r'^\s*\d{1,3}[.)]\s*(?=[A-Za-z])',text)
    if numbered:
        parts=compound_labels(text[numbered.end():])
        if parts:return [(f,a+numbered.end(),b+numbered.end()) for f,a,b in parts]
    parts=list(re.finditer(r'[^/&]+',text))
    roles=[]
    for part in parts:
        found=semantic_label(part.group().strip())
        if not found or found[0] not in {'shipper','exporter','seller','buyer','consignee','notify_party'}:roles=[];break
        start=part.start()+len(part.group())-len(part.group().lstrip())
        roles.append((found[0],start,part.end()-len(part.group())+len(part.group().rstrip())))
    if len(roles)>1:return [(role,0,len(text)) for role,_,_ in roles]
    issuance=re.match(r'(?i)^\s*place\s+and\s+date\s+of\s*issue\s*[:：]?\s*',text)
    if issuance:
        suffix=text[issuance.end():]
        from .normalize import normalize
        if not suffix or normalize(suffix,'date')[0] is not None or ':' in text[:issuance.end()] or '：' in text[:issuance.end()]:
            return [('issue_place',0,issuance.end()),('issue_date',0,issuance.end())]
    if re.fullmatch(r'(?i)\s*terms of delivery and payment(?: due date)?\s*',text):
        return [('incoterms',0,len(text)),('payment_terms',0,len(text))]
    m=re.fullmatch(r'(?i)\s*(?:bill of lading|b/l)\s+no\.?\s*/\s*p\.?o\.?\s+no\.?\s*',text)
    if m:return [('bill_of_lading_number',0,len(text)),('purchase_order_number',0,len(text))]
    if re.fullmatch(r'(?i)\s*forwarding agent\s*/\s*fmc\s+no\.?\s*',text):
        return [('forwarding_agent',0,len(text)),('forwarding_agent_number',0,len(text))]
    if re.fullmatch(r'(?i)\s*vessel\s*[/&]\s*voy(?:age)?\.?\s*(?:no\.?)?\s*',text):
        return [('vessel',0,len(text)),('voyage',0,len(text))]
    m=re.match(r'(?i)^\s*vessel\s*[/&]\s*voy(?:age)?(?:\.\s*|\s+)(?:no\.?\s+)?',text)
    if m:return [('vessel',0,m.end()),('voyage',0,m.end())]
    m=re.fullmatch(r'(?i)\s*(invoice|packing list|b/l|bill of lading|l/c)\s+(?:no\.?|number)\s*(?:and|&|/)\s*date\s*',text)
    if m:
        kind=m.group(1).lower();number={'invoice':'invoice_number','packing list':'packing_list_number','b/l':'bill_of_lading_number','bill of lading':'bill_of_lading_number','l/c':'letter_of_credit_number'}[kind]
        return [(number,0,len(text))]+([('invoice_date',0,len(text))] if kind=='invoice' else [('letter_of_credit_date',0,len(text))] if kind=='l/c' else [])
    # Multiple complete labels merged by OCR, with no intervening value text.
    cursor=0;merged=[]
    while cursor<len(text):
        gap=re.match(r'\s+',text[cursor:])
        if gap:cursor+=gap.end();continue
        matches=[]
        for field,term,pattern in TERM_PREFIXES:
            match=pattern.match(text,cursor)
            if match:matches.append((match.end()-cursor,field))
        if not matches:break
        length,field=max(matches)
        merged.append((field,cursor,cursor+length));cursor+=length
    if cursor==len(text) and len(merged)>1:return merged
    m=re.fullmatch(r'(?i)\s*(?:invoice\s+)?(?:no\.?|number)\s*[&/]\s*date\s+of\s+(invoice|packing list|b/l|bill of lading|l/c)\s*',text)
    if m:
        kind=m.group(1).lower();number={'invoice':'invoice_number','packing list':'packing_list_number','b/l':'bill_of_lading_number','bill of lading':'bill_of_lading_number','l/c':'letter_of_credit_number'}[kind]
        result=[(number,0,len(text))]
        if kind=='invoice':result.append(('invoice_date',0,len(text)))
        if kind=='l/c':result.append(('letter_of_credit_date',0,len(text)))
        return result
    if re.fullmatch(r"(?i)\s*(?:quantity|q['’]?ty)\s*[/&]\s*unit\s*",text):
        return [('quantity',0,len(text)),('unit',0,len(text))]
    m=re.match(r'(?i)^\s*(grand total|total amount|invoice total|total)\s*(?=[$€£¥₩]|\d)',text)
    if m:return [('total_amount',0,m.end())]
    return []

def has_inline_value(text):
    if re.search(r'(?i)\b(?:to be (?:completed|filled)|insert your|not provided|left blank)\b',text):return True
    found=semantic_label(text)
    return bool(found and text[found[2]:].strip(' :：#\t')) or any(text[end:].strip(' :：#\t') for _,_,end in compound_labels(text))


# Grounded semantic candidates: never repair or synthesize OCR value text.
def one_edit(a,b):
    if abs(len(a)-len(b))>1:return False
    if len(a)==len(b):return sum(x!=y for x,y in zip(a,b))==1
    if len(a)>len(b):a,b=b,a
    i=0
    while i<len(a) and a[i]==b[i]:i+=1
    return a[i:]==b[i+1:]

@lru_cache(maxsize=32768)
def caption_candidate(text):
    prefix=re.split(r'[:：]',text,maxsplit=1)[0].strip()
    caption=re.sub(r'^\s*\d{1,2}[.)]\s*','',prefix)
    # These complete role phrases establish their own meaning; Ref here
    # does not mean buyer reference or an agent's registration number.
    if re.fullmatch(r'(?i)(?:f\s*/\s*|forwarding\s+)agent\s+name\s*(?:&|and)\s+ref(?:erence)?\.?',caption):return ('forwarding_agent',0,len(prefix),False)
    if re.fullmatch(r'(?i)(?:clean\s+)?(?:shipped\s+)?on\s+board\s+on',caption):return ('on_board_date',0,len(prefix),False)
    candidate=key(caption)
    if not 8<=len(candidate)<=45 or len(caption.split())>6 or re.search(r'\d',caption):return None
    matches={field for term,field in LOOKUP.items() if len(term)>=8 and one_edit(candidate,term)}
    if len(matches)==1:return (matches.pop(),0,len(prefix),True)
    return None

def non_trade_caption(text):
    caption=re.split(r'[:：]',text,maxsplit=1)[0].strip()
    if re.fullmatch(r'(?i)importer(?:\s*\([^)]*\))?',caption):return 'importer_is_not_consignee_or_buyer'
    if re.fullmatch(r"(?i)(?:figure|fig\.?|illustration)\s+\d+[A-Za-z]?",caption):return 'publication_figure_caption'
    if re.fullmatch(r"(?i)(?:air\s*waybill|awb)(?:\s+(?:no\.?|number|#))?",caption):return 'air_waybill_is_not_bill_of_lading'
    if re.fullmatch(r"(?i)(?:reason\s+for\s+return|true\s+and\s+correct\.?)",caption):return 'return_or_attestation_is_not_trade_reference'
    return None

def attribution_narrative(text):
    return bool(re.search(r'(?i)\b(?:this\s+bill\s+of\s+lading\s+is\s+issued|carrier\s+named\s+here\w*|conditions\s+of\s+shipment)\b',text))

def carriage_contract_evidence(document, dtype):
    from .layout import span
    if dtype != 'bill_of_lading': return []
    for page in document.pages:
        tokens=[t for t in document.tokens if t.page==page.page]
        roles={}
        for token in tokens:
            label=semantic_label(token.text)
            if label:roles.setdefault(label[0],[]).append(token)
        required={'bill_of_lading_number','shipper','consignee','port_of_loading','port_of_discharge'}
        if not required.issubset(roles):continue
        # Independent contract language is evidence of carriage, not a field label.
        receipt=[t for t in tokens if re.search(r'(?i)\breceived\s+in\s+apparent\s+good\s+order\b',t.text)]
        originals=[t for t in tokens if re.search(r'(?i)\boriginal\s+bills?\s+of\s+lading\b',t.text)]
        if receipt and originals:
            return [span(roles[k][0]) for k in sorted(required)]+[span(receipt[0]),span(originals[0])]
    return []
