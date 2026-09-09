import json
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
from fintraocr.compact import CompactSelector
from fintraocr.models import OCRDocument
from fintraocr.mapping import MappingEngine
from scripts.run_benchmark import score
p=Path('data/ui/664588c0c97c41ea809143df3503b07e');tr=json.loads((p/'mapping-trace.json').read_text(encoding='utf-8'));responses=iter([x['response'] for x in tr['trace'] if 'response' in x])
with patch('fintraocr.compact.urlopen',side_effect=lambda *a,**kw:BytesIO(json.dumps(next(responses)).encode())):
 s=CompactSelector('qwen3.5:4b');r=MappingEngine(s).map(OCRDocument.model_validate_json((p/'ocr.json').read_text(encoding='utf-8')))
m=score(json.loads(Path('data/external/lakay.gold.json').read_text(encoding='utf-8')),r.model_dump());print(json.dumps(m,ensure_ascii=False,indent=2));Path('outputs/compact-study/lakay-replay.json').write_text(json.dumps({'score':m,'result':r.model_dump(),'trace':s.metadata},ensure_ascii=False,indent=2),encoding='utf-8')
