# Fintra Studio

제작자: 신민철 · 이메일: min.developer.acc@gmail.com

현재 웹·거래 검토·챗봇 서비스의 자체 작성 코드입니다. 저장소 루트의 `fintraocr/` OCR 패키지를 대체하지 않습니다.

## 실행 환경

이 서비스는 Windows의 기존 Fintra 설치 런타임 및 OCR·회계기준 서비스를 사용합니다. 코드만 clone한 새 PC에서 자동으로 모든 모델과 데이터가 설치되는 구성은 아닙니다. `%LOCALAPPDATA%/Fintra/current.json`에 지정된 설치 버전과 런타임, 기존 분석 서비스가 필요합니다.

- 로컬 실행: `Start-Fintra.cmd`
- 팀 테스트 URL: `Start-Team-Preview.cmd` 실행 후 로컬에 생성되는 `team-preview/access.txt`에서 URL과 계정을 확인
- 팀 테스트 중지: `Stop-Team-Preview.cmd`

모델, 토크나이저, 기준서 코퍼스, 계정, 비밀번호, 업로드 문서, 채팅 기록, 로그 및 실행 결과는 이 폴더에 포함하지 않습니다. 기준서 자료의 이용 권한은 별도로 확인해야 합니다.

## 검증

Python 테스트: `python -m unittest discover -s tests -p "test_*.py"`

일부 통합 테스트는 설치 런타임과 로컬 합성 거래 fixture를 참조합니다. 따라서 새 checkout에서 해당 자료 없이 모든 테스트가 실행되는 것은 아닙니다. 테스트가 필요한 자료 경로는 각 테스트 파일에서 확인할 수 있습니다.

JavaScript 구문 확인: `node --check web/app.js`

## 출처

자체 코드의 제작자 표기와 외부 자산 구분은 상위 `AUTHORS.md`를 참고하세요. 외부 라이브러리의 원래 라이선스는 유지합니다.
