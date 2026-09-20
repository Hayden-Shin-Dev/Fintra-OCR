# 실행 방법

제작자: 신민철 / 이메일: min.developer.acc@gmail.com

## 웹 서비스

`studio/`는 기존 Fintra 설치 환경의 OCR, 거래 비교, 회계기준 서비스를 사용합니다.
`%LOCALAPPDATA%/Fintra/current.json`, 해당 버전의 런타임과 모델과 검색 데이터가 필요합니다.
이 저장소를 clone하는 것만으로 해당 서비스와 데이터가 설치되지는 않습니다.

1. 필요한 경우 `studio/config/ai-runtime.example.json`을 `ai-runtime.json`으로 복사하고 설치된 모델 이름을 지정합니다.
2. `studio` 폴더에서 설치된 Fintra Python으로 `run.py`를 실행합니다.
3. 로컬 웹 화면은 `http://127.0.0.1:8780`에서 엽니다.

팀 서버는 `studio/서버켜기.cmd`, 종료는 `studio/서버끄기.cmd`입니다. 고정 공유 링크는 https://hayden-shin-dev.github.io/Fintra-OCR/ 입니다. 시작 후 창은 닫아도 되며 Windows 로그인 시에도 자동 실행됩니다. PC가 꺼지거나 절전 상태이면 접속할 수 없습니다.

로그인 화면의 회원가입으로 개인 계정을 만들 수 있습니다. 아이디는 영문, 숫자, 밑줄, 하이픈 3~32자, 비밀번호는 10~128자입니다. 계정 DB는 팀 서버의 `studio/team-preview/users.sqlite3`에 저장하고 비밀번호는 scrypt로 해시합니다. 업로드 자료, 검토 기록, 보고서와 대화는 계정별로 접근을 제한합니다. 기존 공용 계정과 그 기록은 유지됩니다. 로컬 단독 실행은 `studio/data/`를 사용합니다. 백업할 때는 서버를 종료하고 해당 데이터 폴더 전체를 복사하세요. 이메일 인증과 비밀번호 찾기는 제공하지 않습니다.

내부 실행 스크립트는 `studio/tools/`에 있습니다. `tools/bin/cloudflared.exe`와 Git Credential Manager의 GitHub 인증이 필요합니다. Cloudflare 주소가 바뀌면 `fintra-live` 브랜치에 접속 주소만 갱신합니다. `gh-pages`는 접속 안내 페이지만 게시하며 문서나 비밀번호는 올리지 않습니다. GitHub 인증이 만료되면 Git 로그인을 갱신해야 합니다.

`FINTRA_ROUTER_MODEL`, `FINTRA_REASONING_MODEL`, `FINTRA_VALIDATOR_MODEL` 환경변수로 챗봇 역할별 모델을 지정할 수 있습니다. 지정하지 않으면 선택한 로컬 모델을 재사용합니다.

## OCR 패키지 단독 실행

Python 3.10 이상과 Ollama가 필요합니다. 저장소 루트에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[ocr,ui,test,cpu]"
ollama pull qwen3.5:4b
.\.venv\Scripts\python launch_ui.py
```

위 명령은 CPU 설치입니다. GPU를 사용할 때는 `cpu` 옵션을 빼고 [PaddlePaddle 공식 설치 안내](https://www.paddlepaddle.org.cn/install/quick)에 맞는 런타임을 설치합니다.

## 합성 예제

`examples/`는 실제 고객 문서가 아닌 오프라인 시연용 데이터입니다.

```powershell
python -m fintraocr map examples/synthetic.ocr.json --proposal examples/synthetic.proposal.json --output outputs/demo.json
```

## 테스트

```powershell
# 저장소 루트: OCR 테스트
python -m pytest -q

# studio 폴더: 웹 서비스 테스트
python -m unittest discover -s tests -p "test_*.py"
node --check web/app.js
```

Studio 통합 테스트 일부는 설치 런타임과 로컬 합성 거래 fixture를 사용합니다. 해당 데이터는 저장소에 포함하지 않으므로 새 PC에서는 별도로 준비해야 합니다. `test_conversational_analysis.py`는 합성 Finding과 통제된 모델 응답으로 대화 흐름을 검증합니다. 실제 모델 평가는 `tools/evaluate_conversation_live.py`로 구분했습니다.

계정, 업로드 문서, 대화 기록, 모델 가중치, 회계기준 코퍼스와 실행 결과는 Git에 올리지 않습니다. 과거 실험 스크립트와 보고서는 이전 커밋에서 확인할 수 있습니다.
