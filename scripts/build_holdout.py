"""Create new synthetic layouts and gold BEFORE inference. Never imported by engine."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fintraocr.schemas import SCHEMAS,ITEM_SCHEMAS
from fintraocr.models import OCRDocument,Page,Token
ROOT=Path("data/holdout");ROOT.mkdir(parents=True,exist_ok=True)
FONT="C:/Windows/Fonts/malgun.ttf"

def make(name,kind,title,entries,rows,headers,variant):
    w,h=1700,2100
    image=Image.new("RGB",(w,h),"white");draw=ImageDraw.Draw(image)
    font=ImageFont.truetype(FONT,27);bold=ImageFont.truetype(FONT,38)
    tokens=[]
    def text(x,y,t,large=False):
        face=bold if large else font
        draw.text((x,y),t,fill="#152333",font=face)
        b=draw.textbbox((x,y),t,font=face)
        tokens.append(Token(id=f"g{len(tokens)}",page=1,text=t,bbox=[(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])],confidence=1))
    text(90,70,title,True)
    text(90,140,"Trade document / Original")
    fields={k:None for k in SCHEMAS[kind]}
    if variant==0:
        # Two-column blocks, alternating positions, label separate from value.
        for i,(key,label,value,normalized) in enumerate(entries):
            x=90+(i%2)*800;y=250+(i//2)*135
            text(x,y,label);text(x,y+48,value)
            if key:fields[key]=normalized
        table_y=300+((len(entries)+1)//2)*135
    else:
        # Single-column compact bilingual form, reverse header order and inline labels.
        for i,(key,label,value,normalized) in enumerate(reversed(entries)):
            text(110,250+i*65,label+": "+value)
            if key:fields[key]=normalized
        table_y=330+len(entries)*65
    draw.line((80,table_y-20,1620,table_y-20),fill="#364653",width=2)
    xs=[90,670,925,1130,1390]
    for x,(_,label) in zip(xs,headers):text(x,table_y,label)
    goldrows=[]
    for i,row in enumerate(rows):
        gold={k:None for k in ITEM_SCHEMAS[kind]}
        for x,(key,_),value in zip(xs,headers,row):
            text(x,table_y+80+i*85,value)
            gold[key]=value
        if "weight_unit" in gold and fields.get("weight_unit"): gold["weight_unit"]=fields["weight_unit"]
        goldrows.append(gold)
    text(90,table_y+100+len(rows)*85,"End of document")
    folder=ROOT/name;folder.mkdir(exist_ok=True);image.save(folder/"document.png")
    gold={"document_type":kind,"fields":fields,"items":goldrows}
    (folder/"gold.json").write_text(json.dumps(gold,ensure_ascii=False,indent=2),encoding="utf-8")
    doc=OCRDocument(pages=[Page(page=1,width=w,height=h,source=str((folder/"document.png").resolve()))],tokens=tokens,engine="renderer-oracle")
    (folder/"oracle.ocr.json").write_text(doc.model_dump_json(indent=2),encoding="utf-8")
    return {"id":name,"kind":kind,"image":str((folder/"document.png").resolve()),"gold":str((folder/"gold.json").resolve()),"family":"two-column" if variant==0 else "reverse-inline"}

manifest=[]
manifest.append(make("invoice_en","commercial_invoice","COMMERCIAL INVOICE",[
 ("buyer","Buyer","Willow Imports Ltd.","Willow Imports Ltd."),("invoice_number","Invoice reference","CI-ZX-7402","CI-ZX-7402"),
 ("seller","Sold by","Northbank Components Ltd.","Northbank Components Ltd."),("invoice_date","Issued on","2026-08-19","2026-08-19"),
 ("currency","Currency","EUR","EUR"),("total_amount","Grand total","847.25","847.25"),
 (None,"Booking reference","BK-99113",None),("payment_terms","Payment terms","Net 45 days","Net 45 days")],
 [["Steel bolts","12","pcs","15.50","186.00"],["Control panels","3","pcs","220.00","660.00"]],
 [("description","Description"),("quantity","Qty"),("unit","Unit"),("unit_price","Unit price"),("amount","Line amount")],0))
manifest.append(make("invoice_fr","commercial_invoice","FACTURE COMMERCIALE",[
 ("seller","Vendeur","Atelier Horizon SARL","Atelier Horizon SARL"),("buyer","Acheteur","Maison Rivage SAS","Maison Rivage SAS"),
 ("invoice_number","Facture numero","FC-882-Q","FC-882-Q"),("invoice_date","Date emission","2026-07-11","2026-07-11"),
 ("currency","Devise","EUR","EUR"),("total_amount","Montant total","921.40","921.40")],
 [["Pompes","7","pcs","40.20","281.40"],["Filtres","8","pcs","80.00","640.00"]],
 [("description","Designation"),("quantity","Quantite"),("unit","Unite"),("unit_price","Prix unitaire"),("amount","Montant")],1))
manifest.append(make("packing_en","packing_list","PACKING LIST",[
 ("packing_list_number","Packing reference","PL-670-Z","PL-670-Z"),("consignee","Consignee","Cedar Distribution Ltd.","Cedar Distribution Ltd."),
 ("shipper","Shipper","Eastshore Tools Ltd.","Eastshore Tools Ltd."),("packing_date","Packing date","2026-06-14","2026-06-14"),
 ("invoice_number","Related invoice","INV-448-M","INV-448-M"),("total_packages","Total packages","15","15"),
 ("gross_weight","Total gross weight","285.50","285.50"),("weight_unit","Weight unit","kg","kg")],
 [["Valve kits","6","24.50","20.00"],["Pump assemblies","9","261.00","250.00"]],
 [("description","Goods"),("package_count","Packages"),("gross_weight","Gross wt"),("net_weight","Net wt")],0))
manifest.append(make("packing_ko","packing_list","포장명세서 / PACKING LIST",[
 ("packing_list_number","포장명세서 번호","PK-391-T","PK-391-T"),("consignee","수하인","하늘무역 주식회사","하늘무역 주식회사"),
 ("shipper","송하인","바다정밀 주식회사","바다정밀 주식회사"),("packing_date","발행일","2026-05-03","2026-05-03"),
 ("total_packages","총 포장 수","11","11"),("gross_weight","총중량","172.80","172.80"),("weight_unit","중량 단위","kg","kg")],
 [["연결 장치","4","62.80","60.00"],["필터 부품","7","110.00","100.00"]],
 [("description","품명"),("package_count","포장 수"),("gross_weight","총중량"),("net_weight","순중량")],1))
manifest.append(make("bl_en","bill_of_lading","OCEAN BILL OF LADING",[
 ("bill_of_lading_number","B/L reference","BL-910-F","BL-910-F"),("consignee","Consignee","Silver Coast Trading Ltd.","Silver Coast Trading Ltd."),
 ("shipper","Shipper","Pine Harbor Industries Ltd.","Pine Harbor Industries Ltd."),("notify_party","Notify party","Aster Customs Ltd.","Aster Customs Ltd."),
 ("vessel","Vessel","OCEAN LANTERN","OCEAN LANTERN"),("voyage","Voyage","072E","072E"),
 ("port_of_loading","Port of loading","BUSAN","BUSAN"),("port_of_discharge","Port of discharge","ROTTERDAM","ROTTERDAM"),
 ("issue_date","Date of issue","2026-08-09","2026-08-09"),("on_board_date","Shipped on board","2026-08-07","2026-08-07")],
 [["Machinery parts","18","425.20"]],[("description","Cargo description"),("package_count","Packages"),("gross_weight","Gross weight")],0))
manifest.append(make("bl_es","bill_of_lading","CONOCIMIENTO DE EMBARQUE",[
 ("bill_of_lading_number","Numero B/L","BL-287-R","BL-287-R"),("consignee","Consignatario","Puerto Verde SL","Puerto Verde SL"),
 ("shipper","Cargador","Metal Costa SA","Metal Costa SA"),("vessel","Buque","ISLA CLARA","ISLA CLARA"),
 ("port_of_loading","Puerto de carga","VALENCIA","VALENCIA"),("port_of_discharge","Puerto de descarga","INCHEON","INCHEON"),
 ("issue_date","Fecha emision","2026-04-12","2026-04-12"),("freight_terms","Flete","PREPAID","PREPAID")],
 [["Repuestos","25","608.40"]],[("description","Descripcion"),("package_count","Bultos"),("gross_weight","Peso bruto")],1))
(ROOT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("Created",len(manifest),"synthetic unseen fixtures; engine never reads gold")
