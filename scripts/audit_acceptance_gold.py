"""Document transcription corrections using independent Azure annotations.
Original pre-inference drafts remain untouched. Both baseline and candidates
must be rescored against this same audited version; no engine output is gold.
"""
import json,hashlib
from pathlib import Path
from scripts.azure_acceptance import ROOT
CORRECTIONS={
 'PL_019919':{'fields.invoice_date':None,'fields.issue_date':'2001-03-24'},
 'BL_020293':{'fields.consignee':'DINCINNATI FINANCIAL'},
 'BL_017394':{'fields.on_board_date':'2013-07-26'},
 'NV_004233':{'fields.shipper':'Wripler Co., Ltd.','fields.port_of_discharge':'COLOCHEL, INDIA'},
 'NV_005134':{'fields.seller':'Dhungdo Timber Co., Ltd.'},
 'NV_003667':{'fields.port_of_loading':'IURRETA, SPAIN'},
 'NV_006981':{'fields.exporter':'NensDirect'},
 'NV_015042':{'fields.consignee':'IcctTwo Shared Services','fields.port_of_discharge':'SIMAO, CHINA'},
 'PL_001315':{'fields.invoice_number':'270278','items.0.description':'High And Low Angle Motor (LAT-0904A)'},
 'PL_002528':{'fields.shipper':'Invironmental Works','fields.exporter':'Invironmental Works'},
 'PL_011792':{'fields.consignee':'Enil Machinery Co. Ltd.'},
 'PL_016736':{'fields.letter_of_credit_number':'M8104361NS49032','fields.letter_of_credit_date':'2013-06-13','items.0.product_code':'70-4'},
 'PL_010961':{'fields.shipper':'JeadLight Technologies','fields.exporter':'JeadLight Technologies','fields.consignee':'KUNG ANG METAL CO. Ltd','fields.departure_date':'2017-05-16'},
 'PL_021849':{'fields.port_of_loading':'AJA, JAPAN','fields.consignee':'UmagineX Consulting LP'},
 'BL_019578':{'fields.shipper':'IKC ENTERPRISES'},
 'BL_004195':{'fields.document_reference':'9939.05-1769','fields.delivery_party':'RHARMAHEALTH LABS CO., LTD.','fields.carrier':'EPPTNESS MEDIA CO., LTD.'},
 'BL_014231':{'fields.delivery_party':'HERO MOTO CO., LTD.','fields.port_of_discharge':'ICCHODA, JAPAN'},
 'BL_009780':{'fields.forwarding_agent_number':'41-47-30-7142','fields.bill_to_party':'LOREA DAISHIN CO. LTD'},
}
def main():
 out=ROOT/'data/acceptance/gold-audited';out.mkdir(exist_ok=True);log=[]
 for p in (ROOT/'data/acceptance/gold').glob('*.json'):
  g=json.loads(p.read_text(encoding='utf-8'));ann=ROOT/'data/acceptance/documents'/p.stem/'annotation.json'
  for path,new in CORRECTIONS.get(p.stem.removeprefix('IMG_OCR_6_T_'),{}).items():
   cur=g;parts=path.split('.')
   for part in parts[:-1]:cur=cur[int(part)] if isinstance(cur,list) else cur[part]
   old=cur[parts[-1]];cur[parts[-1]]=new
   log.append({'document':p.stem,'path':path,'old':old,'new':new,'reason':'Draft transcription corrected against source image and independently supplied Azure bbox transcription','source_annotation_sha256':hashlib.sha256(ann.read_bytes()).hexdigest()})
  g['gold_version']='audited-v2';g['original_draft_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
  (out/p.name).write_text(json.dumps(g,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'outputs/acceptance/gold-corrections.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Independent transcription corrections:',len(log))
if __name__=='__main__':main()
