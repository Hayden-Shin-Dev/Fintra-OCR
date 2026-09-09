"""Create a separately frozen post-refactor synthetic challenge, never engine input."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fintraocr.schemas import SCHEMAS,ITEM_SCHEMAS,ALIASES
ROOT=Path(__file__).resolve().parents[1]

def main():
    dest=ROOT/'data/fresh';dest.mkdir(parents=True,exist_ok=True)
    cases=[
      ('fresh_invoice','commercial_invoice','COMMERCIAL INVOICE',[
        ('Commercial invoice no','CN-812','invoice_number'),('Invoice date','2025-02-18','issue_date'),
        ('Vendor','Granite Works Ltd.','seller'),('Sold to','Oak Logistics Ltd.','buyer'),
        ('B/L number','OC-4902','bill_of_lading_number'),('Currency','EUR','currency')],
       [('Line amount','amount'),('Description','description'),('Unit price','unit_price'),('Quantity','quantity'),('Unit','unit')],
       [['105.00','Valve body','15.00','7','pcs'],['144.00','Mounting kit','18.00','8','pcs']],
       [('Total amount','249.00','total_amount')]),
      ('fresh_packing','packing_list','PACKING LIST',[
        ('Packing list no','PK-508','packing_list_number'),('Issue date','2025-03-21','issue_date'),
        ('Shipper','Birch Materials Ltd.','shipper'),('Consignee','Pioneer Goods Ltd.','consignee'),
        ('Invoice reference','IV-770','invoice_number')],
       [('Gross weight','gross_weight'),('Goods description','description'),('Packages','package_count'),('Net weight','net_weight'),('Measurement','volume')],
       [['44.50 kg','Housing','3 PKG','40.00 kg','1.20 CBM'],['82.00 kg','Connector','5 PKG','77.50 kg','2.35 CBM']],
       [('Total packages','8','total_packages')]),
      ('fresh_bl','bill_of_lading','BILL OF LADING',[
        ('B/L number','SEA-774','bill_of_lading_number'),('Date of issue','2025-04-22','issue_date'),
        ('Consignee','Meadow Imports Ltd.','consignee'),('Shipper','Summit Export Ltd.','shipper'),
        ('Port of discharge','OSAKA','port_of_discharge'),('Port of loading','BUSAN','port_of_loading')],
       [('Measurement','volume'),('Cargo description','description'),('Gross weight','gross_weight'),('No. of packages','package_count')],
       [['2.40 CBM','Pump casing','300.00 kg','12 PKG'],['3.80 CBM','Drive unit','480.00 kg','16 PKG']],
       [('Total packages','28','total_packages'),('Carrier name','Harbor Shipping Ltd.','carrier')]),
    ]
    manifest=[]
    for ident,dtype,title,headers,columns,rows,footers in cases:
        folder=dest/ident;folder.mkdir(exist_ok=True)
        image=Image.new('RGB',(1800,1600),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',29)
        bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',40)
        draw.text((110,70),title,font=bold,fill='black')
        gold={'document_type':dtype,'fields':{k:None for k in SCHEMAS[dtype]},'items':[]}
        for i,(label,value,field) in enumerate(headers):
            x=110 if i%2 else 950;y=190+(i//2)*130
            draw.text((x,y),label,font=font,fill='black');draw.text((x,y+48),value,font=font,fill='black')
            gold['fields'][field]=value
        for alias,key in ALIASES[dtype].items():gold['fields'][alias]=gold['fields'][key]
        xs=[110,410,970,1290,1560] if len(columns)==5 else [110,440,1130,1470]
        for x,(label,key) in zip(xs,columns):draw.text((x,760),label,font=font,fill='black')
        draw.line((90,815,1730,815),fill='black',width=2)
        for i,values in enumerate(rows):
            item={k:None for k in ITEM_SCHEMAS[dtype]}
            for x,(label,key),value in zip(xs,columns,values):
                draw.text((x,870+i*140),value,font=font,fill='black')
                if key in ['gross_weight','net_weight']:
                    number,unit=value.split();item[key]=number;item[key+'_unit']=unit;item['weight_unit']=unit
                elif key=='volume':item[key]=value.split()[0];item['volume_unit']='m3'
                elif key=='package_count':item[key]=value.split()[0];item['package_type']='PKG'
                else:item[key]=value
            gold['items'].append(item)
        for i,(label,value,key) in enumerate(footers):
            draw.text((110,1230+i*110),label+': '+value,font=font,fill='black');gold['fields'][key]=value
        image.save(folder/'document.png')
        text=json.dumps(gold,ensure_ascii=False,indent=2);(folder/'gold.json').write_text(text,encoding='utf-8')
        manifest.append({'id':ident,'kind':dtype,'image':str(folder/'document.png'),'gold':str(folder/'gold.json'),'family':'permuted-columns-offset-header','language':'en','split':'fresh-frozen','gold_sha256':hashlib.sha256(text.encode()).hexdigest()})
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Frozen',len(manifest),'fresh cases before OCR/model inference')
if __name__=='__main__':main()
