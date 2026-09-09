"""Report measured subsets without presenting diagnostics as population accuracy."""
import json,statistics,xml.etree.ElementTree as ET
from pathlib import Path
from fintraocr.schemas import catalog
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def value(r,path):
 for key in path.split('.'):
  r=r[int(key)] if isinstance(r,list) and int(key)<len(r) else r.get(key,{}) if isinstance(r,dict) else {}
 return r.get('value') if isinstance(r,dict) else None
checks=read(ROOT/'data/inventory_checks.json')['checks']
report={'scope':'Diagnostic subset, not exhaustive gold or independent holdout','inventory':{},'regression':{},'generalization_proven':False,'under_20_seconds_sla_proven':False}
for version in ['before','final-v3','after']:
 groups={}
 for folder in (ROOT/'outputs/inventory').iterdir():
  actual_version=next(v for v in ['final-v7','final-v6','final-v5','final-v4'] if (folder/v/'result.json').exists()) if version=='after' else version
  path=folder/actual_version/'result.json'
  if not path.exists():continue
  result=read(path);kind=read(folder/'source.json')['expected_type']
  g=groups.setdefault(kind,{'documents':0,'checks':0,'correct_checks':0,'positive':0,'predicted':0,'correct_positive':0,'errors':[],'seconds':[]})
  g['documents']+=1;g['seconds'].append(read(folder/actual_version/'timing.json')['seconds'])
  for field,expected in checks.get(folder.name,{}).items():
   actual=value(result,field);g['checks']+=1;g['correct_checks']+=actual==expected
   g['positive']+=expected is not None;g['predicted']+=actual is not None;g['correct_positive']+=actual==expected and expected is not None
   if actual!=expected:g['errors'].append({'document':folder.name,'field':field,'expected':expected,'actual':actual})
 for g in groups.values():
  g['subset_precision']=g['correct_positive']/g['predicted'] if g['predicted'] else None
  g['subset_recall']=g['correct_positive']/g['positive'] if g['positive'] else None
  g['median_mapping_seconds']=statistics.median(g['seconds']);g['max_mapping_seconds']=max(g['seconds'])
 report['inventory'][version]=groups
for folder in (ROOT/'outputs/inventory-regression/final-live').iterdir():
 if (folder/'score.json').exists():
  metrics=read(folder/'score.json')
  baseline=ROOT/'outputs/compact-study'/((folder.name+'-final') if folder.name.startswith('external-') else 'qwen3.5-4b/'+folder.name)/'score.json'
  if baseline.exists():metrics['baseline']=read(baseline)
  report['regression'][folder.name]=metrics
tests=ET.parse(ROOT/'outputs/inventory-regression/tests.xml').getroot()
report['tests']=sum(int(s.get('tests','0')) for s in tests.iter('testsuite'))
ui=ROOT/'outputs/inventory-regression/ui-verification.json'
if ui.exists():report['ui']=read(ui)
(ROOT/'outputs/inventory-regression/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# FintraOCR 전체 샘플 재검증 (2026-09-09)','',
'모든 양식에서 정확하다는 주장은 하지 않습니다. 기존의 작은 평가만으로 전체 성능을 설명하기 어려워 제공 이미지 31개(송장 15, 포장명세서 11, 선하증권 5)를 확대 점검했습니다. OCR는 실제 추출본이며 이미지 바이트 해시를 대조해 재사용했습니다. 매핑은 로컬 Qwen3.5 4B를 실제 호출했습니다.','',
'## 수정 사항','',
'모델 요청에서 빠져 있던 필드 의미·상대 좌표를 연결하고, 응답을 후보 토큰 ID와 스키마 필드로 제한했습니다. 문자 구간·라벨/값 구분·당사자 참조·표의 행/열·정규화 검증을 보강했습니다. 알려진 어휘만으로 값을 승인하지 않으며 근거와 구조 검증을 함께 적용합니다.','',
'짧은 품명과 줄바꿈된 품목, 복합 송장/신용장 날짜, 별도 단위 행, 분리된 Notify Party 제목, 공통 컨테이너/화인 열을 수정했습니다. 소재를 제품 코드로, 본문/제목/서명을 라벨로, 같은 번호를 B/L과 주문 번호에 동시에 쓰던 오류를 차단했습니다. 총중량 제목의 각주 기호가 유효한 합계 값을 가리던 문제도 수정했습니다.','',
'소재·색상·배송 출발지·주선인 등록 번호·청구/인도 대상자·견적 번호·신용장 날짜·발행 장소·배송일·품목별 주문 번호를 추가했습니다. [SCHEMA.md](SCHEMA.md)에 코드에서 생성한 전체 필드/자료형/의미가 있습니다. 새 필드는 기존 키를 유지하는 추가 방식이며, 정답이 없는 새 필드의 추출률을 정확도로 취급하지 않습니다.','',
'## 제공 데이터 진단 부분집합','',
f'직접 점검한 {sum(map(len,checks.values()))}개 조건은 발견한 오류와 회귀를 확인하기 위한 부분집합입니다. 전체 필드 정답이나 독립 일반화 평가가 아닙니다. 아래 정밀도/재현율은 이 부분집합에만 적용됩니다. null 정답은 정밀도·재현율의 true positive로 세지 않았습니다. 새 필드를 before에서 찾지 못하면 누락으로 계산하므로 스키마 확장 효과도 포함됩니다.','',
'| 유형 | before P / R | 최종 P / R | 최종 조건 일치 | before 매핑 중앙 / 최대 | 최종 매핑 중앙 / 최대 |','|---|---:|---:|---:|---:|---:|']
def pct(x):return '-' if x is None else f'{x*100:.1f}%'
for kind,g in report['inventory']['after'].items():
 b=report['inventory']['before'][kind]
 lines.append(f"| {kind} | {pct(b['subset_precision'])} / {pct(b['subset_recall'])} | {pct(g['subset_precision'])} / {pct(g['subset_recall'])} | {g['correct_checks']}/{g['checks']} ({g['documents']}문서) | {b['median_mapping_seconds']:.2f} / {b['max_mapping_seconds']:.2f}초 | {g['median_mapping_seconds']:.2f} / {g['max_mapping_seconds']:.2f}초 |")
lines+=['','## 기존 고정 정답과 외부 문서','',
'합성 문서와 제공 문서, 외부 공개 예제는 분리합니다. 외부 예제도 수정 과정에서 사용했으므로 이제는 독립 미관측 검증셋이 아닙니다. 동결한 원래 정답을 그대로 사용합니다.','',
'| 사례 | before P / R | 최종 P / R | 매핑 시간 |','|---|---:|---:|---:|']
for name,m in report['regression'].items():
 b=m.get('baseline',{})
 lines.append(f"| {name} | {pct(b.get('precision'))} / {pct(b.get('recall'))} | {pct(m['precision'])} / {pct(m['recall'])} | {m['seconds']:.2f}초 |")
if report.get('ui'):
 lines+=['','## UI 실제 실행','', '| 작업 | 전체 | 초기화 | OCR | 매핑 |','|---|---:|---:|---:|---:|']
 for name in ['full','remap','ocr_only','latest_remap']:
  if name not in report['ui']:continue
  job=report['ui'][name];tm=job['timings']
  lines.append(f"| {name} | {job['wall_seconds']:.2f}초 | {tm.get('initialization_seconds',0):.2f}초 | {tm.get('ocr_seconds',0):.2f}초 | {tm.get('mapping_seconds',0):.2f}초 |")
 lines+=['','실제 GPU OCR, 전체 매핑, 저장 OCR 재매핑, JSON/처리 기록 다운로드를 API로 실행했습니다. 브라우저에서 전체 적용 필드·null·품목 수량/단위/포장 수 및 M/T의 원문·토큰 p1t46[0:3] 표시를 확인했습니다.']
lines+=['','## 한계와 실행 기록','',
'모델 응답 재생(final-v5-replay, replay-current)은 코드 변경의 영향만 확인하며 실제 모델 실행 시간으로 사용하지 않았습니다. before, final-v3, final-v4의 원응답·proposal·결과·시간은 outputs/inventory에 보존합니다. 마지막 확인에서 발견한 오류는 final-v5~v7 실제 재호출 결과로 대체해 집계합니다. 새 평가 정답은 엔진에서 읽지 않습니다.','',
'저해상도 문서는 2배 확대 OCR와 별도 키릴 문자 인식기까지 추가 시험했습니다. 확대는 제목을 복구하지 못했고, 키릴 인식기는 일부 문자를 개선했지만 문서 종류가 unknown으로 반환돼 기본 경로로 채택하지 않았습니다. 이 실험을 개선 성공으로 계산하지 않았습니다.','',
'가려진 원본 및 OCR가 열 제목을 훼손한 문서에서는 미추출이 남습니다. NV003382의 수량 30 sets는 복구했지만 단가 제목은 OCR가 잘못 읽어 단가가 미추출 상태입니다. 숫자 220을 중량으로 승인하지 않고 검토 대상으로 남겼습니다. 모호한 날짜, Scotland의 국가 코드, 오독된 제품 코드/품명은 자동으로 정답을 만들지 않습니다. 송장의 Exporter를 Seller로 합치지 않아 기존 정답과 1건 차이가 있으며, Montana는 원본 OCR와 정답의 대소문자 차이 1건을 그대로 오답으로 보고합니다.','',
'GPU RTX 4050 Laptop 6GB에서 측정했습니다. 다른 Ollama 서버 및 GPU 앱이 동시에 관측되어 시간 비교에는 경합 영향이 있습니다. 초기화/OCR/매핑은 UI 작업별 timing JSON으로 분리했습니다. 캐시 OCR 매핑 시간과 이미지 전체 처리 시간을 혼동하지 않아야 합니다. 모든 문서의 20초 이내 처리는 보장하지 못합니다.','',
f"회귀 테스트 {report['tests']}개 통과 기록은 outputs/inventory-regression/tests.xml에 있습니다. 자동 테스트 통과를 일반화의 증명으로 취급하지 않습니다.",'',
'실행한 명령(프로젝트 폴더에서):','',
'```powershell',
"& 'C:\\Users\\shinm\\.cache\\fintraocr-venv\\Scripts\\python.exe' -m scripts.audit_inventory --version final-v4",
"& 'C:\\Users\\shinm\\.cache\\fintraocr-venv\\Scripts\\python.exe' -m scripts.check_inventory --version final",
"& 'C:\\Users\\shinm\\.cache\\fintraocr-venv\\Scripts\\python.exe' -m pytest -q --junitxml=outputs/inventory-regression/tests.xml",
'```','',
'[UI](http://127.0.0.1:8768) · [JSON 보고서](outputs/inventory-regression/report.json) · [전체 스키마](SCHEMA.md)','',
'인도 조건의 과거 코드(DAT/DAF/DES/DEQ/DDU)도 원문 그대로 보존합니다. 근거: [ICC 2010 소개](https://iccwbo.org/wp-content/uploads/sites/3/2010/01/ICC-Introduction-to-the-Incoterms-2010.pdf). 국가·단위 변환과 별개로 법적 의미를 판단하거나 최신 코드로 바꾸지 않습니다.']
(ROOT/'INVENTORY-VALIDATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Wrote inventory report; inspect errors before delivery.')
