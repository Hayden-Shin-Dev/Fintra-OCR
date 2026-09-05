"""Audit every frozen field against raw OCR. Never supply gold to extractors."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_field_extraction import normalize_field
from fintra.normalization.values import normalize_date

CATEGORIES = (
    'OCR_TEXT_ERROR', 'OCR_REGION_MISSING', 'ANCHOR_DETECTION_ERROR',
    'LABEL_VALUE_ASSOCIATION_ERROR', 'WRONG_SECTION', 'WRONG_PARTY_BLOCK',
    'MULTILINE_BLOCK_ERROR', 'TABLE_HEADER_ERROR', 'TABLE_COLUMN_ERROR',
    'TABLE_ROW_ERROR', 'TOTAL_VS_SUBTOTAL_ERROR', 'DATE_ASSOCIATION_ERROR',
    'UNIT_ASSOCIATION_ERROR', 'NORMALIZATION_ERROR', 'CANDIDATE_RANKING_ERROR', 'OTHER',
)

def bounds(poly):
    if len(poly) == 4 and isinstance(poly[0], (float, int)):
        return tuple(poly)
    if isinstance(poly[0], (float, int)):
        poly = list(zip(poly[::2], poly[1::2]))
    return min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)

def overlap(a, b):
    intersection = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    return intersection / max(1, (a[2]-a[0])*(a[3]-a[1]))

def words(text):
    return re.findall(r'\w+', str(text).replace('쉼표', ',').casefold())

def lexical(text):
    return ' '.join(words(text))

def reading_text(regions):
    lines = []
    for region in sorted(regions, key=lambda r: (r['box'][1], r['box'][0])):
        x1,y1,x2,y2 = region['box']
        cy=(y1+y2)/2
        line = next((ln for ln in lines if abs(cy-ln[0]) <= max(1, min(y2-y1, ln[1])*.65)), None)
        if line is None:
            lines.append([cy,y2-y1,[region]])
        else:
            line[2].append(region)
    return ' '.join(r['text'] for ln in sorted(lines) for r in sorted(ln[2],key=lambda r:r['box'][0]))

def audit(cases: Path, report: Path):
    report.mkdir(parents=True, exist_ok=True)
    frozen=report/'frozen_baseline'
    if not frozen.exists():
        frozen.mkdir()
        for name in ('field_results.csv','field_metrics.json','FIELD_EXTRACTION_EVALUATION.md'):
            shutil.copy2(report/name, frozen/name)
    baseline=list(csv.DictReader((frozen/'field_results.csv').open(encoding='utf-8-sig')))
    previous={(r['case_id'],r['field_name']):r for r in baseline}
    rows=[]
    hashes={}
    for case in sorted(cases.iterdir()):
        if not (case/'case_manifest.json').is_file():
            continue
        manifest=json.loads((case/'case_manifest.json').read_text(encoding='utf-8'))
        gt=json.loads((case/'gt.json').read_text(encoding='utf-8'))
        predictions=list((case/'outputs'/'recognition').glob('*.json'))
        if len(predictions)!=1:
            raise ValueError(f'{case}: expected one recognition JSON')
        payload=json.loads(predictions[0].read_text(encoding='utf-8'))
        for p in (case/'case_manifest.json',case/'gt.json',predictions[0],case/'outputs'/'detection.json'):
            hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        regions=[{'index':i,'text':r['text'].replace('쉼표',','),'box':bounds(r['bbox'])} for i,r in enumerate(payload['regions'])]
        for field in manifest['gold_fields']:
            if field['status']!='available':
                continue
            name=field['field_name']; value=str(field['value'])
            old=previous[(manifest['case_id'],name)]
            indices=field['source_token_indices']
            source=[{'index':i,'text':gt['bbox'][i]['data'],'box':(min(gt['bbox'][i]['x']), min(gt['bbox'][i]['y']), max(gt['bbox'][i]['x']), max(gt['bbox'][i]['y']))} for i in indices]
            matched=[r for r in regions if any(overlap(t['box'],r['box'])>=.35 or overlap(r['box'],t['box'])>=.35 for t in source)]
            raw_text=' '.join(r['text'] for r in matched)
            order_text=reading_text(matched)
            target=Counter(words(value)); found=Counter(words(raw_text))
            # Optimistic evidence availability: gold may reorder observed tokens,
            # but may not invent missing characters. This is NOT a score matcher.
            bag_present=bool(target) and not (target-found)
            norms=[normalize_field(r['text'],name) for r in matched]
            expected=normalize_field(value,name)
            numeric_or_date=any(k in name for k in ('date','quantity','amount','price','weight','currency','package_count'))
            normalized_present=numeric_or_date and expected is not None and expected in norms+[normalize_field(order_text,name)]
            present=bool(bag_present or normalized_present or lexical(value)==lexical(order_text))
            matched_tokens=sum(min(v,found[k]) for k,v in target.items())
            coverage=matched_tokens/max(1,sum(target.values()))
            selected_box=json.loads(old['bbox']) if old.get('bbox') else None
            selected=[r['index'] for r in regions if selected_box and overlap(r['box'],bounds(selected_box))>=.5]
            flags=[]
            if 'date' in name and not normalize_date(value): flags.append('DATE_GOLD_REQUIRES_REVIEW')
            if name.endswith('number') and re.search(r'\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b|\d{2}-\d{2}-\d{4}',value,re.I): flags.append('DATE_IN_IDENTIFIER_GOLD')
            if name.startswith('port_') and re.search(r'\bV\.\d|\bCFS/CFS\b',value): flags.append('VOYAGE_OR_SERVICE_IN_PORT_GOLD')
            if any(k in name for k in ('seller','buyer','exporter','consignee','notify_party','shipper')) and re.search(r'\b(?:TEL|FAX)\b|\)\+',value): flags.append('PARTY_GOLD_INCLUDES_ADDRESS_CONTACT_BLOCK')
            if lexical(reading_text(source))!=lexical(value): flags.append('GOLD_READING_ORDER_DIFFERS_FROM_LINES')
            if name=='currency' and len(words(value))>1: flags.append('REPEATED_CURRENCY_GOLD')
            pred=old.get('predicted_value','')
            null_match=old['status']=='normalized_match' and normalize_field(pred,name) is None and expected is None
            if null_match: flags.append('FALSE_MATCH_BOTH_NORMALIZATIONS_NULL')
            category='OTHER'; reason='Existing match; review flags remain independent of outcome.'
            if null_match:
                category='NORMALIZATION_ERROR'; reason='Two failed parses compared equal.'
            elif old['status'] not in ('exact_match','normalized_match'):
                if not matched:
                    category='OCR_REGION_MISSING'; reason='No recognition region overlaps annotated field evidence.'
                elif not present:
                    category='OCR_TEXT_ERROR'; reason='Annotated text is not recoverable verbatim from overlapping OCR tokens.'
                elif 'items[' in name:
                    category='TABLE_ROW_ERROR'; reason='Field evidence exists; indexed table row/cell differs.'
                elif any(k in name for k in ('seller','buyer','exporter','consignee','notify_party','shipper')):
                    category='WRONG_PARTY_BLOCK'; reason='Available party tokens and selected block differ.'
                elif 'unit' in name:
                    category='UNIT_ASSOCIATION_ERROR'; reason='Available unit token was not selected as field value.'
                elif 'date' in name:
                    category='DATE_ASSOCIATION_ERROR'; reason='Available date evidence and selected value differ.'
                elif 'total' in name:
                    category='TOTAL_VS_SUBTOTAL_ERROR'; reason='Total evidence exists but selected monetary candidate differs.'
                elif len(source)>1:
                    category='MULTILINE_BLOCK_ERROR'; reason='Available token group and selected or ordered block differ.'
                else:
                    category='LABEL_VALUE_ASSOCIATION_ERROR'; reason='Available value and selected candidate differ.'
            features='Use line overlap, reading order, anchor boundaries, datatype and competing section headings; do not use GT at inference.'
            rows.append({'case_id':manifest['case_id'],'document_id':manifest['document_id'],'document_type':manifest['document_type'],
                'field_name':name,'gt_value':value,'baseline_status':old['status'],'evidence_present':present,
                'evidence_token_coverage':coverage,'ocr_region_indices':json.dumps([r['index'] for r in matched]),
                'ocr_evidence_text':order_text,'selected_candidate':pred,'selected_region_indices':json.dumps(selected),
                'category':category,'reason':reason,'distinguishing_features':features,
                'gt_review_flags':';'.join(flags),'source_token_indices':json.dumps(indices),
                'evidence_status':'present' if present else 'no_region' if not matched else 'text_incomplete'})
    with (report/'error_analysis.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    n=len(rows); present=sum(r['evidence_present'] for r in rows)
    false_parse=sum('FALSE_MATCH' in r['gt_review_flags'] for r in rows)
    extractor=sum(r['evidence_present'] and r['baseline_status'] not in ('exact_match','normalized_match') for r in rows)
    counts=Counter(r['category'] for r in rows)
    summary={'available_fields':n,'GT_EVIDENCE_PRESENT_RATE':present/n,'EXTRACTOR_ERROR_RATE':extractor/n,
        'OCR_LIMITED_RATE':(n-present)/n,'EXTRACTION_UPPER_BOUND':present/n,
        'upper_bound_scope':'Operational token-availability estimate against legacy gold, NOT a proven mathematical ceiling or validated semantic accuracy.',
        'false_null_matches':false_parse,'fields_with_gt_review_flags':sum(bool(r['gt_review_flags']) for r in rows),
        'category_counts':dict(counts),'metrics_valid_for_90_percent_claim':False,
        'reason':'Legacy semantic gold was generated with one fixed pixel template across multiple forms. Full independent semantic review remains required.'}
    (report/'error_analysis.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (report/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    lines=['# Field evidence audit','',f'All {n} existing available fields audited; no field removed from denominator.','',
        'This is an automated geometry/text audit. Error categories are diagnostic hypotheses, not 492 individually image-reviewed semantic judgments.','',
        '```json',json.dumps(summary,indent=2),'```','',
        'Evidence presence uses overlapping raw OCR region tokens, allowing token reorder for an optimistic evidence bound. Similarity is never used to score a field correct.',
        'The historical 39.23% includes false matches from None == None. Keep the frozen snapshot and recompute baseline/final with identical corrected scoring.',
        'Source review: bl-002 visibly has B/L HG732993, shipment APR 24 2009, and a shipper block. Legacy gold assigns the shipment date to bl_number and excludes shipper/shipment_date. This is a gold-generation defect, not document ambiguity.',
        'Missing OCR text, missed regions, wrong sections, word ordering and legacy gold defects must be resolved separately. No automatic gold rewrite from extractor predictions is permitted.','']
    (report/'ERROR_ANALYSIS.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cases',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();audit(args.cases,args.output)
