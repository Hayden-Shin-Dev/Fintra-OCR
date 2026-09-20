# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Human-readable PDF working paper, with original values and source citations."""
import os
from datetime import datetime
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether

STATUS={'pass':'일치','flag':'불일치','review':'검토 필요','cannot_evaluate':'정보 부족',
        'generated_review_required':'근거 확인·사용자 검토 필요','insufficient_evidence':'관련 근거 부족','generation_failed':'설명 생성 실패'}
DOCS={'ledger':'장부','commercial_invoice':'상업송장','packing_list':'포장명세서','bill_of_lading':'선하증권'}
FIELDS={'amount':'금액','total_amount':'송장 총액','currency':'통화','quantity':'상품 수량','unit':'수량 단위',
 'gross_weight':'총중량','net_weight':'순중량','weight_unit':'중량 단위','package_count':'포장 개수',
 'invoice_number':'송장 번호','bill_of_lading_number':'B/L 번호','purchase_order_number':'주문 번호',
 'transaction_date':'장부 거래일','issue_date':'발행일','invoice_date':'송장 발행일','shipment_date':'선적일',
 'package_type':'포장 종류','packing_list_number':'포장명세서 번호','buyer_reference':'구매자 참조번호','document_reference':'문서 참조번호','booking_number':'예약 번호',
 'buyer':'구매자','seller':'판매자','shipper':'송하인','consignee':'수하인','counterparty':'거래처'}

def label(text):
    for key,value in sorted(FIELDS.items(),key=lambda item:-len(item[0])):text=text.replace(key,value)
    return text

def display(value):
    if value is None:return '확인할 값 없음'
    if isinstance(value,dict):return ' / '.join(f'{FIELDS.get(k,k)}: {display(v)}' for k,v in value.items())
    if isinstance(value,list):return ' / '.join(display(v) for v in value)
    return str(value)

def create_report(result,path,analysis_id=''):
    font=Path(os.environ.get('FINTRA_REPORT_FONT',str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/malgun.ttf')))
    if not font.is_file():raise FileNotFoundError('한글 보고서 글꼴이 없습니다. FINTRA_REPORT_FONT를 설정하세요.')
    if 'FintraKR' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('FintraKR',str(font)))
    normal=ParagraphStyle('body',fontName='FintraKR',fontSize=9,leading=14,wordWrap='CJK',spaceAfter=7)
    title=ParagraphStyle('title',parent=normal,fontSize=24,leading=32,textColor=colors.HexColor('#17443F'),spaceAfter=18)
    h=ParagraphStyle('heading',parent=normal,fontSize=14,leading=21,spaceBefore=14,spaceAfter=10,keepWithNext=True)
    small=ParagraphStyle('small',parent=normal,fontSize=8,leading=12,textColor=colors.HexColor('#52646A'))
    p=lambda text,style=normal:Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    story=[p('fintra | 거래 검토보고서',title),p('입력 자료와 원본 근거를 바탕으로 작성한 검토 초안입니다. 최종 감사 의견이나 회계기준 적용 확정이 아닙니다.',small),
           p('생성 일시 '+datetime.now().astimezone().isoformat(timespec='seconds')+'\n분석 ID '+analysis_id,small)]
    audit=result.get('audit') or {};review=result.get('standards_review') or {};transactions=audit.get('transactions',[])
    summary=audit.get('summary',{})
    story.extend([p('검토 개요',h),p(f"연결된 거래 {len(transactions)}건 · 미연결 증빙 {summary.get('unmatched_documents',0)}건 · 감사 포인트 {summary.get('audit_points',0)}건")])
    if result.get('failures'):story.append(p('일부 입력 또는 처리 단계가 실패했습니다. 누락된 자료를 정상으로 간주하지 마세요.'))
    if not review:story.append(p('기준 검색·설명 결과가 없습니다. 비교 결과만 포함했습니다.'))
    entities={d['id']:DOCS.get(kind,kind) for t in transactions for kind,d in t.get('documents',{}).items()}
    find={f['audit_point_id']:f for f in review.get('findings',[])}
    def table(rows,widths):
        t=Table([[p(c,small) for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8F1EF')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#72978D')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#DCE4E3')),
            ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        return t
    def finding(point):
        story.extend([p(STATUS.get(point.get('status'),point.get('status',''))+' | '+point.get('title','검토 항목'),h),p(point.get('description',''))])
        ev=point.get('evidence',[])
        if ev:
            rows=[['비교 항목','원본에서 확인한 값','원본 위치']]
            for e in ev:
                src=e.get('source',{});original=e.get('original') or {};spans=original.get('evidence',[]) if isinstance(original,dict) else []
                loc='장부 행 '+str(src['row_index'])+' / '+str(src.get('original_column','')) if 'row_index' in src else '\n'.join('페이지 '+str(s.get('page'))+' / '+str(s.get('selected_text',s.get('text',''))) for s in spans)
                source_name='장부' if str(src.get('entity_id','')).startswith('ledger:') else entities.get(src.get('entity_id'),'증빙')
                rows.append([source_name+' · '+FIELDS.get(e.get('field_name'),e.get('field_name','')),display(e.get('normalized_value')),loc or '근거 위치 미확인'])
            story.append(table(rows,[105,120,285]))
        diff=point.get('values',{}).get('difference')
        if diff is not None:story.append(p('계산된 차이: '+display(diff)))
        f=find.get(point.get('audit_point_id'))
        if not f:story.append(p('이 항목의 회계처리기준 설명은 생성되지 않았습니다.',small));return
        exp=f['explanation'];sources={s['id']:s for s in f['retrieval']['results']}
        story.append(p('관련 기준·자료: '+STATUS.get(exp['status'],exp['status']),small))
        if not exp['citations']:story.append(p('해당 문제를 직접 뒷받침하는 인용 근거가 확보되지 않았습니다. 검색 순위를 적용 근거로 확정하지 않습니다.',small))
        for citation in exp['citations']:
            source=sources[citation['source_id']]
            story.extend([p(source['title']+' ['+source['source_type']+']'),p(citation['quote']),
                p('출처: '+source['source']['file']+'\n원문 위치: '+source['source']['json_pointer']+' / 문자 '+str(citation['source_char_start'])+'-'+str(citation['source_char_end'])+'\n근거 ID: '+source['id'],small)])
        for action in exp['review_actions']:story.append(p('확인 사항: '+action['text']))
    for transaction in transactions:
        identity=((transaction.get('ledger') or {}).get('fields') or {}).get('transaction_id',{}).get('value') or transaction.get('transaction_id','')
        story.extend([Spacer(1,16),p('거래 '+str(identity),h)])
        for point in transaction.get('audit_points',[]):finding(point)
        passed=[c for c in transaction.get('checks',[]) if c['status']=='pass' and c.get('values',{}).get('observed')]
        story.append(p('일치한 주요 값',h))
        if passed:story.append(table([['비교 항목','확인한 값']]+[[label(c['title']),display(c['values']['observed'])] for c in passed[:12]],[220,290]))
        else:story.append(p('값까지 일치 확인한 항목이 없습니다.'))
        unavailable=[c for c in transaction.get('checks',[]) if c['status']=='cannot_evaluate']
        if unavailable:
            story.append(p('추가 확인 필요',h))
            story.append(p(f'{len(unavailable)}개 검사는 필요한 값·문서·비교 조건 부족으로 판정하지 못했습니다. 정상 판정에 포함하지 않습니다.'))
            story.append(table([['검사','미확인 값']]+[[label(c['title']),display(c.get('values',{}).get('observed'))] for c in unavailable],[220,290]))
    for point in audit.get('unmatched_audit_points',[]):finding(point)
    story.extend([Spacer(1,15),p('처리 범위와 한계',h),p('회계기준·질의회신·상담·실무해설은 구분해 인용했습니다. 데이터셋의 분류가 공식성이나 최신성을 보증하지 않습니다. 기준 적용과 최종 감사 판단은 검토자가 원문·거래 조건을 확인한 뒤 결정해야 합니다.',small)])
    if review.get('status')=='partial':story.append(p('일부 설명 생성에 실패했습니다. 앱에서 실패한 항목을 확인하세요.',small))
    def footer(canvas,doc):
        canvas.setFont('FintraKR',8);canvas.setFillColor(colors.HexColor('#52646A'))
        canvas.drawString(42,24,'FINTRA | 검토 초안');canvas.drawRightString(A4[0]-42,24,str(doc.page))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.partial.pdf')
    SimpleDocTemplate(str(temp),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=44,title='Fintra 거래 검토보고서',author='Fintra').build(story,onFirstPage=footer,onLaterPages=footer)
    temp.replace(path)
    return {'status':'complete','filename':path.name,'bytes':path.stat().st_size,'format':'pdf','draft':True}
