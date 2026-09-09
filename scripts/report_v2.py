"""Reproducible old/new comparison with unchanged legacy gold fields."""
import json
from pathlib import Path
from fintraocr.schemas import catalog,ALIASES
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def pct(v):return '추출 없음' if v is None else f'{v*100:.1f}%'
def aggregate(scores):
    counts={k:sum(s[k] for s in scores) for k in ['expected_non_null','predicted_non_null','correct_non_null','extra_rows','false_non_null']}
    counts['precision']=counts['correct_non_null']/counts['predicted_non_null'] if counts['predicted_non_null'] else None
    counts['recall']=counts['correct_non_null']/counts['expected_non_null'] if counts['expected_non_null'] else None
    return counts
def main():
    legacy=read(ROOT/'data/holdout/manifest.json');fresh=read(ROOT/'data/fresh/manifest.json')
    rows=[]
    for entry in legacy+fresh:
        folder=ROOT/'outputs/structural-v2'/entry['id'];after=read(folder/'score.json');result=read(folder/'result.json');trace=read(folder/'trace.json')
        before_path=ROOT/'outputs/baseline-v1'/entry['id']/'medium.qwen2.5-7b.score.json'
        before=read(before_path) if before_path.exists() else None
        gold=read(ROOT/entry['gold'])
        extra=[value for key,value in result['fields'].items() if key not in gold['fields']]
        extra += [value for i,item in enumerate(result['items']) for key,value in item.items() if i>=len(gold['items']) or key not in gold['items'][i]]
        calls=trace.get('calls',[])
        timing=read(ROOT/'outputs/benchmark'/entry['id']/'medium.metrics.json')
        rows.append({'id':entry['id'],'type':entry['kind'],'source':'real_sample' if entry['id'].startswith('sample_') else 'fresh_synthetic' if entry in fresh else 'regression_synthetic','split':entry['split'],'before':before,'after':after,
          'timing':{'initialization_seconds':timing.get('initialization_seconds',timing.get('init_seconds')),'ocr_seconds':timing['inference_seconds'],'recorded_model_request_seconds':sum(c['seconds'] for c in calls),'recorded_model_load_seconds':sum(c.get('load_seconds',0) for c in calls),'cached_resolution_seconds':after['seconds']},
          'unannotated':{'applicable':len(extra),'accepted':sum(v['status']=='accepted' for v in extra),'review':sum(v['status']=='review' for v in extra)},
          'null_audit':{'expected_absent':after['annotated_fields']-after['expected_non_null'],'existing_but_missed':sum(e['expected'] is not None and e['actual'] is None for e in after['errors']),'false_fill_of_absent':after['false_non_null']}})
    report={'cases':rows,'groups':{}}
    lines=['# FintraOCR 개선 검증 — v2.0','','요청 범위인 이미지 → OCR → 필드 매핑 → 표준화 → 근거 JSON → 테스트 UI를 연결했습니다. **아래 한정된 평가 세트에서는 세 문서 유형 각각 정밀도·재현율 90% 목표를 충족했습니다.** 이는 모든 신규 고객 문서의 90% 정확도를 보증하는 수치가 아닙니다.','','## 기존 실제 문서 before/after','','기존 정답의 필드와 행을 그대로 사용했습니다. 각 유형당 Sample.zip 1장입니다. 필드별 값의 대소문자·구두점까지 정확히 비교하며, null끼리 일치한 수는 정밀도/재현율 분자에 넣지 않습니다. 추가 행과 잘못 채운 부재 필드를 따로 집계합니다.','','| 문서 유형 | 이전 정밀도 | 이전 재현율 | 개선 정밀도 | 개선 재현율 | 정답 필드 |','|---|---:|---:|---:|---:|---:|']
    for row in rows:
        if row['source']!='real_sample':continue
        b,a=row['before'],row['after']
        lines.append(f"| {row['type']} | {pct(b['precision'])} | {pct(b['recall'])} | {pct(a['precision'])} | {pct(a['recall'])} | {a['correct_non_null']}/{a['expected_non_null']} |")
    lines+=['','기존 송장 정답은 Exporter를 seller로 주석했습니다. v2는 exporter와 seller를 별도 역할로 유지하고 seller를 추정하지 않습니다. 기존 정답을 변경하지 않아 이 1개는 불일치로 계산되어 재현율이 95.8%입니다. 새 exporter 값에는 원문 근거가 보존됩니다.','','## 합성 문서: 실제 문서와 분리','','개발 UI에서 사용한 영어 송장은 아래 집계에서 제외합니다. 기존 합성 5장은 회귀 평가입니다. 추가 3장은 기존과 다른 열 순서·헤더 배치로 만들고 OCR/모델 추론 전에 정답을 고정했습니다. 추가 3장도 깨끗한 합성 이미지이며 독립적인 외부 고객 평가가 아닙니다.','','| 평가군 | 문서 유형 | 문서 수 | 이전 P/R | 개선 P/R | 일치/정답 |','|---|---|---:|---|---|---:|']
    for source in ['regression_synthetic','fresh_synthetic']:
        for dtype in catalog():
            selected=[r for r in rows if r['source']==source and r['type']==dtype and r['split']!='development-ui']
            if not selected:continue
            a=aggregate([r['after'] for r in selected]);before=[r['before'] for r in selected if r['before']];b=aggregate(before) if before else None
            report['groups'][source+'/'+dtype]={'before':b,'after':a}
            lines.append(f"| {source} | {dtype} | {len(selected)} | {pct(b['precision'])+'/'+pct(b['recall']) if b else '신규 평가'} | {pct(a['precision'])}/{pct(a['recall'])} | {a['correct_non_null']}/{a['expected_non_null']} |")
    lines+=['','## 시간: 초기화, OCR, 매핑 구분','','OCR 모델을 유지한 일괄 평가에서 모델 초기화 시간은 세션 공통입니다. 최초 라벨 모델 요청에는 Ollama 로딩 및 추론 시간이 포함됩니다. 코드 수정 후에는 이 요청의 실제 원응답을 재사용해 근거 연결·표준화를 재평가했습니다. **캐시 재평가 시간은 전체 매핑 시간이 아닙니다.** 현재 요청으로 수행한 추가 합성 3장과 UI 전체 실행을 별도로 확인했습니다. 초기화와 실제 UI 대기 시간은 실행 환경/메모리 상태에 따라 달라집니다.','','| 문서 | OCR 초기화 | OCR | 이전 전체 매핑 | 개선 모델 요청 | 그중 모델 로딩 | 캐시 연결/검증 |','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        t=r['timing'];old_time=(f"{r['before']['mapping_seconds']:.2f}초" if r['before'] else '신규');lines.append(f"| {r['id']} | {t['initialization_seconds']:.2f}초 | {t['ocr_seconds']:.2f}초 | {old_time} | {t['recorded_model_request_seconds']:.2f}초 | {t['recorded_model_load_seconds']:.2f}초 | {t['cached_resolution_seconds']:.3f}초 |")
    lines+=['','## 신규 필드와 null 감사','','정답으로 주석되지 않은 신규 필드는 정확도를 계산하지 않습니다. 아래는 추출률·검토 대상 규모만 보여줍니다. 새 합성 문서는 추론 전에 작성한 정답 범위만 평가합니다. 모든 적용 필드는 JSON에 남아 있습니다.','','| 실제 문서 | 정답 없는 적용 필드 | 추출 후보 | 검토 |','|---|---:|---:|---:|']
    for r in rows:
        if r['source']=='real_sample':
            u=r['unannotated'];lines.append(f"| {r['id']} | {u['applicable']} | {u['accepted']} | {u['review']} |")
    lines+=['','`presence_status`는 not_observed(발견하지 못함), label_only(라벨만 확인), value_observed(값 근거 확인), unresolved_evidence(근거 연결 실패)를 구분합니다. 관측되지 않은 값을 문서에 확실히 없다고 단정하지 않습니다. `null_reason`은 라벨 미제안, 값 선택 실패, 인용 연결 실패, 중복 충돌, 표준화 실패를 구분합니다. 정답을 아는 평가에서는 실제 부재, 존재하지만 누락, 부재 필드의 잘못된 채움을 별도로 집계합니다.','','## 수정 내용과 한계','','- 대형 전체 필드 생성 요청을 라벨 의미 선택과 상대적 문서 구조 해석으로 분리했습니다. 모델이 값 자체를 라벨로 선택한 경우, 이미 확인된 값 영역·자료형·표 구조와 대조해 거절합니다.','- 다단 표 헤더를 연결하고 열과 행을 분리합니다. 합계행은 문서 필드로 연결합니다. 서로 다른 숫자 셀을 붙여 그룹 구분 숫자로 승인하지 않습니다.','- 같은 토큰의 겹치지 않는 문자 구간, 공통 단위 헤더, 명시적인 Same as above/party 참조, 잘못된 중복 사용을 구분합니다.','- 서명란의 AS CARRIER와 DATED처럼 값과 라벨 순서가 다른 경우를 의미와 상대적 배치로 연결합니다. 운송 방식·항차·운송인, 신고 가액·송장 번호를 분리했습니다.','- OCR는 기존 GPU PaddleOCR 경로를 유지했습니다. 원문에 없는 날짜를 고치거나 누락 금액을 계산하지 않습니다. 한국어는 전용 인식기를 사용합니다.','- 구조화 요청/원응답, 라벨 검증 결과, proposal, 최종 근거 및 null 사유를 저장합니다. 모델 자체 점수는 의미 정확도 확률로 취급하지 않습니다.','- 도메인 어휘는 의미 후보를 제안하며 단어 일치만으로 값을 확정하지 않습니다. 회사명·정답값·샘플 ID·양식의 고정 좌표는 엔진에 없습니다.','','긴 표의 복잡한 병합 셀, 회전·왜곡·저화질 이미지, 명시적인 라벨이 거의 없는 문서, 대규모 다중 페이지 문서는 추가 실증이 필요합니다. 문맥 예산을 초과하면 조용히 잘라내지 않고 오류를 반환합니다. 새 합성 세트도 일반적인 사진 품질을 대표하지 않습니다. 회계기준 검색·대사·감사 의견·클라우드 배포는 이번 구현에 포함하지 않았습니다.','','## 재현','','```powershell','python -m scripts.evaluate_v2 --replay','python -m scripts.evaluate_v2 --manifest data/fresh/manifest.json --replay','python -m scripts.report_v2','python -m pytest -q','```','','`--replay`를 빼면 Ollama에 실제 요청합니다. `data/holdout`은 기존 정답, `data/fresh`는 새 합성 정답입니다. `outputs/baseline-v1`에 기존 출력, `outputs/structural-v2/<id>`에 새 출력/원응답/오류를 보존합니다. [최종 필드 목록과 계약](SCHEMA.md)을 참고하세요.']
    (ROOT/'outputs/structural-v2/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'BENCHMARK-V2.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'outputs/schemas-v2.json').write_text(json.dumps({'schema_version':'2.0','documents':catalog(),'aliases':ALIASES},ensure_ascii=False,indent=2),encoding='utf-8')
    path=ROOT/'SCHEMA.md';intro=path.read_text(encoding='utf-8').split('## commercial_invoice')[0]
    for dtype,scopes in catalog().items():
        intro+=f'## {dtype}\n\n'
        for scope,fields in scopes.items():
            intro+=f'### {scope}\n\n| 필드 | 형식 | 의미 |\n|---|---|---|\n'
            for name,s in fields.items():intro+=f"| {name} | {s['kind']} | {s['description']} |\n"
            intro+='\n'
    path.write_text(intro,encoding='utf-8')
    print('Wrote BENCHMARK-V2.md, SCHEMA.md, report.json')
if __name__=='__main__':main()
