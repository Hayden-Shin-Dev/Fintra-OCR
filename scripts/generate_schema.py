"""Generate the extraction contract tables from the actual engine schema."""
from pathlib import Path
from fintraocr.schemas import catalog
p=Path(__file__).resolve().parents[1]/'SCHEMA.md'
s=p.read_text(encoding='utf-8').split('## commercial_invoice')[0]
for dtype,groups in catalog().items():
 s+=f'## {dtype}\n\n'
 for group,fields in groups.items():
  s+=f'### {group}\n\n| 필드 | 자료형 | 의미 |\n|---|---|---|\n'
  for name,spec in fields.items():s+=f'| {name} | {spec["kind"]} | {spec["description"]} |\n'
  s+='\n'
p.write_text(s,encoding='utf-8')
