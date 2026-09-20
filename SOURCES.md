# 사용한 기술과 출처

## 자체 코드

제작자: 신민철 / 이메일: min.developer.acc@gmail.com

`fintraocr/`, `studio/backend/`, 웹 화면과 실행 도구와 테스트의 자체 코드에는 제작자 주석을 남겼습니다. 아래 외부 코드와 자산은 자체 제작물로 표시하지 않습니다.

## 저장소에 포함된 외부 자산

| 파일 | 원본 출처 | 라이선스 기록 |
|---|---|---|
| `studio/web/assets/three.module.js` | [Three.js r160](https://github.com/mrdoob/three.js/tree/r160) | [MIT 원문](studio/web/assets/three-LICENSE.txt), 원본 헤더 보존 |
| `studio/web/assets/lucide.js` | [Lucide 0.468.0](https://www.npmjs.com/package/lucide/v/0.468.0) | [해당 버전 ISC 원문](studio/web/assets/lucide-LICENSE.txt), 원본 헤더 보존 |
| `fintraocr/assets/qwen35-tokenizer.json` | [Qwen3.5-4B tokenizer](https://huggingface.co/Qwen/Qwen3.5-4B/resolve/main/tokenizer.json) | [Apache-2.0 원문](fintraocr/assets/LICENSE.txt) |


현재 안경 쓴 로봇은 `studio/web/assets/experience.js`의 `character()`에서 Three.js로 그립니다. 사용하지 않는 이전 PNG 이미지는 제거했습니다.

토크나이저 다운로드: 2026-09-09 / SHA-256: `5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`. 모델 가중치가 아닌 문맥 길이 계산용 파일입니다.

## 외부 패키지와 실행 도구

버전 범위는 [pyproject.toml](pyproject.toml)에 기록합니다. 설치형 서비스의 종속 패키지는 별도 런타임에서 관리합니다. 각 배포물의 라이선스는 해당 프로젝트의 원문을 따릅니다.

| 사용처 | 프로젝트 |
|---|---|
| OCR | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [PaddlePaddle](https://github.com/PaddlePaddle/Paddle) |
| 로컬 LLM | [Ollama](https://github.com/ollama/ollama), [Qwen](https://huggingface.co/Qwen) |
| 이미지와 배열 | [OpenCV](https://github.com/opencv/opencv), [NumPy](https://github.com/numpy/numpy), [Pillow](https://github.com/python-pillow/Pillow) |
| 데이터, 국가 코드, 토큰 | [Pydantic](https://github.com/pydantic/pydantic), [pycountry](https://github.com/pycountry/pycountry), [Tokenizers](https://github.com/huggingface/tokenizers) |
| OCR 웹 API | [FastAPI](https://github.com/fastapi/fastapi), [Uvicorn](https://github.com/encode/uvicorn), [python-multipart](https://github.com/Kludex/python-multipart) |
| PDF 출력 | [ReportLab](https://www.reportlab.com/opensource/) |
| 설치형 기준 검색 서비스 | [FAISS](https://github.com/facebookresearch/faiss), [rank_bm25](https://github.com/dorianbrown/rank_bm25) |
| 테스트 | [pytest](https://github.com/pytest-dev/pytest), [HTTPX](https://github.com/encode/httpx) |
| 팀 테스트 터널 | [cloudflared](https://github.com/cloudflare/cloudflared) |
| 웹 폰트 | Google Fonts의 [DM Sans](https://fonts.google.com/specimen/DM+Sans), [Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR) — CSS로 불러오며 폰트 파일은 저장소에 포함하지 않음 |

## 회계기준과 데이터

공식 수집 출발점은 한국회계기준원의 [시행 중 K-IFRS 목록](https://www.kasb.or.kr/front/board/ingAccountingList.do)과 [질의회신 목록](https://www.kasb.or.kr/front/board/List016005.do)입니다. 기준서 원문, 질의회신, 내부 참고 사례는 출처 유형을 구분합니다. 원문과 검색 인덱스는 저장소에 포함하지 않습니다.

`examples/`의 JSON은 자체 합성 예제입니다. 실제 고객 자료나 OCR 정확도 평가 결과가 아닙니다. 업로드 문서, 장부, 개인정보, 계정, 대화, 실행 로그는 공개 대상에서 제외합니다.
