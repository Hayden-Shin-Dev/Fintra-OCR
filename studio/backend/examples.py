# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Small, explicit input fixtures; every example runs the unchanged Audit engine."""
import copy, io, json, zipfile
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
SAMPLE_ROOT = HOME / 'FintraOCR/data/sample'

def sample_catalog():
    manifest = json.loads((SAMPLE_ROOT / 'manifest.json').read_text(encoding='utf-8-sig'))
    return [{'id': i, 'name': Path(row['path']).name, 'document_type': row['expected_type'],
             'image_url': f'/api/samples/{i}/image'} for i, row in enumerate(manifest)]

def sample_path(index):
    manifest = json.loads((SAMPLE_ROOT / 'manifest.json').read_text(encoding='utf-8-sig'))
    if not isinstance(index, int) or index < 0 or index >= len(manifest): raise ValueError('Unknown sample')
    path = Path(manifest[index]['path']).resolve()
    if not path.is_relative_to(SAMPLE_ROOT.resolve()) or not path.is_file(): raise ValueError('Invalid sample path')
    return path

def sample_inputs(ids):
    if not isinstance(ids, list) or len(ids) != 3 or any(type(i) is not int for i in ids): raise ValueError('CI / PL / B/L 이미지를 각각 선택하세요.')
    catalog = {c['id']: c for c in sample_catalog()}
    if {catalog.get(i, {}).get('document_type') for i in ids} != {'commercial_invoice','packing_list','bill_of_lading'}: raise ValueError('3종 문서를 각각 선택하세요.')
    return [('documents', sample_path(i).name, sample_path(i).read_bytes()) for i in ids]
CONFIG = {'lang': 'en', 'audit': {'ledger_amount_basis': 'invoice_total', 'counterparty_role': 'buyer'}}
CASES = [
    ('normal', '일치 · 연결된 3종 증빙', None),
    ('amount', '장부–송장 금액 불일치', 'ledger_invoice_amount_mismatch'),
    ('currency', '통화 불일치', 'currency_mismatch'),
    ('party', '거래처 불일치', 'counterparty_mismatch'),
    ('invoice_quantity', '송장–포장명세서 수량 불일치', 'invoice_packing_quantity_mismatch'),
    ('bl_quantity', '포장명세서–B/L 수량 불일치', 'packing_bl_quantity_mismatch'),
    ('gross_weight', '총중량 불일치', 'gross_weight_mismatch'),
    ('net_weight', '순중량 불일치', 'net_weight_mismatch'),
    ('date', '날짜 불일치', 'date_inconsistency'),
    ('unit', '단위가 달라 비교 불가', 'comparison_not_possible'),
    ('null', '송장 금액 누락', 'missing_required_field'),
    ('missing_bl', 'B/L 누락', 'missing_required_document'),
    ('multiple', '금액·수량·중량 복합 불일치', 'ledger_invoice_amount_mismatch'),
    ('original', '기존 실제 OCR 3종 + 장부', None),
    ('original_amount', '기존 실제 OCR + 장부 금액 변경', None),
    ('original_images', '기존 원본 이미지 3종 · OCR부터 실행', None),
]

def catalog():
    return [{'id': k, 'name': n, 'expected_point': e, 'description':
        ('보유한 실제 문서입니다. 서로 다른 거래의 증빙이 포함되어 미연결·검토 항목이 발생할 수 있습니다. 장부는 OCR에서 만든 예시입니다.' +
         (' 이미지를 다시 OCR하므로 수십 초 이상 걸릴 수 있습니다.' if k == 'original_images' else ' 저장된 실제 OCR 결과와 원본 이미지를 확인합니다.'))
        if k.startswith('original') else
        '기존 합성 테스트 거래를 사용합니다. 3종 매핑 JSON과 장부를 실제 비교 엔진으로 검사합니다. OCR 정확도 검증용 이미지가 아니며 좌표·신뢰도를 만들지 않습니다.'}
        for k, n, e in CASES]

def cell(value):
    return {'value': value, 'status': 'accepted' if value is not None else 'missing',
            'raw_text': value, 'evidence': [], 'ocr_confidence': None, 'provenance': 'synthetic_test'}

def inputs(key):
    if key not in {x[0] for x in CASES}: raise ValueError('알 수 없는 예시입니다.')
    config = copy.deepcopy(CONFIG)
    if key.startswith('original'):
        root = HOME / 'FintraAudit/examples'
        ledger = 'synthetic-ledger-amount-mismatch.csv' if key == 'original_amount' else 'synthetic-ledger-from-ocr.csv'
        files = [('ledger', 'ledger.csv', (root / ledger).read_bytes())]
        for pattern in ('commercial_invoice-*.json', 'packing_list-*.json', 'bill_of_lading-*.json'):
            for path in sorted(root.glob(pattern)):
                if key == 'original_images':
                    obj = json.loads(path.read_text(encoding='utf-8-sig'))
                    for page in obj['ocr']['pages']:
                        image = Path(page['source'])
                        if not image.resolve().is_relative_to((HOME / 'FintraOCR/data').resolve()): raise ValueError('Invalid sample image')
                        files.append(('documents', path.stem + '-' + str(page['page']) + image.suffix, image.read_bytes()))
                else: files.append(('documents', path.name, path.read_bytes()))
        config['audit'].pop('counterparty_role')
        config['_trusted_demo'] = True
        return files, config
    values = dict(invoice_number='SYN-INV-91', purchase_order_number='SYN-PO-71', bill_of_lading_number='SYN-BL-81',
        packing_list_number='SYN-PL-61', buyer_reference='REF-51', document_reference='REF-41', buyer='Synthetic Buyer',
        booking_number='SYN-BOOKING-1', total_packages='1', currency='USD', total_amount='1000', invoice_date='2026-01-02', issue_date='2026-01-02',
        on_board_date='2026-01-02', shipment_date='2026-01-02', departure_date='2026-01-02', gross_weight='110', net_weight='100', weight_unit='KG')
    item = dict(product_code='SYN-PART-1', description='Synthetic part', quantity='10', unit='PCS', package_count='1', package_type='CARTON', gross_weight='110', net_weight='100', weight_unit='KG')
    docs = [{'schema_version': '2.0', 'document_type': t, 'test_fixture': True,
        'fields': {k: cell(v) for k, v in values.items()}, 'items': [{k: cell(v) for k, v in item.items()}]}
        for t in ('commercial_invoice', 'packing_list', 'bill_of_lading')]
    if key in {'amount', 'multiple'}: docs[0]['fields']['total_amount'] = cell('900')
    if key == 'currency': docs[0]['fields']['currency'] = cell('EUR')
    if key == 'party': docs[0]['fields']['buyer'] = cell('Another Synthetic Buyer')
    if key in {'invoice_quantity', 'multiple'}: docs[0]['items'][0]['quantity'] = cell('11')
    if key == 'bl_quantity': docs[2]['items'][0]['quantity'] = cell('12')
    if key in {'gross_weight', 'multiple'}: docs[2]['fields']['gross_weight'] = cell('120')
    if key == 'net_weight': docs[2]['fields']['net_weight'] = cell('90')
    if key == 'date': docs[0]['fields']['invoice_date'] = cell('2026-01-05')
    if key == 'unit': docs[0]['items'][0]['unit'] = cell('KG')
    if key == 'null': docs[0]['fields']['total_amount'] = cell(None)
    if key == 'missing_bl': docs.pop()
    ledger = 'transaction_id,invoice_number,purchase_order_number,transaction_date,posting_date,amount,currency,counterparty,counterparty_role\nSYNTHETIC-1,SYN-INV-91,SYN-PO-71,2026-01-02,2026-01-02,1000,USD,Synthetic Buyer,buyer\n'
    return [('ledger', 'ledger.csv', ledger.encode('utf-8-sig'))] + [('documents', d['document_type'] + '.json', json.dumps(d, ensure_ascii=False, indent=2).encode()) for d in docs], config

def archive(key):
    files, config = inputs(key)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for field, name, blob in files: z.writestr(('ledger/' if field == 'ledger' else 'documents/') + name, blob)
        config.pop('_trusted_demo', None)
        z.writestr('settings.json', json.dumps(config, ensure_ascii=False, indent=2))
        z.writestr('case.json', json.dumps(next(c for c in catalog() if c['id'] == key), ensure_ascii=False, indent=2))
    return out.getvalue()
