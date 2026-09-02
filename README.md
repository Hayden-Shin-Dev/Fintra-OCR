# Fintra OCR

Fintra의 거래 증빙 OCR 파트 부분 단계별 구현 현황입니다 참고 부탁드립니다 ( 이름은 그냥 제가 임의로 Fintra 라고 정했습니다. Finance + Trace )

## OCR 작업 현황

1. [완료] 데이터셋 기본 구조 확인
2. [완료] 데이터 경로 구성
3. [완료] ZIP 구조 및 파일 구성 분석
4. [완료] 라벨 JSON 구조 상세 분석
5. [완료] 이미지-라벨 pairing 검증
6. [완료] 대상 문서 3종 선별
7. [완료] PaddleOCR baseline 환경 구성
8. [완료] 단일 이미지 baseline 추론
9. [완료] OCR prediction과 정답 라벨 비교
10. [완료] 여러 샘플 baseline 평가
11. [완료] Fine-tuning 필요 여부 결정
12. [미완료] 필요 시 Fine-tuning 및 성능 평가
13. [미완료] 최종 OCR 모델 확정
14. [미완료] OCR 결과에서 필요한 필드 추출
15. [미완료] 필드 값 normalization
16. [미완료] 공통 JSON schema 출력
17. [미완료] Fintra 교차검증 모듈 연결
18. [미완료] 전체 OCR 파이프라인 테스트
19. [미완료] README 최종 정리

현재까지 완료된 사항들입니다. 미완료 부분은 계속 진행 예정입니다.



## OCR 데이터 메모 (아래부터는 데이터 분석 결과입니다 참고해주세요.)

- Training 원천 ZIP: 34개
- Training 라벨 ZIP: 34개
- Validation 원천 ZIP: 34개
- Validation 라벨 ZIP: 34개
- Training 내부 PNG/JSON: 각각 126,326개
- Validation 내부 PNG/JSON: 각각 15,785개
- 현재 확인 범위에서 이미지와 라벨의 basename pairing 누락: 0개

데이터 디렉터리는 다음과 같이 구성되어 있는데 깃허브 레포지토리에는 따로 업로드 하지 않습니다 ( 용량 약 170GB )

```text
OCR/
├─ Training/
│  ├─ 01.원천데이터/
│  └─ 02.라벨링데이터/
└─ Validation/
   ├─ 01.원천데이터/
   └─ 02.라벨링데이터/
```

현재 원천 및 라벨 데이터는 ZIP으로 보관되어 있고 원천 ZIP에는 PNG, 라벨 ZIP에는 JSON이 들어 있습니다.

샘플 라벨 JSON의 top-level 구성은 `Annotation`, `Dataset`, `Images`, `bbox`입니다 `bbox` 항목에는 OCR 텍스트와 좌표 정보가 포함되어 있습니다. 

## ZIP 구조

- Training 원천 archive: 34개
- Training 라벨 archive: 34개
- Validation 원천 archive: 34개
- Validation 라벨 archive: 34개
- Training 원천 내부 파일: `.png` 126,326개
- Training 라벨 내부 파일: `.json` 126,326개
- Validation 원천 내부 파일: `.png` 15,785개
- Validation 라벨 내부 파일: `.json` 15,785개
- archive pairing 누락: 0개

원천 archive 이름의 `TS_` 및 `VS_` prefix는 각각 라벨 archive의 `TL_` 및 `VL_` prefix와 대응합니다. archive 내부 파일은 원천 PNG와 라벨 JSON으로 구성되어있는데, 
용량 문제 관계로 집계 과정에서 압축을 해제하지 않고 파이썬 코드로 다이렉트로 분석 진행했습니다.

## OCR 개발 메모 ( 단계별로 수행하면서 남기는 메모입니다 )

- 4-1 JSON 로딩: `zipfile`로 archive 안의 JSON을 직접 읽는 중. 압축 해제 없음.
- 4-1 schema 샘플: 금융 archive는 `Dataset`, 물류 archive는 `DataSet` 키를 사용함.
- 4-2 metadata: `form_type`, `identifier`, `width`, `height`는 공통으로 읽을 수 있음.
- 4-3 bbox: `data`, `x`, `y`는 공통 필드. 금융 `id`는 정수, 물류 `id`는 UUID 문자열. `data_type`은 optional.
- 4-4 schema target: 물류 3종은 `DataSet` + `Images` 6개 필드 + bbox `data/id/x/y` 구조. 빈 text는 허용.
- 4-5 target schema scan: 물류 3종 JSON 71,973개, schema 오류 0개.
- 4-6 malformed test: 필수 bbox 누락, ID 타입, 좌표 개수, 금융 전용 필드를 오류로 처리함.
- 4-7 target bbox: 7,294,849개. 빈 text 783개.
- Training form_type: 상업송장 20,835개 / 포장명세서 21,910개 / 선하증권 21,232개.
- Validation form_type: 상업송장 2,604개 / 포장명세서 2,738개 / 선하증권 2,654개.
- 5-1 member pairing: PNG/JSON basename 비교 완료. 압축 해제 없음.
- 5-2 target pairing: Training 63,977쌍 / Validation 7,996쌍. 누락·중복 0.
- 6-1 target archive selection: 실제 `form_type`으로 대상 3종 archive만 선택 완료. split별 15개.
- 8-1 single sample selection: 대상 3종별 실제 PNG/JSON basename 일치 샘플 선택 기능 추가. 압축 해제 없음.
- 8-2 image loading: 선택한 PNG를 ZIP에서 bytes로 직접 읽는 기능 추가. 원본 추출 없음.
- 8-3 single inference runner: 이미지 bytes를 RGB array로 바꿔 PaddleOCR raw 결과를 받는 최소 runner 추가. 평가/필드 추출은 아직 하지 않음.
- 8-3 실제 실행: Training 상업송장 1장 추론 성공. `OCRResult` 1개, text 70개, bbox 70개 반환.
- 9-1 prediction parsing: PaddleOCR의 `rec_texts/rec_scores/rec_boxes`를 정답과 비교할 `text + x/y bbox + score`로 정규화. NumPy 결과도 처리.
- 9-2 comparison: IoU 0.5 기준 bbox 1:1 매칭, prediction precision/recall, 매칭 text exact count 계산 추가.
- 9-2 실제 실행: 상업송장 1장에서 prediction 70개 / 정답 80개 / 매칭 27개 / exact text 24개. precision 0.3857, recall 0.3375.
- 10-1 multi-sample evaluation: Training 대상 3종에서 1장씩 평가하는 실행기 추가. 모델 1회 생성 후 문서 유형별 결과 수집.
- 10-1 실제 실행: 상업송장 70/80 box, 매칭 27, exact 24, precision 0.3857, recall 0.3375. 선하증권 97/139, 매칭 22, exact 13, precision 0.2268, recall 0.1583. 포장명세서 63/109, 매칭 18, exact 17, precision 0.2857, recall 0.1651.
- 10-2 multi-sample 확장: 대상 3종별 여러 샘플 선택 및 평가 지원. 기본 1장 동작은 유지하고 `samples_per_form`으로 개수 지정.
- 10-2 실제 실행 메모: 6장 CPU 평가를 시도했으나 처리 시간이 길어 중단. 현재 기록된 실제 수치는 10-1의 3장 결과이며, 다음에 입력 크기/처리 방식 점검.
- 10-3 batch runner: PaddleOCR에 여러 RGB array를 한 번에 전달하는 batch runner 추가. 상업송장 2장 입력에서 결과 2개 반환 확인.
- 10-4 batch evaluation 연결: 실제 다중 샘플 평가도 batch runner를 사용하도록 연결. 테스트용 predictor 주입 경로는 유지.
- 10-4 실제 실행 메모: batch 6장 평가도 CPU 처리 시간이 길어 중단. batch API 자체는 2장 실제 입력에서 결과 2개 반환을 확인했고, 기록 수치는 3장 평가 결과를 사용.
- 11-1 fine-tuning 판단: 3장 합산 prediction 230 / 정답 328 / 매칭 67 / exact 54, precision 0.2913, recall 0.2043. baseline은 낮지만 표본 3장과 CPU 시간 제약이 있어 즉시 fine-tuning은 보류.
- 12-1 학습 준비: 대상 3종 라벨을 PaddleOCR detection line으로 변환하는 순수 변환기 추가. 실제 학습/대량 추출은 아직 시작하지 않음.
- 평가 보완 1-1: Unicode/공백 정규화 exact match와 character-level CER/edit similarity 계산 추가 예정.
- split별 target JSON: Training 63,977개 / Validation 7,996개.
- 전체 사전 scan 142,111개에서는 금융/물류 schema가 섞여 있었음. 이후 Fintra 기준 통계는 물류 3종만 사용.
- Fintra OCR 대상: 상업송장 / 포장명세서 / 선하증권.
- 금융 문서와 물류의 원산지증명서 / 기타는 Fintra 대상에서 제외.
- 물류 metadata 실제값: `DataSet.identifier=IMG_OCR_6_T`, `Images.form_type`로 문서 종류 구분.
- 물류 form_type 실제값: 상업송장 / 포장명세서 / 선하증권 / 원산지증명서 / 기타.
- 7-1 baseline 의존성: CPU 기준 `paddlepaddle==3.2.0`, `paddleocr==3.7.0`로 고정.
- 7-1 환경 기준: Python 3.13 `.venv` 생성 및 설치 완료. 현재 머신에는 NVIDIA GPU가 없어 CPU baseline부터 진행.
- 7-2 import 확인: PaddlePaddle 3.2.0 / PaddleOCR 3.7.0 / PaddleX 3.7.2 정상.



질문 있으면 바로 팀즈 DM 주세요. 계속 업데이트 예정입니다. 


| 문서    | Precision |    Recall | bbox 매칭 | 매칭된 bbox 중 Text Exact |
| ----- | --------: | --------: | ------: | --------------------: |
| 상업송장  |     38.6% |     33.8% |   27/80 |     24/27 = **88.9%** |
| 선하증권  |     22.7% |     15.8% |  22/139 |     13/22 = **59.1%** |
| 포장명세서 |     28.6% |     16.5% |  18/109 |     17/18 = **94.4%** |
| 합계    | **29.1%** | **20.4%** |  67/328 |     54/67 = **80.6%** |


지금 문제 : OCR 성능이 낮다고 확정된 건 아니고 현재 bbox 중심 평가가 실제 OCR 성능을 제대로 보여주는지 아직 검증이 안 됐습니다.
