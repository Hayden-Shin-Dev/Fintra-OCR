> 과거 버전의 검증 기록입니다. 현재 기본 엔진과 검증 결과는 [COMPACT-VALIDATION.md](COMPACT-VALIDATION.md)를 확인하세요.

# 최종 실행 검증 — 2026-09-08

코드 패키지 0.3.0, JSON 계약 2.0입니다. 실제 작업 경로는 C:\Users\shinm\FintraOCR입니다.

- 자동 테스트 **80개 통과**. 기존 63개를 보존하고 구조·중복·동일 당사자 참조·Exporter 역할 분리·스키마/API·실패 종료 테스트를 추가했습니다.
- 기존 실제 문서 3장과 합성 6장의 OCR 캐시 및 실제 Ollama 원응답을 사용해 회귀검증했습니다. 정답 필드와 행을 삭제하지 않았습니다.
- 정답을 먼저 고정한 추가 합성 3장은 Medium GPU OCR와 실제 Ollama 호출로 평가했습니다. 세 유형 모두 정밀도·재현율 100%였습니다. 평가 범위는 BENCHMARK-V2.md에 명시했습니다.
- 기존 실제 문서의 최종 정밀도/재현율: 송장 100%/95.8%, 포장명세서 100%/100%, 선하증권 100%/100%. Exporter를 Seller로 간주했던 기존 정답 1개를 그대로 유지해 송장에서 불일치로 계산했습니다.
- 브라우저에서 전체 실행: 작업 978a83d0781a4604977277184e16991c. 초기화 10.4초, OCR 1.6초, 매핑 64.8초, 전체 약 78초.
- 브라우저에서 저장 OCR 재매핑: 최종 작업 b6fa27dc38ad415e86c455997a370305. 매핑 88.2초. 적용 헤더 필드 38개와 모든 품목 필드가 JSON/UI에 존재하고, 평가 정밀도·재현율 100%임을 API 출력으로 확인했습니다.
- 필드 클릭 bbox 강조, 품목과 OCR 탭, JSON/처리 기록 다운로드, URL 새로고침 복원을 확인했습니다.
- 존재하지 않는 로컬 모델을 지정한 실제 실패 작업 846a608d6564445e89983c975409ae11은 failed로 종료됐습니다. UI는 계속 분석 중으로 남지 않고 모델을 찾을 수 없다는 안내를 표시합니다. OCR와 오류 요청 기록은 보존됩니다.
- OCR 단독 모드도 실제 업로드로 확인했습니다. 작업 921aabc3080f42eea85a73b9f65707cd: 초기화 13.9초, OCR 2.0초, 전체 약 17초.
- CLI의 저장 proposal 재생 실행도 완료했습니다. 결과는 outputs/cli-v2-verified.json입니다.

실제 실행한 명령:

```powershell
python -m scripts.evaluate_v2 --replay
python -m scripts.evaluate_v2 --manifest data/fresh/manifest.json --replay
python -m scripts.report_v2
python -m pytest -q
python -m fintraocr map outputs/benchmark/fresh_invoice/medium.ocr.json --proposal outputs/ui-latest.proposal.json --output outputs/cli-v2-verified.json
```

Ollama 실시간 평가에는 위 evaluate_v2에서 --replay를 빼고 실행했습니다. 새 이미지의 OCR는 PaddleEngine('en','gpu:0','medium')으로 실행했습니다. 일반 사용자는 Start-FintraOCR.cmd를 더블클릭하면 됩니다.

작은 평가 세트의 목표 달성은 모든 신규 실제 양식에 대한 정확도 보장이 아닙니다. 정답이 없는 신규 필드는 정확도를 계산하지 않고 추출/검토 규모로 보고했습니다. 복잡한 병합 셀·저화질·회전·대규모 다중 페이지는 추가 실증 범위이며, 교차검증·회계기준·감사 의견·클라우드 배포는 이번 범위 밖입니다.
