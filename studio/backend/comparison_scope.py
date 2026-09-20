# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Separate supplementary checks from required comparison coverage, without altering evidence."""
OPTIONAL_REFERENCES={'packing_list_number','buyer_reference','document_reference','booking_number'}
OPTIONAL_ITEM={'item_gross_weight_comparison','item_net_weight_comparison','item_package_count_comparison'}

def scope_for(check, transaction):
    if check.get('status')!='cannot_evaluate':return 'required'
    # A value awaiting human confirmation is never an optional absence.
    if check.get('reason') not in {'required_value_missing','value_or_unit_missing'}:return 'required'
    evidence=check.get('evidence',[])
    if any(isinstance(e.get('original'),dict) and e['original'].get('status')=='review' for e in evidence):return 'required'
    kind=check.get('type','')
    linked=any(c.get('status')=='pass' and c.get('type','').startswith('reference_') for c in transaction.get('checks',[]))
    if linked and kind.startswith('reference_') and kind.removeprefix('reference_') in OPTIONAL_REFERENCES:return 'supplementary'
    if kind=='cross_document_date_review' and evidence and all(e.get('normalized_value') is None for e in evidence):return 'supplementary'
    if kind=='cross_document_date_review' and check.get('context',{}).get('event')=='on_board_date':
        docs={d['id']:k for k,d in transaction.get('documents',{}).items()}
        missing=[e for e in evidence if e.get('normalized_value') is None]
        if missing and all(docs.get(e.get('source',{}).get('entity_id')) in {'commercial_invoice','packing_list'} for e in missing):return 'supplementary'
    if kind in OPTIONAL_ITEM:
        main=[e for e in evidence if e.get('field_name') in {'gross_weight','net_weight','package_count'}]
        if main and all(e.get('normalized_value') is None for e in main):return 'supplementary'
        # Invoices need not repeat packing quantities; units missing for an
        # observed quantity remain required and cannot be waived here.
        docs={d['id']:k for k,d in transaction.get('documents',{}).items()}
        missing=[e for e in main if e.get('normalized_value') is None]
        if missing and all(docs.get(e.get('source',{}).get('entity_id'))=='commercial_invoice' for e in missing):return 'supplementary'
    return 'required'

def coverage(transaction):
    checks=transaction.get('checks',[])
    extra=[c['check_id'] for c in checks if scope_for(c,transaction)=='supplementary']
    return {'supplementary_ids':extra,'required_missing_ids':[c['check_id'] for c in checks if c['status']=='cannot_evaluate' and c['check_id'] not in extra],
            'note':'비교 범위 내 일치이며 회계처리 적정성에 대한 감사 의견은 아닙니다.'}
