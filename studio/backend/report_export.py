# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from grounded_chat import STATUS
import os

def export_pdf(draft,folder,analysis_id):
    font=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/malgun.ttf'
    if 'FintraKorean' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('FintraKorean',str(font)))
    p=Path(folder)/'Fintra-edited-review.pdf'
    ink=colors.HexColor('#202c43');muted=colors.HexColor('#66738b');line=colors.HexColor('#e1e6ef')
    body=ParagraphStyle('body',fontName='FintraKorean',fontSize=9,leading=15,textColor=ink,wordWrap='CJK',spaceAfter=6)
    small=ParagraphStyle('small',parent=body,fontSize=8,leading=12,textColor=muted)
    h=ParagraphStyle('heading',parent=body,fontSize=15,leading=23,spaceBefore=17,spaceAfter=10,keepWithNext=True)
    title=ParagraphStyle('title',parent=h,fontSize=25,leading=35,spaceAfter=20)
    def para(text,style=body):return Paragraph(escape(str(text if text is not None else '')).replace('\n','<br/>'),style)
    def table(rows,widths):
        t=Table([[para(cell,small if i==0 else body) for cell in row] for i,row in enumerate(rows)],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf1f8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8f9fc')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,0),.6,line)]))
        return t
    def footer(canvas,doc):
        canvas.saveState();w,height=A4
        canvas.setStrokeColor(line);canvas.line(44,height-43,w-44,height-43)
        canvas.setFont('FintraKorean',8);canvas.setFillColor(muted)
        canvas.drawString(44,height-32,'FINTRA  /  TRANSACTION REVIEW')
        canvas.drawString(44,26,'검토 보조 자료 · 최종 감사 의견을 대체하지 않습니다.')
        canvas.drawRightString(w-44,26,str(doc.page));canvas.restoreState()
    facts=draft.get('facts',{});counts=facts.get('review_result',{}).get('counts',{})
    from review_rules import LABELS
    blocks=[para('검토 완료' if draft.get('reviewed') else '검토용 초안',small),para(draft['title'],title),para(draft.get('summary',''))]
    if draft.get('generation'):
        g=draft['generation'];blocks.append(para('적용 기준: '+str(g.get('framework') or '미지정 · K-IFRS 조건부 참고')+' | AI 초안: '+('일부 항목 검토 대기' if g.get('status')=='partial' else '작성 완료'),small))
    if draft.get('reviewer'):blocks.append(para('검토자: '+draft['reviewer'],small))
    blocks.append(table([['검토 거래','증빙','불일치 영역','일치 영역','필수누락 영역'],[len(facts.get('transactions',[])),facts.get('document_count',0),counts.get('FAIL',0),counts.get('PASS',0),counts.get('MISSING',0)]],[101]*5))
    for tx in facts.get('review_result',{}).get('transactions',[]):
        blocks.append(para(tx['title']+' · '+LABELS[tx['overall_status']],h))
        blocks.append(table([['핵심 검토 영역','결과']]+[[a['title'],LABELS[a['status']]] for a in tx['review_areas']],[330,175]))
        blocks.append(para('필수 누락값 '+str(len(tx['missing_required']))+'건. 보조 필드는 검토 대상 아님(N/A)으로 분류하여 정상·누락 집계에서 제외했습니다.',small))
    blocks.extend([Spacer(1,14),para('01  감사조서 본문',h)])
    for section in draft.get('sections',[]):
        blocks.append(para(section['heading'],h))
        blocks.extend(para(part) for part in section['text'].split('\n\n') if part.strip())
    blocks.extend([para('담당자 검토 의견',h),para(draft.get('conclusion') or '담당자 의견이 아직 작성되지 않았습니다.')])
    for tx in facts.get('transactions',[]):
        blocks.extend([PageBreak(),para('02  비교 내역 · '+tx['title'],h)])
        for status,label in [('flag','불일치'),('review','추가 검토'),('pass','일치 확인'),('cannot_evaluate','정보 부족')]:
            selected=[c for c in tx['checks'] if c['status']==status and c.get('review_status')!='NOT_APPLICABLE']
            if not selected:continue
            blocks.append(para(label,h));rows=[['비교 항목','문서별 확인 값','결과']]
            for c in selected:
                values='\n'.join(dict.fromkeys(v['label']+': '+v['value'] for v in c['values'])) or ('문서 연결 확인' if status=='pass' else '비교에 필요한 값이 없습니다')
                outcome=LABELS.get(c.get('review_status'),STATUS[status])
                if status in {'review','cannot_evaluate'} and c.get('reason_text'):outcome+='\n'+c['reason_text']
                if c['difference'] is not None and status!='pass':outcome+='\n차이 '+str(c['difference'])+' '+c['unit']
                rows.append([c['title'],values,outcome])
            blocks.append(table(rows,[139,278,88]))
        issues=[c for c in tx['checks'] if c['status'] in {'flag','review'}]
        if issues:blocks.extend([PageBreak(),para('03  검토 항목의 원본 근거',h)])
        for c in issues:
            blocks.append(para(c['title'],h))
            for e in c['evidence']:
                text=e['label']+'\n파일: '+e['file']+'\n위치: '+e['location']+'\n원문: '+(e['raw_text'] or '확인되지 않음')
                if e['human_reviewed']:text+='\n사용자가 추출값을 확인 또는 수정했습니다. 원문과 수정값을 구분해 검토하세요.'
                for token in e['tokens']:
                    text+='\n페이지 '+str(token.get('page',''))+' · '+str(token.get('token_id',''))+' · 문자 '+str(token.get('start',''))+'–'+str(token.get('end',''))+'\n위치 좌표: '+str(token.get('bbox',''))
                blocks.append(para(text,small));blocks.append(Spacer(1,8))
    blocks.append(para('직접 연결된 회계기준 없음. 증빙 대조는 회계 인식·측정 요건의 검증과 구분합니다.',small))
    if facts.get('references'):
        blocks.extend([PageBreak(),para('04  후속 검토용 조건부 참고 기준',h)])
        for ref in facts['references']:
            blocks.extend([para(ref['title'],h),para(ref.get('link_reason','후속 검토를 위한 참고 원문입니다.')),para(ref.get('excerpt') or ref['quote']),para(str(ref.get('framework') or '적용체계 확인 필요')+' · '+ref['source_type'],small),para('출처: '+ref['source']['file']+' · '+ref['source']['json_pointer']+' · 원문 범위 '+str(ref['source']['char_start'])+'–'+str(ref['source']['char_end']),small)])
    blocks.append(KeepTogether([Spacer(1,18),para('검토 범위와 제한',h),para('비교 내역은 저장된 검사 결과이며 보고서 편집으로 판정이 변경되지 않습니다. 정보 부족 항목은 정상으로 판단하지 않았습니다. 참고 회계기준의 실제 적용 여부와 최신성은 담당자가 확인해야 합니다.'),para('미연결 증빙: '+str(facts.get('unmatched_count',0))+'개',small),para('분석 '+analysis_id+' · 편집 버전 '+str(draft['revision']),small)]))
    SimpleDocTemplate(str(p),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=62,bottomMargin=48,title=draft['title'],author='Fintra').build(blocks,onFirstPage=footer,onLaterPages=footer)
    return p
