# 외부 소프트웨어와 자료의 권리

Fintra 자체 코드의 이용 범위는 [LICENSE](LICENSE)에 따릅니다. 외부 구성요소에는 해당 프로젝트의 라이선스가 우선합니다. 신민철의 제작자 표시는 외부 코드의 저작권자를 대체하지 않습니다.

## 저장소에 포함된 구성요소

| 구성요소 | 버전과 파일 | 권리자와 조건 |
| --- | --- | --- |
| Three.js | r160, `studio/web/assets/three.module.js` | Three.js Authors. [MIT 원문](studio/web/assets/three-LICENSE.txt) 보존 |
| Lucide | 0.468.0, `studio/web/assets/lucide.js` | Lucide Contributors. Feather 유래 부분은 Cole Bemis. [ISC 및 원문 고지](studio/web/assets/lucide-LICENSE.txt) 보존 |
| Qwen 토크나이저 | Qwen3.5-4B, `fintraocr/assets/qwen35-tokenizer.json` | Alibaba Cloud. [Apache-2.0 원문](fintraocr/assets/LICENSE.txt) 보존. 모델 가중치 제외 |

원본 링크와 취득 기록은 [SOURCES.md](SOURCES.md)에 있습니다. 위 파일을 별도 배포물에 포함하는 경우에도 해당 라이선스와 고지를 함께 전달해야 합니다.

## 설치해서 사용하는 종속성

Python 패키지의 선언된 의존성은 [pyproject.toml](pyproject.toml)을 기준으로 합니다. 설치된 버전과 전이 의존성은 환경에 따라 달라집니다. 이 고지는 별도 설치 프로그램 전체에 대한 라이선스 검증을 대신하지 않습니다.

PaddleOCR, PaddlePaddle, Ollama, OpenCV, NumPy, Pillow, Pydantic, pycountry, Tokenizers, FastAPI, Uvicorn, python-multipart, ReportLab, FAISS, rank_bm25, pytest, HTTPX 등의 공식 출처는 [SOURCES.md](SOURCES.md)에 기록했습니다. 실행 환경을 재배포하려면 실제 설치 버전의 LICENSE와 NOTICE, 바이너리 구성요소의 조건까지 확인해야 합니다. pycountry의 데이터와 라이선스도 Fintra 자체 코드의 권리로 묶지 않습니다.

모델의 조건은 선택한 모델과 배포본별로 확인해야 합니다. 토크나이저에 적용된 조건이 모든 모델이나 양자화 배포본에도 동일하다고 가정하지 않습니다.

## 화면 자산

웹 캐릭터는 `studio/web/assets/experience.js`에서 Three.js로 구성합니다. 대표 이미지는 생성형 AI로 제작한 소개 이미지이며 실제 화면 캡처와 구분합니다. 출처는 [SOURCES.md](SOURCES.md)에 남겼습니다.

DM Sans와 Noto Sans KR은 Google Fonts를 통해 불러옵니다. 폰트 파일은 저장소에 포함하지 않습니다. 로컬 배포로 변경할 때는 해당 버전의 라이선스도 함께 포함해야 합니다.

## 회계기준과 데이터

K-IFRS, IFRS 기준서와 KASB 질의회신은 Fintra 소유 자료가 아닙니다. 웹에서 열람할 수 있다는 사실만으로 자동 수집, 인덱싱, 서비스 제공 또는 원문 재배포 권한이 생기지는 않습니다. 이 저장소는 기준서 PDF, HWP, 코퍼스와 검색 인덱스를 배포하지 않습니다.

`studio/backend/kasb_sync.py`의 `rights_for()`는 자동 다운로드, 인덱싱, 서비스 이용 권한의 확인 기록을 요구합니다. 설정값은 권리자의 허락 자체가 아니며 실제 이용 근거를 확보한 운영자만 설정해야 합니다. 신속처리질의는 기준서 원문과 별개인 출처로 표시합니다.

공식 확인 경로: [KASB 시행 중 기준서](https://www.kasb.or.kr/front/board/ingAccountingList.do), [KASB 질의회신](https://www.kasb.or.kr/front/board/List016005.do), [IFRS Foundation 이용조건](https://www.ifrs.org/legal/terms-and-conditions/).
