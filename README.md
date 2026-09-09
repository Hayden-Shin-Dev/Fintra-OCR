# FintraOCR — GPU OCR + 모델 기반 근거 매핑 + 로컬 검토 UI

최신 상태: [candidate110b 검증 현황](docs/CURRENT_VALIDATION.md). 일반화 인수 기준은 아직 통과하지 않았습니다.

현재 JSON 계약은 **v2.0**(추가 필드 호환)입니다. 기본 경로는 **Qwen3.5 4B 모델 기반 분석**입니다. [전체 샘플 재검증과 한계](INVENTORY-VALIDATION.md)과 [문서별 필드 목록](SCHEMA.md)을 확인하세요. 기존 보고서는 당시 버전의 기록이며 현재 기본 설정과 다릅니다.

상업송장(Commercial Invoice), 포장명세서(Packing List), 선하증권(Bill of Lading)의 이미지에서 문서별 필드를 추출합니다. 회계감사 판단·회계기준 조회·증빙 간 비교는 포함하지 않습니다.

## 지금 사용하기

**`Start-FintraOCR.cmd`를 더블클릭**하세요

1. 이미지 파일을 선택하거나 Sample.zip에서 추출한 샘플을 고릅니다. 여러 파일은 **같은 문서의 페이지 순서**입니다.
2. 기본 OCR 모델은 **PP-OCRv6 Medium**, 장치는 **자동(GPU 우선)**입니다.
3. 기본 **모델 기반 분석**은 Ollama Qwen3.5 4B가 라벨 의미와 원문 근거를 선택합니다. 코드는 문자 구간·상대 배치·자료형을 검증해 값을 재구성합니다. 구조 분석만 옵션은 진단용이며 기본 추출을 대체하지 않습니다.
4. `문서 분석 시작`을 누릅니다. 같은 언어·장치·프로필의 OCR 모델을 재사용하고 임시 GPU 메모리를 반환합니다. 이미지 OCR과 모델 매핑은 매번 다시 실행합니다. 최초 초기화 시간과 재사용 시 시간을 구분해 표시합니다.
5. 필드나 OCR 문장을 누르면 원본 위치가 강조됩니다. 처리 기록 다운로드에는 요청·모델 원응답·라벨 검증·proposal이 들어갑니다. 품목 탭과 원문 탭, JSON 다운로드를 확인하세요.
6. 날짜·숫자 해석을 바꾼 뒤 `매핑 재실행`을 누르면 저장된 OCR를 재사용합니다.

`OCR만 실행`도 지원합니다. 중지 버튼으로 실행 중 작업을 종료할 수 있습니다. 매핑 실패 시 OCR 결과는 남습니다. 결과 URL에 작업 ID가 있으므로 새로고침해도 해당 결과를 다시 볼 수 있습니다.

현재 작업 파일은 `C:\Users\shinm\FintraOCR`, Python 환경은 `C:\Users\shinm\.cache\fintraocr-venv`입니다. 이전 OneDrive 프로젝트 폴더에서는 파일 생성이 실패하여 이 경로에서 작업했습니다.

## 인식 모델과 언어

| UI 선택 | 검출기 | 인식기 |
|---|---|---|
| Medium + 영어/유럽계 언어 | PP-OCRv6_medium_det | PP-OCRv6_medium_rec |
| Medium + 한국어 | PP-OCRv6_medium_det | korean_PP-OCRv5_mobile_rec |
| Mobile + 영어 | PP-OCRv5_mobile_det | en_PP-OCRv5_mobile_rec |
| Mobile + 한국어 | PP-OCRv5_mobile_det | korean_PP-OCRv5_mobile_rec |

PP-OCRv6의 기본 인식기는 한국어를 지원하지 않습니다. 한국어는 고급 설정에서 **한국어 (전용 인식기)**를 선택해야 합니다. 실제 사용 모델명과 전처리 설정은 OCR JSON의 `pages[].preprocessing.models`에 기록됩니다. 자동 언어 감지는 구현하지 않았습니다.

이 PC의 RTX 4050 Laptop GPU(6GB), CUDA 12.6 PaddlePaddle GPU에서 두 OCR 프로필을 실행했습니다. 상세 품질·속도와 매핑 오류는 [검증 보고서](BENCHMARK-V2.md)를 참고하세요. Ollama 7B는 GPU 메모리 일부가 부족해 CPU도 사용할 수 있으며, OCR보다 매핑이 훨씬 오래 걸립니다.

## 설치

Python 3.10 이상. 새 환경에서는 CPU 또는 GPU 런타임 중 **하나만** 설치합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[ocr,ui,test]"
# GPU: NVIDIA 드라이버와 호환되는 공식 Paddle wheel 사용
.\.venv\Scripts\python -m pip install paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
# CPU만 사용하는 별도 환경은 위 GPU 설치 대신:
# .\.venv\Scripts\python -m pip install ".[cpu]"
ollama pull qwen3.5:4b
python launch_ui.py
```

현재 PC에서는 위 설치가 완료되어 있습니다. CUDA/패키지 버전은 `requirements-tested.txt`에 기록합니다. 공식 Windows GPU wheel이 cuDNN 9.5를 의존성으로 설치하면서 빌드 버전 9.9와 다르다는 경고를 냈으나, GPU 설치 점검과 실제 OCR 비교 실행은 완료됐습니다. 클라우드 환경에서는 해당 환경용 런타임을 별도로 검증하세요.

## 파이프라인과 근거 보존

`이미지 → OpenCV 전처리 → PaddleOCR → OCRDocument → 라벨 의미 선택 → 상대적 행·열/값 영역 해석 → 근거 검증 → 표준화 → Result`

- `ocr.py`: 비율 축소, 선택적 CLAHE 명암 보정, text/bbox/confidence 추출. bbox를 원본 이미지 픽셀 좌표로 복원합니다. 회전/왜곡 보정은 현재 하지 않습니다.
- `compact.py`: 전체 OCR 텍스트와 적용 스키마로 모델에 짧은 라벨 선택 요청을 보냅니다. 여러 필드가 섞인 토큰은 필요할 때만 별도 근거 선택을 요청합니다. `grounded.py`: 선택된 라벨을 실제 OCR 문자 구간에 연결합니다. `domain.py`는 검토 가능한 도메인 어휘로 의미 후보를 보완하며 `layout.py`가 행·열·상대적 배치·자료형으로 값 영역을 연결합니다. 어휘 일치만으로 값을 확정하지 않습니다. `semantic.py`의 기존 선택기는 이전 요청 재생과 호환 테스트용으로 남겼습니다.
- 인용이 OCR 문자열과 **정확히 일치**하는지 검사하고 원본 token ID와 문자 범위로 바꿉니다. 유일하게 일치하지 않으면 null/검토로 남깁니다. 반복된 문자열에는 위치 힌트를 사용할 수 있습니다. OCR 오독을 모델이 임의로 고치지 않습니다.
- `mapping.py`: 스키마, 신뢰도, 모호성, span 범위와 중복 사용을 검증합니다. 단위처럼 여러 행에 공통으로 적용되는 동일 필드는 같은 근거를 공유할 수 있습니다.
- `normalize.py`: Decimal 문자열, 날짜, ISO 통화, 단위, 거래처명 공백/Unicode를 정규화합니다. 회사 마스터 매칭이나 번역은 하지 않습니다.
- `schemas.py`: 각 문서의 헤더와 품목 필드를 별도로 정의합니다. 샘플의 회사명·값·고정 좌표·양식별 예외는 엔진에 없습니다.
- 문서 속 명령은 신뢰하지 않는 데이터이며 모델에 도구 실행 권한을 주지 않습니다.

각 필드는 `presence_status`, `null_reason`, `provenance`, `reference_evidence`, `reference_field`, `value`, `raw_text`, `evidence`(원본 OCR text, selected_text, bbox, confidence, token_id, page, start/end), `label_evidence`, `ocr_confidence`, `mapping_score`, `status`, `issues`를 가집니다. bbox는 **부분 문자열이 속한 OCR 토큰 전체**의 위치이며 문자별 박스가 아닙니다. 전체 OCR와 모델 제안도 결과에 보존됩니다.

- `accepted`: 검증을 통과한 추출 후보. 사람이 확정한 값이 아닙니다.
- `missing`: 근거 선택 없음, `value=null`.
- `review`: 불확실하거나 검증 실패, `value=null`, 근거와 사유 보존.
- 분류 근거가 부족한 문서는 `unknown`입니다. 여러 종류가 섞인 파일 묶음은 별도 문서로 나눠야 합니다.

`mapping_score`는 현재 선택기의 근거 연결 점수이며, 모델 정확도나 보정된 확률이 아닙니다. 원문에 존재하는 값을 잘못된 필드에 연결하는 **의미 오류는 여전히 가능합니다**. 근거 검증은 의미적 정확성까지 증명하지 않습니다.

## 표준화 정책

- `1,234.56` / `1.234,56` → `1234.56`. `$125.50` → 숫자 `125.50`; 달러 기호만으로 USD라고 추정하지 않습니다.
- `1,234`, `1.234`처럼 모호한 숫자는 기본 null. 문서의 표기법을 아는 경우에만 소수점 구분자를 명시합니다.
- `03/04/2026`은 기본 null. 날짜 순서 DMY/MDY를 명시하면 해당 규칙으로 해석합니다. 문서 발행일을 다른 날짜로 대신하지 않습니다.
- 합계 계산·수량 추정·금액 환산·누락된 거래처 생성은 하지 않습니다.

## CLI

```powershell
python -m fintraocr ocr invoice.png --profile medium --device gpu:0 --output outputs/invoice.ocr.json
python -m fintraocr map outputs/invoice.ocr.json --model qwen3.5:4b --output outputs/invoice.json
python -m fintraocr run page1.png page2.png --profile medium --device auto --model qwen3.5:4b --output outputs/result.json
python -m fintraocr schemas --output outputs/schemas.json
python -m pytest -q
```

한글 문서에는 `--lang korean`을 사용하세요. OCR 최초 실행 시 공식 모델 파일을 다운로드합니다. `map`에는 OCR 설치가 필요 없으며, 추출 JSON을 재사용할 수 있습니다. 합성 예제의 저장된 Proposal 재생은 `--proposal examples/synthetic.proposal.json`으로 실행합니다. 이는 모델 정확도 검증이 아닙니다.

## 검증 재현

```powershell
python scripts/extract_samples.py C:\Users\shinm\Downloads\Sample.zip
python scripts/run_benchmark.py ocr --profile medium
python scripts/run_benchmark.py ocr --profile mobile
python -m scripts.evaluate_v2 --replay
python -m scripts.evaluate_v2 --manifest data/fresh/manifest.json --replay
python -m scripts.report_v2
```

`data/holdout/manifest.json`은 평가 이미지·정답·분할을 지정합니다. 엔진은 정답 파일을 읽지 않습니다. 새 합성 양식 생성기는 `scripts/build_holdout.py`이며 개발용으로 사용한 UI 문서는 분리 표기합니다. 샘플의 sparse OCR 라벨을 필드 정답으로 취급하지 않습니다. 필드 정답은 별도로 전사했습니다.

`--replay`를 빼면 현재 엔진으로 Ollama에 실제 요청합니다. 이전 `run_benchmark.py map`은 v1 비교용입니다.

평가 중 발생한 오류·null·잘못된 연결을 모두 기록합니다. 작은 합성 세트의 결과는 실제 고객 문서 전체의 정확도 추정치가 아닙니다. 새로운 회사/서식으로 분리한 충분한 외부 문서, 저품질 사진, 회전, 장문/다중 페이지 검증은 추가로 필요합니다.

## UI/API와 클라우드 경계

`web.py`는 FastAPI UI/API와 작업 상태를 담당하며 `worker.py`가 별도 프로세스에서 OCR 또는 매핑을 실행합니다. 이 경계 덕분에 추후 작업 큐와 클라우드 GPU 워커로 교체할 수 있습니다. 현재는 로컬 프로세스이며 클라우드 연결을 구현하거나 배포하지 않았습니다.

서버는 `127.0.0.1:8768`에 바인딩하고, Ollama도 localhost만 허용합니다. 이 MVP 서버에 외부 공개용 인증·사용자 격리·분산 큐는 없습니다. 클라우드 공개 전에는 해당 기능이 필요합니다. 작업은 `data/ui/<job-id>`에 저장되며 자동 삭제하지 않습니다.

공식 참고: [PP-OCRv6 비교](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.en.md), [OCR 언어 지원](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md), [Ollama 구조화 출력](https://docs.ollama.com/capabilities/structured-outputs), [Paddle Windows GPU 설치](https://www.paddlepaddle.org.cn/documentation/docs/zh/install/pip/windows-pip.html).
