"""Summarize frozen benchmark outputs, excluding the UI development case."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def percent(value):
    return "추출 없음" if value is None else f"{value:.1%}"

def main():
    entries = read(ROOT / "data/holdout/manifest.json")
    cases = []
    for entry in entries:
        folder = ROOT / "outputs/benchmark" / entry["id"]
        score = read(folder / "medium.qwen2.5-7b.score.json")
        cases.append({**entry, "score": score})
    groups = {}
    for name, selected in {
        "reserved_all": [c for c in cases if c["split"] != "development-ui"],
        "reserved_synthetic": [c for c in cases if c["split"] != "development-ui" and not c["id"].startswith("sample_")],
        "reserved_sample": [c for c in cases if c["id"].startswith("sample_")],
    }.items():
        totals = {key: sum(c["score"][key] for c in selected) for key in
                  ["expected_non_null", "predicted_non_null", "correct_non_null", "false_non_null", "extra_rows"]}
        totals.update(documents=len(selected), type_correct=sum(c["score"]["type_correct"] for c in selected))
        totals["precision"] = totals["correct_non_null"] / totals["predicted_non_null"] if totals["predicted_non_null"] else None
        totals["recall"] = totals["correct_non_null"] / totals["expected_non_null"]
        groups[name] = totals
    (ROOT / "outputs/benchmark/summary.json").write_text(json.dumps(groups, indent=2), encoding="utf-8")
    lines = ["# 실제 검증 결과 — 2026-09-08", "",
        "현재 OCR과 검토 UI는 실행되지만, **새 양식의 안정적인 필드 매핑이라는 목표는 아직 달성하지 못했습니다.** 근거 문자열 검증만으로 잘못된 의미 연결을 막을 수 없었습니다.", "",
        "## 평가 구성", "",
        "RTX 4050 Laptop 6GB / PaddlePaddle GPU 3.3.1 / PaddleOCR 3.7.0 / Ollama Qwen2.5 7B. 샘플별 회사명·값·고정 좌표를 엔진 규칙으로 추가하지 않았습니다. 개발에 사용한 영어 송장 1장은 집계에서 제외했습니다. 예약 평가 8장은 합성 문서 5장과 Sample.zip 문서 3장입니다. 합성 세트에는 두 레이아웃 계열과 영어·프랑스어·한국어·스페인어가 포함됩니다. Sample 문서는 개발 문서와 양식이 겹칠 수 있어 완전히 새로운 양식이라고 간주하지 않습니다.", "",
        "정답은 추론 전에 저장했습니다. 이번 결과를 본 뒤 프롬프트를 조정한 재평가 수치가 아닙니다. 단, 동일 실행에서 한국어 OCR의 지원 언어 오류를 발견해 전용 인식기로 수정했습니다. 독립적인 외부 블라인드 평가는 아닙니다.", "",
        "## 필드 매핑", "",
        "정밀도 = 정답과 일치한 비어 있지 않은 필드 / 출력한 비어 있지 않은 필드. 재현율 = 일치한 필드 / 정답의 비어 있지 않은 필드. 정답으로 주석한 필드 범위에서 문자열을 정확히 비교하며, 품목은 행 순서대로 비교합니다. 주석하지 않은 필드는 점수에 포함하지 않습니다. 추가 행은 별도 집계하므로 이 정밀도는 전체 출력의 정밀도가 아닙니다. null만 많이 반환해 점수를 높이는 것을 피하려고 null 일치율을 대표 수치로 쓰지 않았습니다.", "",
        "| 평가군 | 문서 | 일치/출력/정답 필드 | 정밀도 | 재현율 |", "|---|---:|---:|---:|---:|"]
    for name, title in [("reserved_all", "예약 평가 전체"), ("reserved_synthetic", "예약 합성"), ("reserved_sample", "Sample.zip")]:
        t = groups[name]
        lines.append(f"| {title} | {t['documents']} | {t['correct_non_null']}/{t['predicted_non_null']}/{t['expected_non_null']} | {percent(t['precision'])} | {percent(t['recall'])} |")
    lines += ["", "| 문서 | 분류 | 정밀도 | 재현율 | 매핑 시간 |", "|---|---|---:|---:|---:|"]
    for c in cases:
        s = c["score"]
        suffix = " (개발용·집계 제외)" if c["split"] == "development-ui" else ""
        lines.append(f"| {c['id']}{suffix} | {'일치' if s['type_correct'] else '실패'} | {percent(s['precision'])} | {percent(s['recall'])} | {s['mapping_seconds']:.1f}초 |")
    lines += ["", "포장명세서 합성 2장은 OCR가 읽은 값이 있었지만 모델이 모든 필드를 null로 반환했습니다. 스페인어 선하증권은 unknown으로 분류됐습니다. Sample 문서에서는 거래처를 이어 붙이거나 운송인을 송하인으로 연결하고, 항목 행을 잘못 대응하는 오류가 있었습니다. 원문에 있는 텍스트도 엉뚱한 필드에 들어갈 수 있습니다. 세부 오류는 각 문서의 `.score.json`에 정답/실제값으로 남겼습니다.", "",
        "## OCR 비교", "", "| 프로필 | 9장 평균 추론 시간 | 합성 6장 영역 CER | Sample 부분 주석 회수 |", "|---|---:|---:|---:|"]
    for profile in ["medium", "mobile"]:
        metrics = [read(ROOT / "outputs/benchmark" / e["id"] / f"{profile}.metrics.json") for e in entries]
        avg = sum(m["inference_seconds"] for m in metrics) / len(metrics)
        quality = [m["quality"] for m in metrics if m.get("quality")]
        errors = sum(m["region_character_errors"] for m in quality)
        chars = sum(m["reference_characters"] for m in quality)
        sparse = [m["sparse_annotation_recall"] for m in metrics if m.get("sparse_annotation_recall")]
        hit, total = sum(m["correct"] for m in sparse), sum(m["total"] for m in sparse)
        lines.append(f"| {profile} | {avg:.2f}초 | {errors}/{chars} ({errors/chars:.1%}) | {hit}/{total} ({hit/total:.2%}) |")
    lines += ["", "추론 시간은 모델 초기화·다운로드를 제외하며 첫 추론의 준비 비용은 포함합니다. UI 전체 대기 시간과 다릅니다. 영역 CER는 렌더러 정답 영역을 맞춘 뒤 대소문자와 공백을 제거해 비교한 값이고, 대응하지 않는 추가 OCR 영역은 벌점에 포함하지 않습니다. Sample 수치는 공간적으로 겹치는 OCR에 부분 주석 문구가 존재하는지 확인한 회수율이며 문서 전체 OCR 정확도가 아닙니다. 작은 선명한 합성 세트에서의 0%를 일반적인 무오류 인식으로 해석하면 안 됩니다.", "",
        "이 세트에서는 Medium의 품질 우위를 확인하지 못했습니다. 품질 우선 기본값으로 Medium을 제공하되 Mobile과 UI에서 비교할 수 있습니다. PP-OCRv6 기본 인식기는 한국어를 지원하지 않아 한국어 설정은 v6 검출기 + 한국어 v5 인식기를 사용합니다. 지원하지 않는 기본 인식기로 한국어를 읽었던 진단 결과는 `outputs/diagnostics`에 별도로 보관했습니다.", "",
        "## 남은 개선", "", "새 양식의 의미 연결 정확도는 현재 부족합니다. 다음 단계는 더 강한 모델을 같은 OCR 입력/근거 검증 경계에 연결하고, 표의 행·열 구조를 명시적으로 표현한 뒤, 별도의 외부 문서 세트로 다시 검증하는 것입니다. 이 평가 세트를 보고 조정한 결과는 회귀 평가로 분류해야 합니다. 실제 사진의 흐림·회전·왜곡, 복잡한 다중 페이지 표, 더 넓은 언어 범위는 아직 검증하지 않았습니다.", "",
        "## 재현 및 원자료", "", "`python scripts/run_benchmark.py report`와 `python scripts/summarize_benchmark.py`로 저장 결과를 집계합니다. OCR/모델 재실행 명령은 README를 참고하세요. `outputs/benchmark/report.json`, `summary.json`, 문서별 `.ocr.json`, `.result.json`, `.score.json`에 입력 근거와 실패를 보존했습니다. `.score.json`의 `engine_sha256`은 평가한 semantic.py 버전입니다."]
    (ROOT / "BENCHMARK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(groups, indent=2))

if __name__ == "__main__":
    main()
