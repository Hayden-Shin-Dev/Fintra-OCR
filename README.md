# Fintra OCR

Fintra의 거래 증빙 OCR 파트를 단계적으로 개발하기 위한 작업 공간입니다.

## OCR 작업 현황

1. [완료] 데이터셋 기본 구조 확인
2. [완료] 데이터 경로 구성
3. [완료] ZIP 구조 및 파일 구성 분석
4. [완료] 라벨 JSON 구조 상세 분석
5. [완료] 이미지-라벨 pairing 검증
6. [완료] 대상 문서 3종 선별
7. [완료] PaddleOCR baseline 환경 구성
8. [미완료] 단일 이미지 baseline 추론
9. [미완료] OCR prediction과 정답 라벨 비교
10. [미완료] 여러 샘플 baseline 평가
11. [미완료] Fine-tuning 필요 여부 결정
12. [미완료] 필요 시 Fine-tuning 및 성능 평가
13. [미완료] 최종 OCR 모델 확정
14. [미완료] OCR 결과에서 필요한 필드 추출
15. [미완료] 필드 값 normalization
16. [미완료] 공통 JSON schema 출력
17. [미완료] Fintra 교차검증 모듈 연결
18. [미완료] 전체 OCR 파이프라인 테스트
19. [미완료] README 최종 정리

단계 상태는 구현, 실행 또는 테스트, 실제 데이터 검증이 모두 끝난 뒤에만 완료로 변경합니다. 다음 단계는 현재 단계가 완료된 뒤 별도로 시작합니다.

## OCR 데이터 메모

- Training 원천 ZIP: 34개
- Training 라벨 ZIP: 34개
- Validation 원천 ZIP: 34개
- Validation 라벨 ZIP: 34개
- Training 내부 PNG/JSON: 각각 126,326개
- Validation 내부 PNG/JSON: 각각 15,785개
- 현재 확인 범위에서 이미지와 라벨의 basename pairing 누락: 0개

데이터 디렉터리는 다음과 같이 구성되어 있습니다.

```text
OCR/
├─ Training/
│  ├─ 01.원천데이터/
│  └─ 02.라벨링데이터/
└─ Validation/
   ├─ 01.원천데이터/
   └─ 02.라벨링데이터/
```

현재 원천 및 라벨 데이터는 ZIP으로 보관되어 있습니다. 원천 ZIP에는 PNG, 라벨 ZIP에는 JSON이 들어 있으며, 분석 과정에서 원본 ZIP을 수정하거나 이동하지 않습니다.

샘플 라벨 JSON의 top-level 구성은 `Annotation`, `Dataset`, `Images`, `bbox`입니다. `bbox` 항목에는 OCR 텍스트와 좌표 정보가 포함되어 있습니다. 상세 schema 검증은 이후 단계에서 수행합니다.

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

원천 archive 이름의 `TS_` 및 `VS_` prefix는 각각 라벨 archive의 `TL_` 및 `VL_` prefix와 대응합니다. archive 내부 파일은 원천 PNG와 라벨 JSON으로 구성되며, 집계 과정에서 압축을 해제하지 않았습니다.

## OCR 개발 메모

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
- split별 target JSON: Training 63,977개 / Validation 7,996개.
- 전체 사전 scan 142,111개에서는 금융/물류 schema가 섞여 있었음. 이후 Fintra 기준 통계는 물류 3종만 사용.
- Fintra OCR 대상: 상업송장 / 포장명세서 / 선하증권.
- 금융 문서와 물류의 원산지증명서 / 기타는 Fintra 대상에서 제외.
- 물류 metadata 실제값: `DataSet.identifier=IMG_OCR_6_T`, `Images.form_type`로 문서 종류 구분.
- 물류 form_type 실제값: 상업송장 / 포장명세서 / 선하증권 / 원산지증명서 / 기타.
- 7-1 baseline 의존성: CPU 기준 `paddlepaddle==3.2.0`, `paddleocr==3.7.0`로 고정.
- 7-1 환경 기준: Python 3.13 `.venv` 생성 및 설치 완료. 현재 머신에는 NVIDIA GPU가 없어 CPU baseline부터 진행.
- 7-2 import 확인: PaddlePaddle 3.2.0 / PaddleOCR 3.7.0 / PaddleX 3.7.2 정상.

## 개발 원칙

- 원천 데이터와 라벨 데이터는 Git에 추가하지 않습니다.
- 독립적으로 설명할 수 있는 기능 또는 검증 단위마다 commit을 만듭니다.
- 각 변경 후 테스트와 실제 데이터 검증을 수행합니다.
- 현재 단계에서는 OCR 모델 설치, 추론, 학습을 진행하지 않습니다.
- Fine-tuning은 pretrained OCR baseline 결과를 확인한 뒤 필요할 때만 결정합니다.

## Commit 규칙

Conventional Commits 형식을 사용합니다.

예시:

```text
docs: add OCR development roadmap
feat: define OCR dataset paths
test: validate OCR dataset paths
```
