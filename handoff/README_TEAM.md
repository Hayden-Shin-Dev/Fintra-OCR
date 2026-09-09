# Fintra OCR 팀 인수인계 패키지

## 전달 범위와 판정

원본 엔진은 `Hayden-Shin-Dev/Fintra-OCR`의 `86f6668468d1ce65c6249ebfc8dfd3889d670cdd`(candidate110b)입니다. OCR, 매핑 규칙, 모델 프롬프트, 문서 스키마는 변경하지 않았습니다. 이번 추가분은 설치, 호출, 재생 테스트, 입출력 계약, 검증 기록입니다.

**연결 개발용 후보입니다. 모든 양식의 정확도가 검증된 자동 감사 엔진이 아닙니다.** 외부 양식은 재현율이 부족하며, 실제 이미지와 Ollama 모델 추론을 이번 CI에서 재실행하지 않았습니다. `accepted`도 사람이 확인한 정답이 아닙니다.

이 패키지는 이미지 → OCR → 필드 추출 → 표준화까지만 제공합니다. 장부 대사, 거래 묶기, 회계기준 검색, 감사 의견 생성은 팀 서비스가 담당합니다.

## 무엇을 넘기면 되는가

`FintraOCR_Team_Handoff.zip` 전체를 전달합니다. `dist/`의 wheel은 엔진 설치용이고 `fintra_ocr_client.py`는 팀 백엔드 호출용입니다. `source/`는 수정 가능한 원본 엔진입니다. 실험 스크립트, 사용자 PC 경로가 들어간 설치 목록, 원본 고객 문서, 모델 가중치, OCR 캐시, 폰트 파일은 전달하지 않습니다.

`schemas/field_catalog.json`은 실제 코드에서 생성한 문서별 필드 정의입니다. `result.schema.json`, `ocr_document.schema.json`, `proposal.schema.json`은 Pydantic에서 생성한 검증 계약입니다. 예전 72-field JSON이나 다른 저장소의 스키마를 섞지 마세요.

## 1. 독립 환경 설치

Python 3.11을 권장합니다. 이 패키지의 코드와 호출 테스트를 Windows와 Linux의 Python 3.11에서 실행했습니다. OCR/CUDA 런타임 호환성은 별도입니다. 설치는 압축을 푼 폴더에서 실행합니다. 기존 팀 가상환경에 Paddle을 덮어 설치하지 않습니다.

```powershell
# NVIDIA GPU와 호환되는 CUDA 12.6 Paddle 환경용
python setup_handoff.py --runtime gpu-cu126 --pull-model

# GPU 없는 별도 환경에서는 위 명령 대신
python setup_handoff.py --runtime cpu --pull-model
```

Ollama는 운영체제에 먼저 설치하고 로컬 서버를 실행해야 합니다. `--pull-model`은 `qwen3.5:4b` 가중치를 다운로드하므로 인터넷, 저장 공간과 시간이 필요합니다. OCR 가중치도 최초 실제 실행에 다운로드될 수 있습니다. 런타임은 패키지에 포함되지 않으며, 복사만으로 모델까지 생기는 것은 아닙니다.

위 GPU 설치는 원본 저장소에 기록된 CUDA 구성입니다. 다른 드라이버/운영체제에서는 공식 Paddle 호환 버전을 별도 선택하세요. CPU Paddle과 GPU Paddle을 같은 환경에 동시에 설치하지 마세요. `requirements-tested.txt` 원본은 사용자 로컬 editable/wheel 경로가 있어 그대로 설치하면 안 됩니다. 이 패키지는 그 파일을 설치 입력으로 사용하지 않습니다.

인터넷 모델 없이 계약 연결만 확인하려면:

```powershell
python setup_handoff.py --runtime none
.\.fintra-venv\Scripts\python.exe smoke_handoff.py
```

이는 저장된 합성 proposal을 재생하는 테스트이며 OCR/LLM 정확도 테스트가 아닙니다. Linux에서는 `.fintra-venv/bin/python`을 사용합니다.

## 2. 실제 실행 준비와 UI

```powershell
.\.fintra-venv\Scripts\python.exe doctor.py --require-gpu
```

CPU 환경은 `--require-gpu`를 생략합니다. 이 명령은 모델 설치와 런타임 정보만 확인하며 추론 성공을 증명하지 않습니다.

`Start-Review.cmd`를 실행하면 localhost 8768의 기존 검토 UI가 열립니다. Linux에서는:

```bash
FINTRA_DATA_DIR="$PWD/jobs-ui" .fintra-venv/bin/python -m uvicorn fintraocr.web:app --host 127.0.0.1 --port 8768
```

샘플 데이터는 배포하지 않으므로 샘플 목록이 비어 있는 것은 정상입니다. 파일 업로드로 확인하세요. 다른 종류의 문서 3개를 한 문서의 페이지로 함께 업로드하지 마세요.

## 3. 팀 백엔드에서 호출

팀 프로젝트에는 `fintra_ocr_client.py`를 복사하고, OCR 엔진 환경의 Python 경로를 설정합니다. 클라이언트는 표준 라이브러리만 사용하므로 팀 서버의 의존성을 바꾸지 않습니다.

```python
from fintra_ocr_client import FintraOCRClient, OCRConfig

client = FintraOCRClient(
    engine_python=r"D:\tools\FintraOCR_Team_Handoff\.fintra-venv\Scripts\python.exe",
    work_root="./private-ocr-jobs",
    config=OCRConfig(device="gpu:0", model="qwen3.5:4b"),
)

run = client.extract(["invoice.png"], document_type="commercial_invoice")
result = run.result                 # 기존 Result JSON 그대로
print(result["fields"]["invoice_number"])
print(run.ocr_path, run.result_path, run.timings)

# 저장된 OCR로 매핑만 재실행
rerun = client.map_saved(run.ocr_path, document_type="commercial_invoice")
```

`engine_python`만 설치 위치에 맞추면 됩니다. 문서 유형은 `commercial_invoice`, `packing_list`, `bill_of_lading`입니다. 생략하면 엔진이 판단합니다. 지정은 근거 검증을 우회하는 강제 정답이 아니며, 엔진 분류와 다르면 `unknown`으로 반환될 수 있습니다.

한 호출은 한 문서입니다. `image_paths`가 여러 개이면 같은 문서의 페이지 순서입니다. 다른 거래/문서 종류는 별도 호출하고 팀 서비스의 transaction ID와 document ID로 묶으세요. 입력은 PNG/JPEG/BMP/TIFF/WebP 페이지 이미지이며 PDF 렌더링은 팀 서비스에서 수행합니다.

호출은 동기식입니다. FastAPI 비동기 라우트에서는 `await asyncio.to_thread(client.extract, paths)`처럼 워커에서 실행하거나 팀 작업 큐로 넘기세요. GPU마다 공용 클라이언트 인스턴스 하나를 사용하고, 다중 서버 프로세스에서는 별도 단일 GPU 큐가 필요합니다.

어댑터는 OCR과 매핑을 별도 자식 프로세스로 실행해 OCR 자식이 종료된 뒤 매핑합니다. 따라서 기존 warm UI보다 초기화 비용이 커질 수 있습니다. 다른 UI/Ollama 작업이 GPU 메모리를 점유하면 부족할 수 있으므로 동시 실행을 피하세요. timeout은 Python 자식 작업을 종료하지만 이미 Ollama 서버가 접수한 추론까지 취소한다고 보장하지 않습니다.

## 출력 계약

`schema_version`은 `2.0`입니다. `fields`는 문서 헤더, `items[]`는 실제 품목 행입니다. 금액과 수량은 부동소수점이 아니라 정규화된 문자열입니다. 계산 시 `Decimal`을 사용하세요. 날짜는 명확한 경우에만 표준화합니다. 통화와 단위는 별도 필드입니다.

각 필드에는 `value`, `raw_text`, `evidence`, `label_evidence`, `ocr_confidence`, `mapping_score`, `status`, `issues`, `null_reason`, `presence_status`, `provenance`, `reference_evidence`, `reference_field`가 있습니다. bbox는 원본 이미지 좌표의 OCR 토큰 전체 영역입니다. 선택된 문자 구간과 글자별 bbox를 혼동하지 마세요.

`accepted`는 엔진 검증을 통과한 후보입니다. `missing`은 미관찰/미선택, `review`는 모호성/검증 문제입니다. 마지막 둘은 `value=null`입니다. null을 0이나 빈 문자열로 치환하지 마세요. `mapping_score`는 정답 확률이 아닙니다.

문서의 필드 누락은 항상 `human_review_required` 전체 issue를 발생시키는 것이 아닙니다. 팀의 각 대사 규칙은 필요한 필드가 모두 `accepted`이고 단위/통화/범위가 비교 가능한지 별도로 확인해야 합니다. 필요한 값이 없으면 판정 불가로 처리해야 하며 정상 거래라고 처리하면 안 됩니다.

`seller`와 `exporter`, `buyer`와 `consignee`는 서로 다른 역할입니다. 같은 이름이 등장해도 무조건 동치로 합치지 않습니다. `total_packages`는 품목 수량이 아닙니다. `issue_date`, `departure_date`, `on_board_date`, `shipment_date`를 구분하세요. 문서 번호는 타 문서의 참조로도 나타납니다.

기존 호환 alias는 `schemas/compatibility_aliases.json`에 기록합니다. CI의 `invoice_date`는 해당 문서 `issue_date`의 호환 이름이며, 다른 문서의 `invoice_date`는 참조 송장의 날짜일 수 있습니다.

실패는 `FintraOCRError` 예외로 전달됩니다. OCR이 완료된 뒤 매핑이 실패하면 작업 폴더의 `ocr.json`은 남습니다. 로그와 실패 사유는 로컬 작업 폴더에서 확인하고, 원문이 담긴 로그를 공개 API 응답으로 반환하지 마세요.

## 보안과 운영 경계

공급한 UI/API는 로컬 검토용입니다. 외부 공개용 인증, 사용자 격리, 문서 보관/삭제 정책, 분산 큐는 포함하지 않습니다. 사용자 문서, OCR, 모델 요청/응답은 작업 폴더에 남습니다. 접근 제한과 보관 정책은 팀 서비스가 담당합니다. 모델 요청은 로컬 Ollama로만 보냅니다. 모델 최초 다운로드는 문서 업로드와 다른 네트워크 동작입니다.

## 검증과 알려진 제한

`validation/`은 이번 GitHub Actions 테스트 결과이며, `SOURCE_VALIDATION.md`는 원본 저장소의 성능 보고서입니다. 둘을 혼동하지 마세요. 원본 보고서의 development/batch20/batch30은 저장된 모델 응답 replay 평가입니다. 기존 계열에서는 높은 수치이나 새 양식의 보증이 아닙니다. 외부 packing 예시의 recall 57.14%, invoice 예시 85.71%, B/L 예시 77.78%가 보고되어 있습니다. 해당 문서들도 실패 분석에 사용됐습니다.

현재 엔진은 LLM이 주로 라벨 의미를 선택하고 Python의 도메인 어휘와 상대 배치 규칙이 값을 연결하는 혼합 방식입니다. `domain.py`의 어휘, `layout.py`의 기하 임계값, 라벨 후보 제한이 남아 있으므로 완전한 양식/언어 일반화를 주장하지 않습니다. 모든 수동 사전이 정답 하드코딩인 것은 아니며 도메인 규칙과 특정 샘플 정답 규칙을 구분해야 합니다.

CI에서 새로 확인한 것은 코드 테스트, API 스키마, 계약 재생, 오류 처리, Windows/Linux 실행 호환, wheel 설치와 패키징입니다. 실제 GPU, 실제 Ollama 모델 응답, 실제 신규 문서 정확도, 전체 서비스 연동은 별도 검증이 필요합니다. 테스트 통과를 결함 0개나 정확도 100%로 해석하지 마세요.

## 팀 인수 체크

독립 환경 설치 → offline smoke → doctor → 실제 CI/PL/B/L 각각 한 문서 실행 → 팀 API에서 JSON 저장과 근거 클릭 → 필수값 null일 때 판정 불가 처리 확인 순서로 진행하세요. 기존 서버의 OCR 구현을 덮어쓰기 전에 이 패키지 호출을 별도 경로에서 확인하세요.
