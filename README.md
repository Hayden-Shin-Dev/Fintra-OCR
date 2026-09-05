# Fintra OCR V2

현재 `restart/clean-v2` 개발 브랜치에서 AI-Hub 물류 OCR 원본을 우선 검증한다. 대상은 Commercial Invoice, Packing List, Bill of Lading이며 금융 OCR, 대체 OCR 프레임워크, field extraction, API, frontend는 원본 OCR pipeline 검증 이후로 미룬다.

## 조사 기준

### Sample

루트의 `sample.zip`은 Git에 추가하지 않는 읽기 전용 원본 입력이다.

- PNG 31개, GT JSON 31개, 1:1 pair 31개
- Commercial Invoice 15개 / Packing List 11개 / B/L 5개
- GT text annotation 3,051개
- JSON root: `Annotation`, `DataSet`, `Images`, `bbox`
- `bbox` 항목: `data`, `id`, `x[4]`, `y[4]`
- pairing key: PNG filename stem = JSON filename stem = `Images.identifier`
- 빈 text annotation 1개가 확인됨

정량 평가는 눈에 보이는 모든 문자가 아니라 GT에 annotation된 text region을 기준으로 detection, recognition, end-to-end metric을 분리해 계산한다.

### AI-Hub package

`C:\Users\shinm\Downloads\OCR 데이터(금융 및 물류)\AI모델.zip`의 중앙 목록만 읽었다. 전체 압축 해제나 Docker load는 수행하지 않았다.

- 물류 Docker artifact: `05. 도커이미지/cognet9-aihub-train-release.tar`
- TAR uncompressed size: 129,864,044,032 bytes (약 129.86 GB)
- outer ZIP compressed size: 92,588,708,861 bytes
- outer ZIP compression method: Deflate64 (method 9)
- source archive: `01. AI모델 소스코드/source_code.zip` (27,670,353 bytes)

원본 source에서 확인된 물류 pipeline은 `run_transit.sh` 기준으로 detector inference를 `new_detection/tools/dist_test.sh`로 수행하고, 결과 PKL의 `boundary_result`에서 score 0.2 초과 polygon을 읽어 Shapely bounds 기반 crop을 만든 후 `detection_model.py`가 ViTSTR recognizer를 실행하는 흐름이다. recognizer 실행 옵션은 `vitstr_small_patch16_224`, 224x224, Transformer이며 결과는 이미지별 `x1,...,y4,text` TXT이다. dictionary와 checkpoint의 실제 Docker 위치, release config 및 Docker manifest는 artifact가 100GB를 초과하고 Deflate64 내부 stream을 현재 기본 도구로 해독할 수 있어 아직 확정하지 않았다.

source package의 요구사항에는 `mmcv-full==1.4.3`, `mmdet==2.20.0`, MMOCR git commit `5582e17...`, `timm==0.5.4`, `torch==1.7.1`이 기록되어 있고, source Dockerfile은 `pytorch/pytorch:1.6.0-cuda10.1-cudnn7-devel`을 기반으로 한다. 이는 release image 내부 환경을 직접 검증한 값이 아니므로 확정 환경 정보로 사용하지 않는다.

## Baseline 재현 판정

이번 baseline을 `Dockerfile`과 `requirements.txt`만으로 만든 소형 환경에서 실행하는 것은 현재 동일성 보장 불가로 판정한다. Dockerfile은 기본 이미지와 OS 패키지만 선언하고, requirements에는 Dockerfile의 PyTorch 1.6.0과 충돌하는 `torch==1.7.1` 및 `/tmp/build` 기반 conda artifact가 포함되어 있다. 또한 `run_transit.sh`가 가리키는 release config, recognizer checkpoint, `unidocs_dict_transit2.txt`는 source archive 목록에서 확인되지 않았다.

따라서 reference baseline은 원본 Docker artifact와 그 안의 release asset을 사용해야 한다. 소형 재현 환경은 exact baseline 결과를 대체하지 않으며, 원본 결과를 확보한 뒤 별도 비교 검증할 때만 사용한다.

평가 대상은 `sample.zip` 31 pair의 GT annotation 3,051개다. Detection은 region/IoU/precision/recall, Recognition은 matched region의 exact match/CER, End-to-End는 위치 검출과 exact text를 모두 만족한 GT 비율로 분리 집계한다. 현재는 Docker load, GPU inference, 성능 평가를 실행하지 않았다.

## 다음 단계

원본 Docker artifact를 처리할 별도 저장공간과 Deflate64 해독/검사 경로를 먼저 확보한다. manifest, image/tag, entrypoint, release config와 checkpoint 경로를 검증한 뒤에만 사용자가 직접 `docker load` 및 GPU smoke test를 실행한다.
