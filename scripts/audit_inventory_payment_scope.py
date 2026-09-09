"""Versioned source-image correction; never reads engine predictions."""
import hashlib,json
from pathlib import Path

source=Path('data/sample/commercial_invoice/IMG_OCR_6_T_NV_003058.png')
original=Path('data/inventory_checks.json')
data=json.loads(original.read_text(encoding='utf-8'))
document='IMG_OCR_6_T_NV_003058';field='fields.payment_terms'
assert data['checks'][document][field]=='By T/T'
data['checks'][document][field]='By T/T 2 % : Upon signing the contract 19 % : Upon cargo arrival at the discharge port 48 % : After inspection within 61 days from cargo arrival at the discharging port'
data['source_audit']={
 'original_checks_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
 'image_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'document':document,'field':field,'previous_expected':'By T/T',
 'reason':'Image reviewed directly: payment terms include the printed instalment schedule. Old check scored only the payment method, inconsistent with the frozen development30 full-payment-terms criterion.',
 'limitations':['Original checks remain unchanged and must still be reported.','Compare both baseline and candidate on this same audited file.','Single source review does not replace independent acceptance adjudication.']}
target=Path('data/inventory_checks-source-v2.json')
if target.exists() and json.loads(target.read_text(encoding='utf-8'))!=data:raise RuntimeError('Existing audit differs')
target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
