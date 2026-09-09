"""Frozen legacy field scores, separate real/synthetic and per-document results."""
import argparse,json,time,hashlib
from pathlib import Path
from fintraocr.models import OCRDocument
from fintraocr.mapping import MappingEngine
from fintraocr.grounded import GroundedSelector
from scripts.run_benchmark import score
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='*');p.add_argument('--replay',action='store_true');p.add_argument('--manifest',default='data/holdout/manifest.json');args=p.parse_args()
    entries=json.loads((ROOT/args.manifest).read_text(encoding='utf-8'))
    for e in entries:
        if args.ids and e['id'] not in args.ids:continue
        folder=ROOT/'outputs/structural-v2'/e['id'];folder.mkdir(parents=True,exist_ok=True)
        s=GroundedSelector('qwen2.5:7b')
        if args.replay and (folder/'trace.json').exists():
            old=json.loads((folder/'trace.json').read_text(encoding='utf-8'))
            response=old['trace'][0]['response']['message']['content']
            def replay(document):
                s.metadata=old
                s.metadata['trace']=old['trace'][:1]
                return json.loads(response)
            s.label_request=replay
        d=OCRDocument.model_validate_json((ROOT/'outputs/benchmark'/e['id']/'medium.ocr.json').read_text(encoding='utf-8'))
        started=time.monotonic()
        try:
            r=MappingEngine(s).map(d)
            (folder/'result.json').write_text(r.model_dump_json(indent=2),encoding='utf-8')
            m=score(json.loads((ROOT/e['gold']).read_text(encoding='utf-8')),r.model_dump())
            m.update(seconds=time.monotonic()-started,replayed=args.replay,document_type=e['kind'],split=e['split'],source='sample' if e['id'].startswith('sample_') else 'synthetic')
            m['code_sha256']=hashlib.sha256(b''.join((ROOT/'fintraocr'/n).read_bytes() for n in ['grounded.py','layout.py','domain.py','mapping.py','schemas.py','normalize.py','models.py'])).hexdigest()
            (folder/'score.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
            print(e['id'],m['precision'],m['recall'],round(m['seconds'],1),flush=True)
        except Exception as exc:
            (folder/'error.json').write_text(json.dumps({'error':str(exc)}),encoding='utf-8');print(e['id'],str(exc),flush=True)
        finally:
            (folder/'trace.json').write_text(json.dumps(s.metadata,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
