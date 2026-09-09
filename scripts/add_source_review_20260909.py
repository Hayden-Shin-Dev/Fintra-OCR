"""Append source-only transcriptions. No engine predictions are read."""
import json
from scripts.azure_acceptance import ROOT

additions = {
 'IMG_OCR_6_T_NV_004306': {
  'fields': {'invoice_number':'678056','bill_of_lading_number':'HG434268','exporter':'Nillhouse Logistics','consignee':'Neltzer Hellrung','buyer':'Realty Partners','document_reference':'642-676-4311','buyer_reference':'83-45-02584','mode_of_transport':'DPMTH','country_of_origin':'SD','country_of_destination':'SN','vessel':'UNDINE','voyage':'V.648','payment_terms':'CREDIT','port_of_loading':'KISHIKU, JAPAN','departure_date':'2011-07-01','port_of_discharge':'GAOGANG, CHINA','place_of_delivery':'SIMOR, INDIA','insurance_policy_number':'685-928-3594','letter_of_credit_number':'91-48-39422','total_amount':'47915.20','currency':'JPY'},
  'items': [
   {'product_code':'82-544','description':'Pin, Shoulder Type, Skinless Type','hs_code':'3966.55','quantity':'53','unit':'Doz','unit_price':'87.26','amount':'241.31'},
   {'product_code':'84-759','description':'Ground Wire, TB1/AC1','hs_code':'4405.04','quantity':'8','unit':'pcs','unit_price':'97.26','amount':'725.39'},
   {'product_code':'77-085','description':'Surfactants','hs_code':'5820.92','quantity':'74','unit':'SM','unit_price':'99.59','amount':'8213.99'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions.','Same exporter-grid family, not a new layout. Page Total 9 and Consignment Total 7 do not establish package counts.','JPY is explicit despite dollar signs. Unknown units Doz and SM retain source spelling under the frozen contract.','No issue date is printed. Signatory company is not a transaction party.']},
 'IMG_OCR_6_T_PL_001904': {
  'fields': {'shipper':'Porthwestern Mutual','exporter':'Porthwestern Mutual','invoice_number':'04859-6449-2086','invoice_date':'2002-11-04','letter_of_credit_number':'M7003405NS88488','letter_of_credit_date':'2021-02-09','consignee':'Tamhwa Paper Co. Ltd.','notify_party':'FONTI Organization','port_of_loading':'ARACAJU, BRAZIL','place_of_delivery':'CANSO, CANADA','vessel':'BO YUN 588','departure_date':'2019-05-25','total_packages':'71','gross_weight':'75','gross_weight_unit':'kg','weight_unit':'kg'},
  'items': [
   {'description':'Valve, For Direction Selection','product_code':'90-3','quantity':'8','unit':'pcs','net_weight':'15','weight_unit':'kg','net_weight_unit':'kg','package_count':'66','package_type':'PKG'},
   {'description':'Cable Assembly, Special Purpose, Electrical. W5273204','product_code':'79-5','quantity':'9','unit':'Yard','net_weight':'43','weight_unit':'kg','net_weight_unit':'kg','package_count':'31','package_type':'PKG'},
   {'description':'Contactor, Electrical','product_code':'22-1','quantity':'3','unit':'SF','net_weight':'39','weight_unit':'kg','net_weight_unit':'kg','package_count':'54','package_type':'PKG'}],
  'unscored_source_fields': {'total_new_weight':'93 KG','packing_terms':'Unitary Packing'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same borderless goods/footer family.','Footer literally reads TOTAL NEW WEIGHT, not NET. Its intended meaning requires adjudication; no silent OCR correction or net-weight assertion. The development gold v2 treatment of this caption is disputed and not used as a rule here.','Unknown Yard and SF units retain their source spelling. Signed-by bank is not a shipper or seller.']},
 'IMG_OCR_6_T_BL_004919': {
  'fields': {'shipment_date':'2003-09-15','shipper':'ONFINITY FLIGHT GROUP','exporter':'ONFINITY FLIGHT GROUP','booking_number':'95254','document_reference':'182-101-6558','quotation_number':'56-65-99964','forwarding_agent_number':'96-15-92-1005','shipping_origin':'SYRIA','consignee':'ANITY FI SOLUTIONS','delivery_party':'QOINTER POOLS AND SPAS','notify_party':'GEBAR HOSPITALITY','bill_to_party':'FONG SEO TRADING CO.','vessel':'ATLANTIC OCEAN','port_of_loading':'AJI, JAPAN','port_of_discharge':'HUANGYAN, CHINA','freight_terms':'PREPAID','gross_weight':'81','gross_weight_unit':'kg','weight_unit':'kg','volume':'661.61','volume_unit':'m3','issue_place':'MARIN, PORTUGAL','issue_date':'2020-06-24'},
  'items': [
   {'container_number':'DLSU4695194','marks':'U815248','package_count':'74','package_type':'PKG','description':'FILTER ASSEMBLY, FOR FLUID','gross_weight':'24','weight_unit':'kg','gross_weight_unit':'kg','volume':'537.82','volume_unit':'m3'},
   {'package_count':'85','package_type':'PKG','description':'CABLE ASSEMBLY, SPECIAL PURPOSE, FOR ELECTRICITY, FORKED TYPE (C207)','gross_weight':'60','weight_unit':'kg','gross_weight_unit':'kg','volume':'522.27','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same multimodal hazardous-cargo family.','Combined BILL OF LADING NO / PO NO caption leaves HG938684 role unresolved, consistent with the previously frozen source criterion.','Both declared values are per package, not a scalar shipment value. COD amount is a separate role.','CFS/CFS and CY/CFS are service terms, not receipt/delivery places. Vessel caption does not establish legal carrier.','Prepaid column is populated and Collect blank. U815248 has no explicit seal caption.','Package counts 74 and 85 are visible in the image although absent from Azure word annotations. No carry-down of container identity to the second row.','Point and Country of Origin describes shipping origin, not manufacture country. Signature company is not asserted as carrier.']}
}

additions.update({
 'IMG_OCR_6_T_NV_005926': {
  'fields':{'invoice_number':'41901-9632-9041','issue_date':'2001-07-15','shipper':'KWASUNG TRADING CO.','exporter':'KWASUNG TRADING CO.','letter_of_credit_number':'M8221002NS71264','letter_of_credit_date':'2004-01-18','letter_of_credit_issuing_bank':'State Street Corp.','consignee':'Tource Consulting','notify_party':'Ceneficial Blends','port_of_loading':'LICATA, ITALY','place_of_delivery':'LUGNVIK, SWEDEN','carrier':'OOCL MEMPHIS','departure_date':'2010-10-18','total_amount':'8543.12'},
  'items':[{'marks':'DLSU3745827 J133403','package_count':'40','package_type':'PKG','description':'Additional Glove Kit Assembly (EAAK)','quantity':'83','unit':'pcs','unit_price':'79.87','amount':'6149.81'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same single-item invoice family.','Caption explicitly says Carrier; a vessel-looking value does not change its field role.','Dollar symbol alone does not identify currency. No arithmetic reconciliation of item amount and document total.','Marks and Number of PKGS does not establish container or seal identities. Signed-by company is not seller.']},
 'IMG_OCR_6_T_PL_009251': {
  'fields':{'issue_date':'2010-10-17','seller':"Qeter Kiewit Sons' Co., Ltd.",'invoice_number':'247830','letter_of_credit_number':'M3993776NS08940','purchase_order_number':'404-863-7622','consignee':'Cum Sung Machine Co., Ltd.','country_of_origin':'KR','port_of_loading':'LIXURI, GREECE','port_of_discharge':'MANAUS, BRAZIL','notify_party':'Derkshire Hathaway Co., Ltd.','vessel':'OSAKANA','voyage':'V.297','departure_date':'2014-12-13','total_packages':'67','gross_weight':'308','gross_weight_unit':'kg','weight_unit':'kg','volume':'795.83','volume_unit':'m3'},
  'items':[
   {'description':'GRIP PAD-DR O/S HDL','quantity':'45','unit':'kg','net_weight':'203','gross_weight':'420','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'684.82','volume_unit':'m3'},
   {'description':'BUMPER-T/GATE OVERSLAM','quantity':'77','unit':'Feet','net_weight':'903','gross_weight':'200','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'182.43','volume_unit':'m3'},
   {'description':'Return Spring','quantity':'83','unit':'yard','net_weight':'204','gross_weight':'455','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'164.47','volume_unit':'m3'}],
  'unscored_source_fields':{'incoterms':'CIF'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same seller-country-three-row family.','Shipping marks refer to Support and Slide, not the three goods descriptions. No row association invented.','Quantity 45 kg remains goods quantity; distinct explicit Net Weight is 203 kg. Do not merge those roles.','Feet and yard retain their source spelling under the frozen contract. Signature company is not seller.']},
 'IMG_OCR_6_T_BL_008678': {
  'fields':{'bill_of_lading_number':'HG634331','shipper':'IUL JIN TEXTILE CO., LTD.','consignee':'TUNSTONE MANAGEMENT CO., LTD.','notify_party':'TUNSTONE MANAGEMENT CO., LTD.','country_of_origin':'PF','forwarding_agent':'RYUNG AN CO., LTD.','forwarding_agent_number':'42-42-070','document_reference':'754-060-1847','on_board_date':'2012-03-05','place_of_receipt':'RIZHAO, CHINA','port_of_loading':'ECKERO, FINLAND','vessel':'AUTOSTAR','voyage':'V.824','port_of_discharge':'MIDSUND, NORWAY','place_of_delivery':'OHDANA, JAPAN','total_packages':'76','freight_terms':'COLLECT','issue_place':'JEONGEUP KOREA','issue_date':'2001-07-21','carrier':'MUGOONGWHA LTD.'},
  'items':[
   {'marks':'DLSU4566776 H140787','package_count':'23','package_type':'PKG','description':'HOISTING UNIT,AIRCRAFT COMPONENT','net_weight':'292','gross_weight':'655','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'package_count':'93','package_type':'PKG','description':'PECAN PRISM COMBINATION','net_weight':'387','gross_weight':'765','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Tank-carrier family unseen in original31, already seen in this source-review batch.','Notify explicitly says SAME AS CONSIGNEE. Explicit AS CARRIER identifies MUGOONGWHA LTD.; LBC signs as agent.','This source explicitly prints Total: 76 PKG, unlike the unlabelled footer count in another reviewed source.','Hazardous declaration date is not issue date. ZARZIS is an on-board place, not port of loading.','Marks caption does not establish container/seal roles. General FCL delivery boilerplate is not either goods description.']}
})

additions.update({
 'IMG_OCR_6_T_NV_010190': {
  'fields':{'invoice_number':'308589','issue_date':'2000-09-09','shipper':'Vuk San Ustry Co., Ltd.','seller':'Vuk San Ustry Co., Ltd.','letter_of_credit_number':'M0242220NS99908','letter_of_credit_date':'2006-08-12','consignee':'Porfolk Southern Co., Ltd.','buyer':'Porfolk Southern Co., Ltd.','vessel':'CMA CGM LOUGA','voyage':'V.750','departure_date':'2006-10-16','port_of_loading':'DIJON, FRANCE','place_of_delivery':'SAKAIDE, JAPAN','incoterms':'DES','payment_terms':'By COW 8 % : Upon signing the contract 24 % : Upon cargo arrival at the discharge port 55 % : After inspection within 60 days from cargo arrival at the discharging port','total_amount':'3826.32'},
  'items':[
   {'marks':'Slide','package_count':'84','package_type':'PKG','description':'Ring, Piston Ring','quantity':'6','unit':'pound','hs_code':'2590.01','unit_price':'2.76','amount':'61.66','purchase_order_number':'80-142'},
   {'marks':'Volt','package_count':'80','package_type':'PKG','description':'Support, Air Cleaner','quantity':'1','unit':'box','hs_code':'0421.94','unit_price':'9.50','amount':'63.10','purchase_order_number':'81-872'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same combined shipper/seller and payment-schedule family.','Buyer explicitly refers to consignee. No exporter assertion from shipper/seller caption.','Full printed payment schedule is retained, consistent with the frozen criterion for this family. Percentages and dates are not reconciled or corrected.','Pound and box retain source spelling under the frozen contract. Dollar signs alone are not an ISO currency. Item-specific PO numbers do not become one document purchase order.']},
 'IMG_OCR_6_T_PL_012461': {
  'fields':{'issue_date':'2021-12-24','seller':'Criggs Stratton Co., Ltd.','invoice_number':'527433','letter_of_credit_number':'M2492253NS28202','purchase_order_number':'704-438-1292','consignee':'Onde Rporation Co., Ltd.','country_of_origin':'NZ','port_of_loading':'KALLO, BELGIUM','port_of_discharge':'PORTICI, ITALY','notify_party':'Tymbol Technologies Co., Ltd.','vessel':'PADIAN 3','voyage':'V.198','departure_date':'2004-07-29','total_packages':'78','gross_weight':'636','gross_weight_unit':'kg','weight_unit':'kg','volume':'291.30','volume_unit':'m3'},
  'items':[
   {'description':'Lightning Protection Filter AIU J3','quantity':'23','unit':'Yard','net_weight':'901','gross_weight':'279','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'687.00','volume_unit':'m3'},
   {'description':'Cover, For Heat Shield','quantity':'37','unit':'pcs','net_weight':'390','gross_weight':'849','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'630.94','volume_unit':'m3'},
   {'description':'CLIP-AIRCON COOLER LINE','quantity':'77','unit':'Ton','net_weight':'225','gross_weight':'922','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'855.40','volume_unit':'m3'}],
  'unscored_source_fields':{'incoterms':'FCA'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same seller-country-three-row family.','Shipping marks refer to LEVER and E-card, not listed goods; no invented row relationship.','Ton does not establish metric tonne; Ton and Yard retain their source spelling under the frozen contract. Signature company is not seller.']},
 'IMG_OCR_6_T_BL_012777': {
  'fields':{'shipment_date':'2006-08-16','shipper':'BLUESCOPE STEEL','exporter':'BLUESCOPE STEEL','booking_number':'17376','document_reference':'239-831-9493','quotation_number':'45-03-78592','forwarding_agent_number':'51-56-19-0236','shipping_origin':'KUWAIT','consignee':'RELIANT MORTGAGE','delivery_party':'NEARNING SCIENCES','notify_party':'TUPERFRIENDLY CO. LTD.','bill_to_party':'B. K. INTERNATIONAL LTD','vessel':'NOBLE BREEZE','port_of_loading':'VOLTRI, ITALY','port_of_discharge':'HYPPELN, SWEDEN','freight_terms':'PREPAID','gross_weight':'88','gross_weight_unit':'kg','weight_unit':'kg','volume':'809.90','volume_unit':'m3','issue_place':'BAZIAS, ROMANIA','issue_date':'2017-08-07'},
  'items':[
   {'container_number':'DLSU4903008','marks':'R158008','package_count':'96','package_type':'PKG','description':'CONNECTOR','gross_weight':'24','weight_unit':'kg','gross_weight_unit':'kg','volume':'158.39','volume_unit':'m3'},
   {'package_count':'27','package_type':'PKG','description':'MESH LIGHT COMBINATION','gross_weight':'63','weight_unit':'kg','gross_weight_unit':'kg','volume':'129.08','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same multimodal hazardous-cargo family.','Combined BILL OF LADING NO / PO NO leaves HG650886 role unresolved. Both declared values are per package, not shipment scalar.','Package counts 96 and 27 are visible in source but absent from Azure word annotations.','Prepaid column is populated; Collect blank. COD is not declared value. Service terms are not receipt/delivery places.','Vessel caption does not establish legal carrier. Signature company is not asserted as carrier.']}
})

additions.update({
 'IMG_OCR_6_T_NV_019366': {
  'fields':{'invoice_number':'001583','issue_date':'2021-02-15','shipper':'Kyosung Metals Co., Ltd.','seller':'Kyosung Metals Co., Ltd.','letter_of_credit_number':'M5057637NS27257','letter_of_credit_date':'2008-11-21','consignee':'Drosscountry Mortgage Co., Ltd.','buyer':'Drosscountry Mortgage Co., Ltd.','vessel':'AS SERAFINA','voyage':'V.303','departure_date':'2019-05-14','port_of_loading':'FUNAYA, JAPAN','place_of_delivery':'EL HAMRA, EGYPT','incoterms':'EXW','payment_terms':'By T/T 9 % : Upon signing the contract 23 % : Upon cargo arrival at the discharge port 66 % : After inspection within 65 days from cargo arrival at the discharging port','total_amount':'1745.71'},
  'items':[
   {'marks':'LINER','package_count':'83','package_type':'PKG','description':'Stud','quantity':'2','unit':'Bag','hs_code':'2997.10','unit_price':'7.63','amount':'59.97','purchase_order_number':'67-741'},
   {'marks':'Cooler','package_count':'73','package_type':'PKG','description':'CLAMP-OIL COOLER HOSE','quantity':'7','unit':'ST','hs_code':'1878.99','unit_price':'9.02','amount':'90.96','purchase_order_number':'76-057'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same combined shipper/seller and payment-schedule family.','Buyer explicitly refers to consignee. Full payment schedule and leading zeros in invoice number preserved. Dollar signs do not establish currency.','Unknown Bag and ST units retain source spelling. Item-specific orders do not become one document purchase order. Signature company is not seller.']},
 'IMG_OCR_6_T_PL_019908': {
  'fields':{'invoice_number':'312867','invoice_date':'2002-02-24','shipper':'Ixko Ustrial Co., Ltd.','buyer_reference':'Toshiba Syste Co., Ltd.','consignee':'Ontrusted Advisors Co., Ltd.','port_of_loading':'MOLDE, NORWAY','country_of_destination':'JP','vessel':'ROTRA MARE','voyage':'V.807','departure_date':'2018-10-17','port_of_discharge':'IWAFUNE, JAPAN','country_of_origin':'SZ'},
  'items':[
   {'description':'PIPE-TAIL W / MUFFLER LH','hs_code':'9905.31-8238','quantity':'9','unit':'ST','net_weight':'58.51','gross_weight':'321.21','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'KEY-CRANKSHAFT','hs_code':'6165.72-6969','quantity':'4','unit':'YD','net_weight':'27.82','gross_weight':'454.90','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'Plate Sub-assemblies','hs_code':'4735.59-5772','quantity':'1','unit':'Ton','net_weight':'15.20','gross_weight':'188.92','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'unscored_source_fields':{'incoterms':'FCA APAPA, NIGERIA','payment_terms':'R/C'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same certification-footer family.','Date of Issue in the invoice reference block is transcribed as invoice_date consistent with frozen family criterion; role adjudication still appropriate.','Unlabelled final 27.46/482.05 line is not an explicit total or a fourth identified item.','Slash in first description is visible in source despite missing Azure word annotation. Buyer Ref company is not buyer.','Swaziland is the printed historic country name; SZ is the expected country identity, not an instruction to hardcode this sample.','Shipping marks refer to different goods. ST, YD and Ton remain raw under frozen unit contract.']},
 'IMG_OCR_6_T_BL_019664': {
  'fields':{'bill_of_lading_number':'HG633431','shipper':'OXPRESSION NETWORKS','consignee':'QAVISTAR INTERNATIONAL','notify_party':'RORTAGE POINT PARTNERS','vessel':'MARLA DUO','voyage':'V.083','port_of_loading':'JIAMUSI, CHINA','port_of_discharge':'MIETKOW, POLAND','delivery_party':'TUMMIT2SEA CONSULTING','total_packages':'29','freight_terms':'PREPAID','freight_payable_at':'SATA, JAPAN','issue_place':'TENES, ALGERIA','issue_date':'2011-07-22','on_board_date':'2000-07-29'},
  'items':[{'container_number':'DLSU9399230','seal_number':'A020812','package_count':'35','package_type':'PKG','description':'SPANNER','gross_weight':'18','weight_unit':'kg','gross_weight_unit':'kg','volume':'118.51','volume_unit':'m3'}],
  'expected_review':['fields.carrier'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same VITA combined-transport family.','Issuer branding/signature is VITA LOGISTICS CO., LTD. but no explicit as-carrier role; carrier needs independent adjudication, consistent with earlier frozen source criterion.','Place of receipt/delivery contains service terms. ROUBAIX is expressly merchant reference only, not place_of_delivery.','Explicit combined container/seal heading and distinct identifiers establish both item roles. 20GPX2/40GPX4 are container size/count, not package count.','Prepaid column populated. Prepaid at establishes freight payment location; this is distinct from empty Payable at. No arithmetic reconciliation.']}
})

additions.update({
 'IMG_OCR_6_T_NV_024386': {
  'fields':{'invoice_number':'486817','issue_date':'2003-01-24','proforma_invoice_number':'54-41-35-7976','buyer':'Auto Flags Gokan Co., Ltd.','seller':'Wadano Korea Co., Ltd.','port_of_loading':'HIRARA, JAPAN','vessel':'MAERSK NEWARK','port_of_discharge':'FREI, NORWAY','voyage':'V.472','departure_date':'2014-03-21','place_of_delivery':'QUINTERO, CHILE','letter_of_credit_number':'M1248159NS29623','letter_of_credit_date':'2015-07-23','country_of_origin':'TR','incoterms':'DEQ KIMASI, GREECE','payment_terms':'D/P','currency':'USD','total_amount':'2240.44'},
  'items':[
   {'hs_code':'1822.55-2195','description':'Small IR Sensor For Unmanned Aerial Vehicles','quantity':'65','unit':'Feet','unit_price':'90.04','amount':'6702.45'},
   {'hs_code':'5433.61-9320','description':'CABLE ASSY-SW, COCKPIT','quantity':'39','unit':'pcs','unit_price':'38.89','amount':'1795.54'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same proforma-reference and two-tier goods-header family.','P/I No. is a proforma reference, not the commercial invoice number. Currency USD is printed in monetary column headings.','Terms location KIMASI belongs to DEQ, distinct from explicit Final Destination QUINTERO. No amount reconciliation. Feet retains source spelling.']},
 'IMG_OCR_6_T_PL_026209': {
  'fields':{'shipper':'REDCON Solutions Group','exporter':'REDCON Solutions Group','invoice_number':'42709-5048-3902','invoice_date':'2017-06-10','letter_of_credit_number':'M6479187NS28556','letter_of_credit_date':'2008-12-26','letter_of_credit_issuing_bank':'Kwangju Bank','consignee':'Inquizit Incorporated','notify_party':'Enivista Insurance','port_of_loading':'GUAYMAS, MEXICO','place_of_delivery':'VARBERG, SWEDEN','carrier':'PRINCESS LAYLA','departure_date':'2001-01-03','weight_unit':'kg','volume':'128.77','volume_unit':'m3'},
  'items':[
   {'marks':'DLSU4771786 W868978','description':'Temperature Sensor, For Cold Water','quantity':'66','unit':'Yard','net_weight':'19','gross_weight':'18','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'881.04','volume_unit':'m3'},
   {'description':'Block, For Connection','quantity':'12','unit':'BOX','net_weight':'82','gross_weight':'83','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'648.92','volume_unit':'m3'},
   {'description':'Plate, Back','quantity':'49','unit':'Doz','net_weight':'61','gross_weight':'81','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'297.41','volume_unit':'m3'}],
  'expected_review':['fields.net_weight','fields.gross_weight'],
  'unscored_source_fields':{'unqualified_total_weight':'20 KG'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same numbered three-row packing family.','TOTAL 20 KG is printed under the description region, without net/gross qualification or alignment with either weight column. Preserve unresolved basis instead of guessing. Total volume is explicitly typed CBM.','Carrier (Flight No.) is the printed caption; value shape alone does not establish a vessel role. Invoice date is a reference date.','Marks and Number does not distinguish container/seal roles; identifiers retained as first-row marks. Unknown units remain raw. Signature company is not shipper.']},
 'IMG_OCR_6_T_BL_024001': {
  'fields':{'bill_of_lading_number':'HG643094','shipper':'IHWA USTRIAL CO., LTD.','consignee':'TOWADA PRINCE HOTEL CO., LTD.','notify_party':'TOWADA PRINCE HOTEL CO., LTD.','country_of_origin':'LA','forwarding_agent':'OVER PLUS CO., LTD.','forwarding_agent_number':'97-31-953','document_reference':'261-233-8985','on_board_date':'2015-05-09','place_of_receipt':'POSITRA, INDIA','port_of_loading':'TSURUGA, JAPAN','vessel':'TRANS FUTURE 11','voyage':'V.122','port_of_discharge':'IMAZATO, JAPAN','place_of_delivery':'MAANSHAN, CHINA','freight_terms':'COLLECT','issue_place':'SANGJU KOREA','issue_date':'2018-03-30','carrier':'MUGOONGWHA LTD.'},
  'items':[
   {'marks':'DLSU6205929 D681161','package_count':'17','package_type':'PKG','description':'MACHINES FOR PROCESSING PULP AND PAPER','net_weight':'884','gross_weight':'148','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'package_count':'31','package_type':'PKG','description':'STOPPER KIT-STARTER PINIO','net_weight':'574','gross_weight':'800','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'expected_review':['fields.total_packages'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Tank-carrier family new relative to original31, repeated in this source-only set.','Notify explicitly refers to consignee. Carrier explicitly named as carrier; LBC is agent.','Unlabelled footer 30 PKG does not explicitly establish total scope; consistent with earlier source criterion for this variant.','Hazard declaration date is not issue date. On-board place MEI is not port of loading. No container/seal type inference from unqualified marks.']}
})

additions.update({
 'IMG_OCR_6_T_NV_000420': {
  'fields':{'invoice_number':'06223-4836-2263','issue_date':'2010-05-21','shipper':'OL SAN ELECTRIC CO. Ltd','exporter':'OL SAN ELECTRIC CO. Ltd','letter_of_credit_number':'M8627492NS04724','letter_of_credit_date':'2007-11-17','letter_of_credit_issuing_bank':'Citizens Financial Group','consignee':'Kenri Bakery & Deli','notify_party':'NY Shower Door. Tampa','port_of_loading':'QUINCHAO, CHILE','place_of_delivery':'USHITSU, JAPAN','carrier':'POLARIS VG','departure_date':'2021-06-03','total_amount':'6653.58'},
  'items':[{'marks':'DLSU3022626 B427949','package_count':'14','package_type':'PKG','description':'Circuit Card Body ; B22','quantity':'79','unit':'drum','unit_price':'18.80','amount':'8074.17'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same single-item invoice family.','Ampersand in consignee and semicolon in description are visible in source despite omitted Azure word annotations.','Explicit Carrier caption retained; no vessel inference. Marks not typed as container/seal. Dollar sign alone is not currency. Signature company is not seller.']},
 'IMG_OCR_6_T_PL_001655': {
  'fields':{'shipper':'PFI Industries','exporter':'PFI Industries','invoice_number':'98430-1399-8460','invoice_date':'2021-05-30','letter_of_credit_number':'M4370552NS18605','consignee':'LUEM HWEA CO. Ltd','notify_party':'Pedical Solutions','port_of_loading':'OLHAO, PORTUGAL','place_of_delivery':'SATPATI, INDIA','vessel':'X PRESS ANGLESEY','departure_date':'2020-02-20','total_packages':'49','gross_weight':'24','gross_weight_unit':'kg','weight_unit':'kg'},
  'items':[
   {'description':'Cable Assembly, Special Purpose, For Electricity, C651','product_code':'20-3','quantity':'2','unit':'BOX','net_weight':'32','weight_unit':'kg','net_weight_unit':'kg','package_count':'27','package_type':'PKG'},
   {'description':'Intercom Set Controller','product_code':'95-5','quantity':'3','unit':'pcs','net_weight':'99','weight_unit':'kg','net_weight_unit':'kg','package_count':'79','package_type':'PKG'},
   {'description':'Coupling Half, Quick Disconnect Type (SIZE132)','product_code':'46-6','quantity':'2','unit':'SF','net_weight':'40','weight_unit':'kg','net_weight_unit':'kg','package_count':'45','package_type':'PKG'}],
  'expected_review':['fields.letter_of_credit_date'],
  'unscored_source_fields':{'total_new_weight':'33 KG','quality_terms':'Quality about equal to samples'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same borderless goods/footer family.','L/C date 05-11-2007 is ambiguous; do not infer order from a different event date. Invoice/departure dates have only one valid month/day interpretation.','Footer literally says TOTAL NEW WEIGHT, not NET. Preserve unresolved meaning without silently correcting the source.','Unknown BOX and SF units stay raw. Signed-by company is not shipper.']},
 'IMG_OCR_6_T_BL_002785': {
  'fields':{'shipment_date':'2006-06-28','shipper':'ILECTROSOFT SERVICES','exporter':'ILECTROSOFT SERVICES','booking_number':'41065','document_reference':'791-196-2035','quotation_number':'54-83-27984','forwarding_agent_number':'52-80-88-9877','shipping_origin':'FINLAND','consignee':'FOLINKURTIS ADVERTISING','delivery_party':'KON INDUSTRIES','notify_party':'FUN & BRADSTREET','bill_to_party':'YOORHI TECH CO. LTD.','vessel':'CONTSHIP HUB','port_of_loading':'XINTANG, CHINA','port_of_discharge':'ORIGAMI, JAPAN','freight_terms':'PREPAID','gross_weight':'84','gross_weight_unit':'kg','weight_unit':'kg','volume':'289.53','volume_unit':'m3','issue_place':'FURIANI, FRANCE','issue_date':'2008-08-12'},
  'items':[
   {'container_number':'DLSU2088195','marks':'K860152','package_count':'90','package_type':'PKG','description':'PIN, SHOULDER TYPE, SKINLESS TYPE','gross_weight':'49','weight_unit':'kg','gross_weight_unit':'kg','volume':'431.65','volume_unit':'m3'},
   {'package_count':'86','package_type':'PKG','description':'FUEL PIPE, FOR HIGH PRESSURE, FOR CYLINDER A4','gross_weight':'45','weight_unit':'kg','gross_weight_unit':'kg','volume':'394.53','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same multimodal hazardous-cargo family.','Combined BILL OF LADING NO / PO NO leaves HG660090 role unresolved. Both declared values per package, not shipment scalar.','Counts 90 and 86 are visible in image but absent from Azure word annotations. Prepaid money column populated, Collect blank.','Service terms are not locations. Vessel is not legal carrier. Signature company is not carrier. No container identity carry-down.']}
})

additions.update({
 'IMG_OCR_6_T_NV_007211': {
  'fields':{'invoice_number':'95734-5619-1379','issue_date':'2003-02-24','shipper':'FHANG DAE CORPORATION','exporter':'FHANG DAE CORPORATION','letter_of_credit_number':'M9625623NS20466','letter_of_credit_date':'2005-06-06','letter_of_credit_issuing_bank':'National Agreeculture Bank','consignee':'Qetrelli Previtera','notify_party':'Faptive Alternatives','port_of_loading':'JUIST, GERMANY','place_of_delivery':'SASUNA, JAPAN','carrier':'MAERSK KIEL','departure_date':'2015-05-29','total_amount':'2616.30'},
  'items':[{'marks':'DLSU2383918 G160471','package_count':'74','package_type':'PKG','description':'Alternator','quantity':'26','unit':'Meter','unit_price':'79.05','amount':'3051.67'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same single-item invoice family.','Printed National Agreeculture Bank spelling preserved. Carrier caption retained, not inferred vessel.','Unknown Meter stays raw. Marks not typed as container/seal. Dollar sign alone is not currency. Signature company is not seller.']},
 'IMG_OCR_6_T_PL_006668': {
  'fields':{'shipper':'AMANO JITENSHATEN','exporter':'AMANO JITENSHATEN','invoice_number':'17318-1777-3193','invoice_date':'2011-08-03','letter_of_credit_number':'M3122118NS98848','letter_of_credit_date':'2003-04-24','consignee':'Tungdo Gl Corporation','notify_party':'Uctane Marketing','port_of_loading':'NEJIME, JAPAN','place_of_delivery':'ARBRA, SWEDEN','vessel':'CONTSHIP NEW','departure_date':'2005-01-30','total_packages':'58','gross_weight':'64','gross_weight_unit':'kg','weight_unit':'kg'},
  'items':[
   {'description':'Spool','product_code':'67-2','quantity':'3','unit':'Meter','net_weight':'49','weight_unit':'kg','net_weight_unit':'kg','package_count':'73','package_type':'PKG'},
   {'description':'Chaff Launch Tube Assembly','product_code':'94-2','quantity':'8','unit':'pcs','net_weight':'33','weight_unit':'kg','net_weight_unit':'kg','package_count':'47','package_type':'PKG'},
   {'description':'Bolt, Shoulder','product_code':'28-1','quantity':'7','unit':'Bale','net_weight':'54','weight_unit':'kg','net_weight_unit':'kg','package_count':'81','package_type':'PKG'}],
  'unscored_source_fields':{'total_new_weight':'83 KG','quantity_terms':'Shipped Quantity Terms'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same borderless goods/footer family.','TOTAL NEW WEIGHT is the literal footer caption; not silently corrected to NET.','Unknown Meter and Bale stay raw. Generic Terms value does not establish a document quantity. Signature company is not shipper.']},
 'IMG_OCR_6_T_BL_008318': {
  'fields':{'shipment_date':'2018-07-10','shipper':'ENITED STATIONERS','exporter':'ENITED STATIONERS','booking_number':'24302','document_reference':'471-247-1906','quotation_number':'52-41-44591','forwarding_agent_number':'42-31-18-5973','shipping_origin':'NAMIBIA','consignee':'JOME TRADE USA','delivery_party':'RIVA SOLUTIONS','notify_party':'CHINA RAILWAY GROUP','bill_to_party':'ROSIERE COSMETICS INC.','vessel':'HYUNDAI OAKLAND','port_of_loading':'KIKUMA, JAPAN','port_of_discharge':'EVERTON, GUYANA','freight_terms':'PREPAID','gross_weight':'61','gross_weight_unit':'kg','weight_unit':'kg','volume':'242.94','volume_unit':'m3','issue_place':'EL HAMRA, EGYPT','issue_date':'2000-10-16'},
  'items':[
   {'container_number':'DLSU6723921','marks':'S700923','package_count':'56','package_type':'PKG','description':'LOCK NUT, FOR PIPE COUPLING','gross_weight':'22','weight_unit':'kg','gross_weight_unit':'kg','volume':'438.77','volume_unit':'m3'},
   {'package_count':'13','package_type':'PKG','description':'CYLINDER ASSEMBLY, LINEAR','gross_weight':'62','weight_unit':'kg','gross_weight_unit':'kg','volume':'512.49','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same multimodal hazardous-cargo family.','Combined BILL OF LADING NO / PO NO leaves HG014481 role unresolved. Both declared values are per package.','Counts 56 and 13 are visible in source but absent from Azure word annotations. Prepaid money column populated.','Service terms are not locations. Vessel is not legal carrier. Signature company is not carrier. No container carry-down or arithmetic reconciliation.']}
})

additions.update({
 'IMG_OCR_6_T_NV_014705': {
  'fields':{'invoice_number':'02700-8357-2095','issue_date':'2001-08-04','shipper':'KOONG ANG IND. CO. Ltd','exporter':'KOONG ANG IND. CO. Ltd','letter_of_credit_number':'M0196248NS76986','letter_of_credit_date':'2016-10-25','letter_of_credit_issuing_bank':'KEB Hana Bank','consignee':'Dallibrity Solutions','notify_party':'Meeping Current Matters','port_of_loading':'EMBLEM, BELGIUM','place_of_delivery':'GALWAY, IRELAND','carrier':'MAERSK IOWA','departure_date':'2008-09-12','total_amount':'4803.93'},
  'items':[{'marks':'DLSU0288793 Y854749','package_count':'97','package_type':'PKG','description':'Diodes, Transistors And Similar Semiconductor Devices','quantity':'90','unit':'set','unit_price':'86.38','amount':'4323.63'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same single-item invoice family.','Carrier caption retained, not inferred vessel. Marks not typed as container/seal. Dollar sign alone is not currency. Signature company is not seller.']},
 'IMG_OCR_6_T_PL_014446': {
  'fields':{'seller':'Kwanam Trading Co., Ltd.','invoice_number':'948818','invoice_date':'2009-01-15','buyer':'Mezhregional Naya Co., Ltd.','consignee':'Nattio Communications Co., Ltd.','notify_party':'Nattio Communications Co., Ltd.','departure_date':'2017-08-04','carrier':'APL SALALAH','voyage':'V.186','port_of_loading':'KUYAMA, JAPAN','place_of_delivery':'HAYAKAWA, JAPAN','net_weight':'255','gross_weight':'949','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'200.95','volume_unit':'m3'},
  'items':[
   {'marks':'Pump A1 ~ A 9','package_count':'20','package_type':'PKG','description':'PLDRO','net_weight':'229','gross_weight':'809','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'778.76','volume_unit':'m3'},
   {'marks':'Inserter B10 ~ B 53','package_count':'19','package_type':'PKG','description':'GUIDE-GLOVE BOX HOUSING','net_weight':'360','gross_weight':'607','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'973.59','volume_unit':'m3'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same two-row quantity-or-net-weight family.','Invoice caption explicitly says date of Invoice; not packing-list issue date. Notify Same as above refers to immediately preceding consignee box.','KG under Quantity or net weight establishes net-weight role; no goods quantity invented. Carrier remains carrier.','Explicit column totals preserved, not recalculated. Shipping-mark typography transcribed from source; spacing may require independent adjudication.']},
 'IMG_OCR_6_T_BL_013073': {
  'fields':{'booking_number':'96817','bill_of_lading_number':'HG598289','document_reference':'1231.89-4186','forwarding_agent':'PATIONSBENEFITS CO., LTD.','forwarding_agent_number':'43322-8503-0160','country_of_origin':'US','notify_party':'DONTI ORGANIZATION CO., LTD.','delivery_party':'JONAN BORING CO., LTD.','mode_of_transport':'DEQ','place_of_receipt':'ASSAB, ERITREA','routing_instructions':'ASAN KOREA','vessel':'EVER ENVOY','port_of_loading':'ADABIYA, EGYPT','movement_type':'OCEAN','port_of_discharge':'MASNOU, SPAIN','place_of_delivery':'APAPA, NIGERIA','total_packages':'15','declared_value':'608.92','freight_terms':'PREPAID','carrier':'JOLDEN STATE BAN CO., LTD.','issue_date':'2003-10-30'},
  'items':[
   {'container_number':'DLSU2656760','marks':'E475080','package_count':'90','package_type':'PKG','description':'EYEPIECE ASSEMBLY','gross_weight':'499','weight_unit':'kg','gross_weight_unit':'kg','volume':'657.27','volume_unit':'m3'},
   {'package_count':'20','package_type':'PKG','description':'BEZEL RR CONSOLE SWITCH','gross_weight':'908','weight_unit':'kg','gross_weight_unit':'kg','volume':'467.93','volume_unit':'m3'}],
  'expected_review':['fields.consignee'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same double-consignee liability form family.','Two different explicitly labelled consignees: VAE RHIM CO., LTD. and DOOP PRETZELS CO., LTD.; no invented shipper or arbitrary party choice.','Not later than AUG04,2001 is a constraint, not actual DATED OCT30,2003. Insurance amount 862.11 is separate from declared value.','Prepaid money column populated. AS CARRIER explicitly identifies carrier. Unqualified second mark not asserted as seal. No container carry-down.']}
})

additions.update({
 'IMG_OCR_6_T_NV_016832': {
  'fields':{'invoice_number':'68895-4002-3097','issue_date':'2018-06-24','shipper':'APEC ENG. CO. Ltd','exporter':'APEC ENG. CO. Ltd','letter_of_credit_number':'M2280292NS56957','letter_of_credit_date':'2006-02-07','letter_of_credit_issuing_bank':'National Agreeculture Bank','consignee':'TuperJeweler.com','notify_party':'Pax Connect Marketing','port_of_loading':'UNOSHIMA, JAPAN','place_of_delivery':'TOMIE, JAPAN','carrier':'HAI SI 1','departure_date':'2006-05-18','total_amount':'6770.76'},
  'items':[{'marks':'DLSU2886333 U550596','package_count':'89','package_type':'PKG','description':'Wire Lace (inside)','quantity':'93','unit':'Bale','unit_price':'44.77','amount':'4817.20'}],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same single-item invoice family.','Carrier caption retained. Unknown Bale stays raw. Marks not typed as container/seal. Dollar sign alone is not currency. Signature company is not seller.']},
 'IMG_OCR_6_T_PL_019725': {
  'fields':{'invoice_number':'001745','invoice_date':'2021-11-01','shipper':'Nim Hwa Metal Co., Ltd.','buyer_reference':'Iscrow Options Co., Ltd.','consignee':'Deutsche Telekom Co., Ltd.','port_of_loading':'FETHIYE, TURKEY','country_of_destination':'CL','vessel':'CAROLINE MAERSK','voyage':'V.426','departure_date':'2006-04-18','port_of_discharge':'MITSUKUE, JAPAN','country_of_origin':'BO'},
  'items':[
   {'description':'Spring Washer','hs_code':'4513.25-8548','quantity':'8','unit':'t','net_weight':'23.44','gross_weight':'551.95','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'LINK OUTPUT ASSY','hs_code':'6541.07-7050','quantity':'1','unit':'ctn','net_weight':'96.85','gross_weight':'135.96','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'CONNECTOR ASSY-HEATER TO AIR V','hs_code':'3325.63-7096','quantity':'1','unit':'Meter','net_weight':'26.91','gross_weight':'194.97','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'unscored_source_fields':{'incoterms':'FOB OSATO, JAPAN','payment_terms':'A/P'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same certification-footer family.','Date of Issue in invoice reference block follows frozen invoice_date criterion; role adjudication appropriate.','Unlabelled last 13.05/376.42 line is not an explicit total or identified fourth item. Buyer Ref remains reference, not buyer.','Country identity BO comes from printed Republic of Bolivia. No address-based country inference. Shipping marks refer to different goods. Unknown Meter remains raw.']},
 'IMG_OCR_6_T_BL_019060': {
  'fields':{'bill_of_lading_number':'HG343571','shipper':'FONA TEXTILE CO., LTD.','consignee':'EPOLLO INTERACTIVE CO., LTD.','notify_party':'EPOLLO INTERACTIVE CO., LTD.','country_of_origin':'WS','forwarding_agent':'FONG JIN CO., LTD.','forwarding_agent_number':'87-77-193','document_reference':'785-056-4916','on_board_date':'2004-04-08','place_of_receipt':'ANTA, NIGERIA','port_of_loading':'NHAVE, INDIA','vessel':'KMTC SURABAYA','voyage':'V.103','port_of_discharge':'FARO, PORTUGAL','place_of_delivery':'GULLUK, TURKEY','freight_terms':'COLLECT','issue_place':'UIWANG KOREA','issue_date':'2006-05-04','carrier':'MUGOONGWHA LTD.'},
  'items':[
   {'marks':'DLSU1709737 E106099','package_count':'74','package_type':'PKG','description':'WASHERS, BEARINGS','net_weight':'523','gross_weight':'156','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'package_count':'55','package_type':'PKG','description':'DEVICE STAND, FOR FILTER INSTALLATION','net_weight':'713','gross_weight':'582','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'expected_review':['fields.total_packages'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same tank-carrier family.','Notify explicitly refers to consignee; as-carrier caption establishes carrier, distinct from LBC agent.','Unlabelled footer 31 PKG needs total-scope adjudication. Hazard date is not issue date; on-board place is not port of loading. Marks do not establish container/seal roles.']}
})

additions.update({
 'IMG_OCR_6_T_NV_024142': {
  'fields':{'invoice_number':'415828','proforma_invoice_number':'58-22-96-3421','buyer':'Hillson Trucking Co., Ltd.','seller':'Gaedong International Co., Ltd.','port_of_loading':'FUSA, NORWAY','vessel':'UND BIRLIK','port_of_discharge':'SHANWEI, CHINA','voyage':'V.932','departure_date':'2007-12-28','place_of_delivery':'PYRGOS, GREECE','letter_of_credit_number':'M2621165NS62135','letter_of_credit_date':'2010-10-23','country_of_origin':'KP','incoterms':'CPT KANOYA, JAPAN','payment_terms':'T/T','currency':'USD','total_amount':'6709.78'},
  'items':[
   {'hs_code':'4582.44-3372','description':'Semiconductor And Display Equipment','quantity':'29','unit':'SF','unit_price':'73.62','amount':'1170.74'},
   {'hs_code':'8910.79-8264','description':'WIRING ASSY-FEM','quantity':'37','unit':'set','unit_price':'31.44','amount':'3592.67'}],
  'expected_review':['fields.issue_date'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same proforma-reference two-tier-header family.','Invoice date 01-03-2022 is ambiguous; do not infer its order from different event dates. Other two dates have one valid month/day interpretation.','USD printed in monetary headings. CPT location distinct from final destination. Explicit full country name identifies KP, not generic Korea. Unknown SF remains raw.']},
 'IMG_OCR_6_T_PL_024317': {
  'fields':{'shipper':'Qrocure America','exporter':'Qrocure America','invoice_number':'62800-2885-3661','invoice_date':'2010-11-24','letter_of_credit_number':'M5940540NS59595','letter_of_credit_issuing_bank':'RBC Capital Markets','consignee':'ERIKA BIYOSHITSU','notify_party':'Nedical Breakthrough','port_of_loading':'KINUURA, JAPAN','place_of_delivery':'BEJAIA, ALGERIA','carrier':'ASIATIC BAY','departure_date':'2018-01-27','weight_unit':'kg','volume':'484.63','volume_unit':'m3'},
  'items':[
   {'marks':'DLSU4364371 Q905106','description':'Vibration Isolator (for Area Admiral)','quantity':'45','unit':'ea','net_weight':'13','gross_weight':'66','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'684.00','volume_unit':'m3'},
   {'description':'Gun Seat Assembly','quantity':'98','unit':'ea','net_weight':'68','gross_weight':'63','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'207.32','volume_unit':'m3'},
   {'description':'Single Starter Assembly','quantity':'58','unit':'SF','net_weight':'91','gross_weight':'42','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'668.53','volume_unit':'m3'}],
  'expected_review':['fields.letter_of_credit_date','fields.net_weight','fields.gross_weight'],
  'unscored_source_fields':{'unqualified_total_weight':'69 KG'},
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same numbered three-row packing family.','L/C date 01-11-2009 is ambiguous. Invoice/departure dates have one valid month/day interpretation.','TOTAL 69 KG lacks net/gross qualification and is not aligned with either weight column. No invented basis.','Marks not distinguished as container/seal. Carrier remains carrier. Unknown SF stays raw. Signature company is not shipper.']},
 'IMG_OCR_6_T_BL_021901': {
  'fields':{'bill_of_lading_number':'HG689431','shipper':'OL JIN BEARING CO., LTD.','consignee':'FHIEF OUTSIDERS CO., LTD.','notify_party':'FHIEF OUTSIDERS CO., LTD.','country_of_origin':'GB','forwarding_agent':'GAE SUNG CO., LTD.','forwarding_agent_number':'91-27-307','document_reference':'379-402-5052','on_board_date':'2000-02-27','place_of_receipt':'VILA, VANUATU','port_of_loading':'HOCHST, GERMANY','vessel':'FENGNIAN88','voyage':'V.599','port_of_discharge':'FROSTA, NORWAY','place_of_delivery':'LUBECK, GERMANY','freight_terms':'PREPAID','issue_place':'BORYEONG KOREA','issue_date':'2003-06-26','carrier':'MUGOONGWHA LTD.'},
  'items':[
   {'marks':'DLSU3014623 E760544','package_count':'70','package_type':'PKG','description':'GUIDE, PIN LOCATING','net_weight':'958','gross_weight':'814','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'package_count':'30','package_type':'PKG','description':'METAL TANKS, STORAGE TANKS AND SIMILAR CONTAINERS','net_weight':'547','gross_weight':'768','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'expected_review':['fields.total_packages'],
  'notes':['Source image and all Azure word annotations reviewed before opening predictions. Same tank-carrier family.','Country text overflows into next caption; visible UNITED KINGDOM OF GREAT BRITAIN AND plus overlapping NORTHERN IRELAND identifies GB. This is an OCR difficulty, not a reason to delete the field.','Notify same as consignee; carrier explicitly as carrier. Unlabelled footer97PKG requires total-scope adjudication.','Hazard date is not issue date. On-board place is not port of loading. Marks not typed as container/seal.']}
})

additions.update({
 'IMG_OCR_6_T_NV_001077': {
  'fields':{'invoice_number':'083864','issue_date':'2015-08-15','shipper':'Yoo Sung Mtec Co., Ltd.','buyer_reference':'437-625-6075','consignee':'Tonic Automotive Co., Ltd.','port_of_loading':'SHIGEI, JAPAN','country_of_destination':'NO','vessel':'SOFRANA SURVILLE','voyage':'V.908','departure_date':'2011-01-18','port_of_discharge':'BODRUM, TURKEY','payment_terms':'L/C','letter_of_credit_issuing_bank':'Bank DBS Indonesia','currency':'USD','total_amount':'4567.15'},
  'items':[
   {'description':'Cable Assembly, Special Purpose, For Electricity, CX-2234K','hs_code':'8060.69','quantity':'5','unit':'pcs','unit_price':'2.25','amount':'59.78'},
   {'description':'COVER-BELL HOUSING','hs_code':'0784.54','quantity':'9','unit':'ea','unit_price':'7.15','amount':'15.44'},
   {'description':'Computer (OBC)','hs_code':'6913.87','quantity':'4','unit':'drum','unit_price':'4.61','amount':'89.26'}],
  'expected_review':['fields.country_of_origin'],
  'unscored_source_fields':{'delivery_service':'CFS/CY NAKIRI, JAPAN','remittance_schedule':'30% advanced USD (with order) 70% balance USD (within 3 days after B/L issued)'},
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same invoice-remittance family.','Solomon is incomplete country wording; preserve review rather than guess Solomon Islands. Destination caption contains TANA, NORWAY and explicitly establishes country NO.','CFS/CY is not an Incoterm. L/C is explicit compact payment method under frozen family criterion; separate remittance paragraph retained as coverage limitation. USD explicitly printed. Signature not party.']},
 'IMG_OCR_6_T_PL_000090': {
  'fields':{'seller':'Faewoo Valve Co., Ltd.','invoice_number':'624668','invoice_date':'2016-01-26','buyer':'Onfinia Search Co., Ltd.','consignee':'Dorporate Armor Co., Ltd.','notify_party':'Dorporate Armor Co., Ltd.','carrier':'IBI','voyage':'V.240','port_of_loading':'OTARU, JAPAN','place_of_delivery':'ON, SWEDEN','net_weight':'706','gross_weight':'821','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'888.22','volume_unit':'m3'},
  'items':[
   {'marks':'Clamp A1 ~ A 6','package_count':'41','package_type':'PKG','description':'Housing Tow Pump','net_weight':'849','gross_weight':'233','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'589.07','volume_unit':'m3'},
   {'marks':'Damper B10 ~ B 78','package_count':'69','package_type':'PKG','description':'Insertion Tube, Flexible, For Pipeline','net_weight':'967','gross_weight':'616','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'747.37','volume_unit':'m3'}],
  'expected_review':['fields.departure_date'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same two-row quantity-or-net-weight family.','Departure 01-10-2019 ambiguous, invoice date unambiguous. Same as above refers to consignee. KG establishes net weight, not goods quantity. Carrier is not inferred vessel. Totals not recomputed.']},
 'IMG_OCR_6_T_BL_000587': {
  'fields':{'shipment_date':'2003-02-21','shipper':'ELLIANT ENERGY','exporter':'ELLIANT ENERGY','booking_number':'21340','document_reference':'194-128-5879','quotation_number':'27-05-69188','forwarding_agent_number':'96-78-16-0059','shipping_origin':'KAZAKHSTAN','consignee':'UKON OFFICE SOLUTIONS','delivery_party':'JRAYDAZE CONTRACTING','notify_party':'RSB ENVIRONMENTAL','bill_to_party':'GONGIL TRADING CO.','vessel':'GLORY GUANGDONG','port_of_loading':'VENNE, GERMANY','port_of_discharge':'GARDUR, ICELAND','freight_terms':'PREPAID','gross_weight':'56','gross_weight_unit':'kg','weight_unit':'kg','volume':'795.88','volume_unit':'m3','issue_place':'SALAVERRY, PERU','issue_date':'2001-07-01'},
  'items':[
   {'container_number':'DLSU6732236','marks':'Q165321','package_count':'22','package_type':'PKG','description':'TRANSCEIVER_ FOR RADIO, ALTIMETER','gross_weight':'91','weight_unit':'kg','gross_weight_unit':'kg','volume':'373.83','volume_unit':'m3'},
   {'package_count':'70','package_type':'PKG','description':'OPTICAL LENSES AND OPTICAL ELEMENTS','gross_weight':'15','weight_unit':'kg','gross_weight_unit':'kg','volume':'837.48','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same multimodal hazardous-cargo family.','Combined B/L NO / PO NO ambiguous. Both declared values per package. Counts 22 and 70 read from image, absent in annotations. Prepaid column populated. Service terms not locations, signature not carrier.']}
})

additions.update({
 'IMG_OCR_6_T_NV_009705': {
  'fields':{'invoice_number':'04647-7521-8178','issue_date':'2000-07-17','shipper':'FWELL TECH CO. LTD.','exporter':'FWELL TECH CO. LTD.','letter_of_credit_number':'M4920741NS87483','letter_of_credit_date':'2013-01-26','letter_of_credit_issuing_bank':'Citizens Financial Group','consignee':'Emsive Digital','notify_party':'Othos Medical Staffing','port_of_loading':'FAID, EGYPT','place_of_delivery':'YALA, THAILAND','carrier':'FORTUNE CARRIER','departure_date':'2017-09-08','total_amount':'5344.03'},
  'items':[{'marks':'DLSU9007825 R728439','package_count':'74','package_type':'PKG','description':'Pipe, For Inlet','quantity':'40','unit':'Bag','unit_price':'17.75','amount':'4672.02'}],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same single-item invoice family.','Carrier caption not vessel. Bag remains raw under frozen unit contract. Marks not typed container/seal. Dollar sign ambiguous currency. Signature not seller.']},
 'IMG_OCR_6_T_PL_008647': {
  'fields':{'seller':'Inheuser Busch Co., Ltd.','invoice_number':'320146','letter_of_credit_number':'M2146131NS40095','purchase_order_number':'471-631-7426','country_of_origin':'MT','consignee':'Yhitepine Rporation Co., Ltd.','notify_party':'Dinary Defense Co., Ltd.','port_of_loading':'KASADO, JAPAN','port_of_discharge':'PARA, BRAZIL','vessel':'WARNOW MOON','voyage':'V.131','departure_date':'2001-10-26','total_packages':'22','gross_weight':'817','gross_weight_unit':'kg','weight_unit':'kg','volume':'882.16','volume_unit':'m3'},
  'items':[
   {'description':'Power Valve','quantity':'84','unit':'BAG','net_weight':'196','gross_weight':'512','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'658.56','volume_unit':'m3'},
   {'description':'Flap Valve Assembly, For Dust Discharge','quantity':'90','unit':'t','net_weight':'596','gross_weight':'437','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'479.23','volume_unit':'m3'},
   {'description':'Flange, For Hose, For Fuel Tank','quantity':'36','unit':'lb','net_weight':'852','gross_weight':'965','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'708.08','volume_unit':'m3'}],
  'expected_review':['fields.issue_date'],
  'unscored_source_fields':{'incoterms':'DAP'},
  'notes':['Source image and all Azure word annotations reviewed before predictions. Seller-country-purchase-order three-row family.','Issue 07-10-2006 ambiguous. Departure unambiguous. Shipping marks name different goods; no invented row associations. BAG raw. Explicit totals not recomputed. Signature not seller.']},
 'IMG_OCR_6_T_BL_009188': {
  'fields':{'booking_number':'37266','bill_of_lading_number':'HG844091','document_reference':'7979.21-9979','forwarding_agent':'ERROWCORE CO., LTD.','forwarding_agent_number':'06391-3844-6923','country_of_origin':'RU','notify_party':'QROUD SOURCE WATER CO., LTD.','delivery_party':'CLACK BOOK RESEARCH CO., LTD.','mode_of_transport':'DDU','place_of_receipt':'CREIL, FRANCE','routing_instructions':'GIMHAE KOREA','vessel':'STAR PIONEER','port_of_loading':'SALAYA, INDIA','movement_type':'OCEAN','port_of_discharge':'ASTAKOS, GREECE','place_of_delivery':'ASSAB, ERITREA','total_packages':'64','declared_value':'528.34','freight_terms':'PREPAID','carrier':'TED BARN ENGINEERING CO., LTD.','issue_date':'2021-03-11'},
  'items':[
   {'container_number':'DLSU1268905','marks':'W210317','package_count':'31','package_type':'PKG','description':'INTERCOM SET CONTROLLER (ICS)','gross_weight':'309','weight_unit':'kg','gross_weight_unit':'kg','volume':'720.93','volume_unit':'m3'},
   {'package_count':'93','package_type':'PKG','description':'PUMP, CENTRIFUGAL','gross_weight':'244','weight_unit':'kg','gross_weight_unit':'kg','volume':'371.30','volume_unit':'m3'}],
  'expected_review':['fields.consignee'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same double-consignee liability family.','Two different consignees LOREANA AUTOMOTIVE and KIDO ORATION; no arbitrary selection or invented shipper. Not-later-than date is not issue date. Insurance amount not declared value. Prepaid money column populated. AS CARRIER explicit.']}
})

additions.update({
 'IMG_OCR_6_T_NV_011792': {
  'fields':{'invoice_number':'461477','bill_of_lading_number':'HG007264','exporter':'Kacking Law Practice','consignee':'Edapex','buyer':'Inlinx','document_reference':'223-029-7156','buyer_reference':'60-65-59845','mode_of_transport':'DPMTH','country_of_origin':'LI','country_of_destination':'TK','vessel':'VINAFCO 26','voyage':'V.119','payment_terms':'CHECK','port_of_loading':'BADDECK, CANADA','departure_date':'2021-07-25','port_of_discharge':'FUKUI, JAPAN','place_of_delivery':'ST MALO, FRANCE','insurance_policy_number':'443-566-4004','letter_of_credit_number':'78-54-36863','total_amount':'33939.42','currency':'MWK'},
  'items':[
   {'product_code':'49-248','description':'Landing Support Assembly','hs_code':'0584.99','quantity':'60','unit':'Bale','unit_price':'95.08','amount':'474.51'},
   {'product_code':'80-213','description':'Cap, Electric','hs_code':'6475.02','quantity':'9','unit':'drum','unit_price':'79.79','amount':'350.95'},
   {'product_code':'27-788','description':'Blower (K343)','hs_code':'8716.33','quantity':'84','unit':'Bag','unit_price':'71.22','amount':'7710.74'}],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same exporter-and-reference three-row family.','Exporter not seller or shipper. Page and consignment totals lack quantity/package basis. Printed currency MWK authoritative over dollar symbol. Unknown units preserved. Signature not seller.']},
 'IMG_OCR_6_T_PL_014195': {
  'fields':{'shipper':'Jraphic Components','exporter':'Jraphic Components','invoice_number':'10823-2183-5233','invoice_date':'2005-12-23','letter_of_credit_number':'M6634184NS73748','consignee':'ROTEK KOREA CORP.','notify_party':'Igile Brains Consulting','port_of_loading':'ANTALYA, TURKEY','place_of_delivery':'NIMA, JAPAN','vessel':'ONE MODERN','total_packages':'35','gross_weight':'16','gross_weight_unit':'kg','weight_unit':'kg'},
  'items':[
   {'description':'Plate Glass Artifacts','product_code':'40-9','quantity':'2','unit':'pcs','net_weight':'57','weight_unit':'kg','net_weight_unit':'kg','package_count':'81','package_type':'PKG'},
   {'description':'STICK,PACKING','product_code':'74-2','quantity':'3','unit':'box','net_weight':'67','weight_unit':'kg','net_weight_unit':'kg','package_count':'57','package_type':'PKG'},
   {'description':'Elbow, For Expansion','product_code':'56-4','quantity':'2','unit':'Yard','net_weight':'60','weight_unit':'kg','net_weight_unit':'kg','package_count':'74','package_type':'PKG'}],
  'expected_review':['fields.letter_of_credit_date','fields.departure_date'],
  'unscored_source_fields':{'total_new_weight':'42 KG','quality_terms':'Quality about equal to samples'},
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same borderless goods/footer family.','L/C 12-06-2012 and departure12-03-2015 ambiguous. TOTAL NEW WEIGHT literal not corrected to NET. Unknown box and Yard remain raw. Signature not shipper.']},
 'IMG_OCR_6_T_BL_013517': {
  'fields':{'shipment_date':'2013-01-11','shipper':'NIONHEART ALLIANCE','exporter':'NIONHEART ALLIANCE','booking_number':'28508','document_reference':'773-164-1397','quotation_number':'69-19-38372','forwarding_agent_number':'70-00-76-4739','shipping_origin':'NIGER','consignee':'PETWORK BUILDERS IT','delivery_party':'F & A SCIENTIFIC','notify_party':'KELLAS CONSTRUCTION','bill_to_party':'DHUNG WON IND CO LTD','vessel':'APL ESPLANADE','port_of_loading':'STORD, NORWAY','port_of_discharge':'OISO, JAPAN','freight_terms':'PREPAID','gross_weight':'50','gross_weight_unit':'kg','weight_unit':'kg','volume':'442.49','volume_unit':'m3','issue_place':'SHIROSE, JAPAN','issue_date':'2019-02-01'},
  'items':[
   {'container_number':'DLSU9340206','marks':'U407816','package_count':'38','package_type':'PKG','description':'SIGNAL CONVERTER','gross_weight':'75','weight_unit':'kg','gross_weight_unit':'kg','volume':'809.53','volume_unit':'m3'},
   {'package_count':'27','package_type':'PKG','description':'TORQUE CONVERTER','gross_weight':'34','weight_unit':'kg','gross_weight_unit':'kg','volume':'529.55','volume_unit':'m3'}],
  'expected_review':['fields.bill_of_lading_number','fields.declared_value'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same multimodal hazardous-cargo family.','Combined B/L NO / PO NO ambiguous. Both declared values per package. Counts 38 and27 read from image. Prepaid money column populated. Service terms not locations, signature not carrier.']}
})

additions.update({
 'IMG_OCR_6_T_NV_019082': {
  'fields':{'invoice_number':'256365','issue_date':'2002-08-28','shipper':'Platform Nine Co., Ltd.','seller':'Platform Nine Co., Ltd.','letter_of_credit_number':'M8923585NS40247','letter_of_credit_date':'2013-10-17','consignee':'Yasuda Shokai Co., Ltd.','buyer':'Yasuda Shokai Co., Ltd.','vessel':'COSCO ASIA','voyage':'V.359','departure_date':'2000-03-19','port_of_loading':'SMOGEN, SWEDEN','place_of_delivery':'FOURNOI, GREECE','incoterms':'FOB','payment_terms':'By L/C 9 % : Upon signing the contract 75 % : Upon cargo arrival at the discharge port 29 % : After inspection within 62 days from cargo arrival at the discharging port','total_amount':'9919.54'},
  'items':[
   {'marks':'Housing','package_count':'21','package_type':'PKG','description':'Outlet Assembly, Transport Assembly','quantity':'9','unit':'INCH','hs_code':'8400.61','unit_price':'9.57','amount':'66.17','purchase_order_number':'41-217'},
   {'marks':'Clapamp','package_count':'62','package_type':'PKG','description':'CONNECTOR-WINDSHIELD WASHER','quantity':'8','unit':'Yard','hs_code':'3558.80','unit_price':'9.26','amount':'37.88','purchase_order_number':'37-860'}],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same joint-shipper-seller two-row family.','Explicit buyer same-to-consignee reference. Full payment schedule under frozen full-terms criterion, no arithmetic reconciliation. Item PO numbers not document scalar. Unknown INCH/Yard raw. Dollar sign alone ambiguous. Signature not seller.']},
 'IMG_OCR_6_T_PL_017497': {
  'fields':{'issue_date':'2014-02-28','seller':'Dloudfit Software Co., Ltd.','invoice_number':'297640','letter_of_credit_number':'M1858087NS40173','purchase_order_number':'952-442-3272','country_of_origin':'LS','consignee':'Onter Clean Co., Ltd.','notify_party':'Jentiva Health Services Co., Ltd.','port_of_loading':'NAVASPUR, INDIA','port_of_discharge':'IHOTA, JAPAN','vessel':'GH CHINOOK','voyage':'V.456','departure_date':'2013-10-29','total_packages':'81','gross_weight':'533','gross_weight_unit':'kg','weight_unit':'kg','volume':'742.46','volume_unit':'m3'},
  'items':[
   {'description':'Distance Measuring Circuit','quantity':'75','unit':'ea','net_weight':'800','gross_weight':'499','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'947.49','volume_unit':'m3'},
   {'description':'Cable','quantity':'34','unit':'Bale','net_weight':'249','gross_weight':'320','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'451.15','volume_unit':'m3'},
   {'description':'Cable Assembly, Printed','quantity':'60','unit':'ctn','net_weight':'413','gross_weight':'734','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg','volume':'461.41','volume_unit':'m3'}],
  'unscored_source_fields':{'incoterms':'CIF'},
  'notes':['Source image and all Azure word annotations reviewed before predictions. Seller-country-purchase-order three-row family.','Shipping marks name different goods; no invented row associations. Bale raw. Explicit totals not recomputed. Signature not seller.']},
 'IMG_OCR_6_T_BL_015012': {
  'fields':{'booking_number':'24254','bill_of_lading_number':'HG786735','document_reference':'8180.84-6976','forwarding_agent':'HEORGIA PACIFIC CO., LTD.','forwarding_agent_number':'26927-9826-7891','country_of_origin':'KE','notify_party':'IMPIRE FLIPPERS CO., LTD.','delivery_party':'ICICI LOMBARD GEN CO., LTD.','mode_of_transport':'DDP','place_of_receipt':'HAKATA, JAPAN','routing_instructions':'SEJONG KOREA','vessel':'SAN LORENZO','port_of_loading':'KAZUME, JAPAN','movement_type':'OCEAN','port_of_discharge':'KEJIT, MALAYSIA','place_of_delivery':'AMBRIZ, ANGOLA','total_packages':'75','declared_value':'254.23','freight_terms':'PREPAID','carrier':'ILLEGHENY TECHNOLOGIES CO., LTD.','issue_date':'2000-02-20'},
  'items':[
   {'container_number':'DLSU8912404','marks':'S210495','package_count':'27','package_type':'PKG','description':'LIQUID CRYSTAL FLAT PANEL DISPLAY','gross_weight':'919','weight_unit':'kg','gross_weight_unit':'kg','volume':'795.70','volume_unit':'m3'},
   {'package_count':'42','package_type':'PKG','description':'PIPE, AIR CONDITIONING-HEATING','gross_weight':'532','weight_unit':'kg','gross_weight_unit':'kg','volume':'971.28','volume_unit':'m3'}],
  'expected_review':['fields.consignee'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same double-consignee liability family.','Two different consignees VE JIN GRAND and ENGEL HEART BOUTIQUE; no invented shipper. Not-later-than date not issue date. Insurance not declared value. Prepaid money column populated. AS CARRIER explicit.']}
})

additions.update({
 'IMG_OCR_6_T_NV_024493': {
  'fields':{'invoice_number':'240205','proforma_invoice_number':'38-56-54-1020','buyer':'Hirst American Co., Ltd.','seller':'Vam Won Mfg Co., Ltd.','port_of_loading':'USUNOURA, JAPAN','vessel':'THORSTREAM','port_of_discharge':'GUASAVE, MEXICO','voyage':'V.060','place_of_delivery':'HAMI, JAPAN','letter_of_credit_number':'M6235089NS67323','letter_of_credit_date':'2011-03-29','country_of_origin':'DE','incoterms':'DAF BELVAL, FRANCE','payment_terms':'CAD','currency':'USD','total_amount':'3550.96'},
  'items':[
   {'hs_code':'3287.74-1109','description':'Heat Shrink Endbell','quantity':'70','unit':'ea','unit_price':'50.04','amount':'1358.66'},
   {'hs_code':'9306.46-8569','description':'Cutter Body Assembly','quantity':'21','unit':'BAG','unit_price':'38.37','amount':'7312.91'}],
  'expected_review':['fields.issue_date','fields.departure_date'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same proforma-reference two-tier-header family.','Issue09-11-2019 and departure09-01-2017 ambiguous. L/C03-29-2011 unambiguous. DAF historical delivery term preserved, CAD under payment is not currency, USD printed monetary headings. BAG raw.']},
 'IMG_OCR_6_T_PL_025567': {
  'fields':{'invoice_number':'991561','invoice_date':'2018-06-27','shipper':'Nagic Textile Co., Ltd.','buyer_reference':'Novolipetsk Steel Co., Ltd.','consignee':'Onbox Health Co., Ltd.','port_of_loading':'INUJIMA, JAPAN','country_of_destination':'PL','vessel':'SILVER DREAM','voyage':'V.133','departure_date':'2019-05-06','port_of_discharge':'SHINJIMA, JAPAN','country_of_origin':'IT'},
  'items':[
   {'description':'Gravity Refuel Filter','hs_code':'9431.56-1409','quantity':'1','unit':'ea','net_weight':'48.26','gross_weight':'519.04','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'Plastic Line. Pole. Tube And Hose','hs_code':'7671.73-5193','quantity':'1','unit':'ft3','net_weight':'36.95','gross_weight':'843.95','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'},
   {'description':'Coupling, For Adapter, With Plug','hs_code':'0978.99-9577','quantity':'9','unit':'pcs','net_weight':'70.13','gross_weight':'911.59','weight_unit':'kg','net_weight_unit':'kg','gross_weight_unit':'kg'}],
  'unscored_source_fields':{'incoterms':'DES AMIENS, FRANCE','payment_terms':'T/T'},
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same certification-footer family.','Date of Issue in invoice reference block follows frozen invoice_date criterion. Buyer Ref not buyer.','Unlabelled final67.93/871.23 line not explicit total or identified fourth item. Shipping marks name other goods. Certification signer not shipper.']},
 'IMG_OCR_6_T_BL_020237': {
  'fields':{'bill_of_lading_number':'HG390026','shipper':'NAKAMURA KENZAI CO, LTD.','consignee':'DAR KEYS EXPRESS','notify_party':'TTEEDE MEDICAL','vessel':'EVER GRADE','voyage':'V.125','port_of_loading':'KUSHIRO, JAPAN','port_of_discharge':'GERZE, TURKEY','delivery_party':'DOLGATE-PALMOLIVE','total_packages':'69','freight_terms':'PREPAID','freight_payable_at':'BUSUM, GERMANY','issue_place':'MERGUI, MYANMAR','issue_date':'2013-04-15'},
  'items':[{'container_number':'DLSU2676055','seal_number':'R266709','package_count':'54','package_type':'PKG','description':'MICRO CRYOGENIC COOLER','gross_weight':'33','weight_unit':'kg','gross_weight_unit':'kg','volume':'102.59','volume_unit':'m3'}],
  'expected_review':['fields.carrier','fields.on_board_date'],
  'notes':['Source image and all Azure word annotations reviewed before predictions. Same VITA combined-transport family.','On-board11-01-2017 ambiguous, issue04-15-2013 unambiguous. Issuer branding/signature lacks explicit carrier role, independent adjudication pending.','Service terms not receipt/delivery locations; ARIKAWA explicitly merchant reference only. Combined container/seal caption establishes roles. Container20GPX4/7 not package count. Prepaid at is freight payment location.']}
})

if __name__ == '__main__':
 path=ROOT/'data/acceptance/source-transcriptions-batch20-additions.json'
 current=json.loads(path.read_text(encoding='utf-8'))
 for name,manual in additions.items():
  if name in current and current[name]!=manual:raise RuntimeError('Existing transcription differs: '+name)
  current[name]=manual
 path.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
