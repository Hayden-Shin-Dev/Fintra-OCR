# FintraOCR 최종 변경·실측 기록 (2026-09-08)

확인된 매핑 회귀를 수정하고 모델 기반 기본 경로를 복원했습니다. 모든 신규 양식 일반화 및 최초 실행 20초 이내는 아직 입증/달성하지 못했습니다. 측정 장비는 RTX 4050 Laptop 6GB, Paddle GPU 3.3.1, PaddleOCR 3.7.0, PP-OCRv6 Medium, Ollama Qwen3.5 4B입니다.

## 수정 내용

- 긴 전체 필드 JSON 생성을 짧은 근거 선택으로 변경했습니다. 모델은 OCR 토큰의 의미를 선택하고 코드는 원문에서 값을 재구성합니다. 모델 사용을 끄는 방식으로 시간을 줄이지 않았습니다.
- 결합된 번호/날짜 및 Shipper/Exporter 라벨, 겹친 bbox, 여러 줄 표 헤더, Qty/Unit 공통 열, 한 토큰 안의 여러 필드와 문자 범위를 처리합니다. 표 핵심 라벨이 누락되면 제한된 추가 모델 요청으로 보완합니다.
- 본문·주소·회사명 자체를 라벨로 쓰는 오류, 옆 열 병합, 짧은 품명 열 이동, 마지막 품목에 합계 행이 섞이는 오류를 수정했습니다. 반복된 상충 값은 review로 남깁니다.
- M/T→t, Cft→ft3 등 단위를 표준화하고 원문을 보존합니다. 사이즈 M을 수량 단위로 사용하지 않습니다. 상품 수량과 포장 개수는 분리합니다.
- 반복 정규식 컴파일과 bbox 계산을 캐시했습니다. 48행 문서의 저장 모델 응답 재생에서 코드 처리만 0.239초였습니다. 이전 cProfile 측정은 계측 비용이 있으므로 운영 지연과 직접 비교하지 않습니다.
- OCR 모델 인스턴스를 재사용합니다. UI와 CLI 모두 compact 모델 엔진에 연결했습니다. 요청/원응답/proposal/검증 사유 및 실패 기록을 보존합니다.

## 기존 평가 기준 before / after

동일 정답 필드 기준입니다. before 품질은 보관된 7B 응답의 재검증 결과이며 7B를 새로 실행한 값이 아닙니다. before 시간은 보관된 실제 모델 호출 시간이고 after는 저장 OCR에 실제 4B 호출+코드 매핑 시간입니다. 양쪽 모두 OCR 시간은 포함하지 않습니다.

| 제공 샘플 유형 (각 1건) | 이전 정밀도/재현율 | 현재 정밀도/재현율 | 이전 모델 호출 | 현재 매핑 |
|---|---|---|---:|---:|
| sample_commercial_invoice | 100.00%/95.83% | 100.00%/95.83% | 223.72초 | 8.86초 |
| sample_packing_list | 100.00%/100.00% | 100.00%/100.00% | 174.12초 | 5.82초 |
| sample_bill_of_lading | 100.00%/100.00% | 100.00%/100.00% | 322.17초 | 11.47초 |

송장 재현율의 미일치 1건은 기존 정답의 seller입니다. 문서의 Exporter를 Seller로 자동 합치지 않는 원칙을 유지하고 정답을 수정해 점수를 높이지 않았습니다.

합성 문서는 총 9건(유형별 3건)이며 유형별 정밀도/재현율 모두 100%입니다. 제공 샘플 및 아래 공개 문서와 별개입니다. 반복 개발에 사용했으므로 독립적인 최종 holdout으로 주장하지 않습니다. null 정답은 정밀도/재현율 분자에 넣지 않습니다.

## 외부 공개 문서

샘플 데이터 외 공개 예시를 먼저 정답화한 뒤 실행하고 발견한 오류를 수정했습니다. 아래 최종 수치는 수정 후 재평가로, 독립된 신규 양식 일반화 증명은 아닙니다. 공개 예시이지 실제 고객 거래가 아닙니다.

| 문서 | 정밀도 | 재현율 | 매핑 시간 |
|---|---:|---:|---:|
| lakay | 100.00% | 100.00% | 14.84초 |
| montana | 92.86% | 92.86% | 5.71초 |
| iccc | 98.35% | 97.55% | 2.17초 |

- [LAKAY 포장명세서](https://www.lakaybusiness.com/docs/sample-packing-list.pdf): 최초 분류 실패로 재현율 0%, 예측 0개라 정밀도 정의 불가 → 현재 100%/100%. 작은 제목, 긴 혼합 토큰, 줄바꿈 헤더와 소수점 근거 연결을 수정했습니다.
- [Montana 선하증권](https://agr.mt.gov/_docs/marketing-docs/sellingtoretail/Bill_of_Lading_Sample.pdf): 최초 33.33%/7.14% → 현재 92.86%/92.86%. 남은 1건은 정답 co.와 OCR Co.의 대소문자 차이이며 엄격 비교 점수를 그대로 유지했습니다.
- [ICCC 가이드의 송장 예시](https://www.iccc.or.id/wp-content/uploads/2020/08/Guide-to-Attending-and-Benefiting-From-International-Trade-Shows-February-2019.pdf): 48개 품목. 남은 차이는 국가 추출 누락, 품명·제품 코드 OCR 오독 및 낮은 신뢰도입니다. OCR에 없는 정답 문자를 생성하지 않았습니다. 첫 모델 실행 원본이 보존되지 않아 신뢰할 수 있는 모델 before 표는 제공하지 않습니다.
- 정답 없는 신규 필드는 score.json의 unannotated_fields/unannotated_items로 추출값만 보고합니다. ICCC 제품 사이즈 48개 추출은 정확도 100%를 뜻하지 않습니다. 문서마다 적용 필드를 줄여 목표를 맞추지 않았습니다.

## UI 실측 및 확인

| 실행 | 전체 시간 | 세부 |
|---|---:|---|
| cold | 35.76초 | `{"ocr": {"initialization_seconds": 19.235000000044238, "ocr_seconds": 7.311999999976251, "model_reused": false, "seconds": 26.54700000002049}, "mapping": {"seconds": 8.514999999955762, "mapping_seconds": 8.5, "model_load_seconds": 0.0730268}}` |
| warm | 11.13초 | `{"ocr": {"initialization_seconds": 0.0, "ocr_seconds": 4.26600000000326, "model_reused": true, "seconds": 4.26600000000326}, "mapping": {"seconds": 6.5310000000172295, "mapping_seconds": 6.5310000000172295, "model_load_seconds": 0.0148917}}` |
| ocr_only_previous_server | 4.03초 | `{"ocr": {"initialization_seconds": 0.0, "ocr_seconds": 3.952999999979511, "model_reused": true, "seconds": 3.952999999979511}}` |
| remap_previous_server | 7.11초 | `{"mapping": {"seconds": 6.610000000044238, "mapping_seconds": 6.594000000040978, "model_load_seconds": 0.0193699}}` |

최종 서버 8768에서 이미지 재업로드 전체 실행, 모든 품목/누락 필드, M/T 원문·토큰 p1t46[0:3] 근거 클릭, 포장 수 67/PKG, 스키마 API 일치, JSON·처리기록 다운로드 HTTP 200과 attachment를 확인했습니다. OCR-only 및 저장 OCR 재매핑은 직전 8767 서버에서 실제 실행했습니다. 단계 실패/종료 처리는 회귀 테스트에 포함됩니다. 사람의 확인 결과를 저장하는 승인 기능은 이번 UI에 구현하지 않았습니다.

최초 전체 실행 약 36초(초기화 19.2초), 재사용 전체 실행 약 11초입니다. 모델 재로딩이 발생한 별도 실험은 34초였고 로드만 17.3초였습니다. 다른 로컬 앱의 Ollama 요청/컨텍스트 변경 및 GPU 경합이 지연을 늘릴 수 있습니다. 20초 SLA 달성에는 상시 준비된 모델 프로세스와 격리된 GPU 운영 환경에서 추가 반복 검증이 필요합니다.

## 스키마와 실행

[SCHEMA.md](SCHEMA.md)에 모든 적용 필드/자료형/의미를 코드에서 생성했습니다. 견적송장 번호, 신용장 개설은행, 제품 사이즈, 송장 품목 포장 수·화인을 추가했습니다. 기존 경로/발행일 별칭을 유지하며 buyer≠consignee, 상품 수량≠포장 수 원칙을 유지합니다.

실제로 실행해 확인한 명령(프로젝트 폴더에서, 현재 Python 경로 사용):

```powershell
& 'C:\Users\shinm\.cache\fintraocr-venv\Scripts\python.exe' -m pytest -q --junitxml=outputs/compact-study/tests.xml
& 'C:\Users\shinm\.cache\fintraocr-venv\Scripts\python.exe' -m fintraocr map data/ui/d7d48e9438cd4830ae2c5eb46f3070e4/ocr.json --model qwen3.5:4b --output outputs/compact-study/cli-final.json
```

123개 테스트 통과(의존성 deprecation 경고 2개). CLI 결과도 실제 모델 호출로 생성했습니다. 재현 평가는 scripts/run_compact_suite.py와 scripts/evaluate_compact.py를 사용합니다. ZIP에는 선택한 OCR/정답/실측 기록이 포함되며 모델 가중치·Python 환경은 별도 설치해야 합니다. UI 실행은 Start-FintraOCR.cmd, 현재 주소는 http://127.0.0.1:8768 입니다.
