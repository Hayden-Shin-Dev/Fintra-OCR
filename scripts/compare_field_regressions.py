"""Compare field regression reports on one fixed comparable-field denominator."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def _load(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _items(report: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    return {
        (str(item["document_id"]), str(item["field_name"])): item
        for item in report["field_results"]  # type: ignore[index]
    }


def _metrics(items: dict[tuple[str, str], dict[str, object]], keys: set[tuple[str, str]], section: str) -> dict[str, object]:
    selected = [items[key] for key in sorted(keys) if key in items]
    outcomes = Counter(str(item[section]["outcome"]) for item in selected)
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    by_field: dict[str, Counter[str]] = defaultdict(Counter)
    by_split: dict[str, Counter[str]] = defaultdict(Counter)
    for item in selected:
        outcome = str(item[section]["outcome"])
        by_type[str(item["document_type"])][outcome] += 1
        by_field[str(item["field_name"])][outcome] += 1
        by_split[str(item["split"])][outcome] += 1

    def serialise(value: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
        return {key: dict(counter) for key, counter in sorted(value.items())}

    return {
        "field_count": len(selected),
        "outcomes": dict(outcomes),
        "by_document_type": serialise(by_type),
        "by_field": serialise(by_field),
        "by_split": serialise(by_split),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-aihub", required=True)
    parser.add_argument("--baseline-paddle", required=True)
    parser.add_argument("--after-aihub", required=True)
    parser.add_argument("--after-paddle", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    baseline_aihub = _load(args.baseline_aihub)
    baseline_paddle = _load(args.baseline_paddle)
    after_aihub = _load(args.after_aihub)
    after_paddle = _load(args.after_paddle)
    ai_base = _items(baseline_aihub)
    paddle_base = _items(baseline_paddle)
    ai_after = _items(after_aihub)
    paddle_after = _items(after_paddle)
    comparable = {
        key for key, item in ai_base.items()
        if item.get("oracle_proxy") and key in paddle_base and paddle_base[key].get("oracle_proxy")
    }
    result = {
        "evaluation": "fixed_comparable_field_regression",
        "denominator_definition": "baseline AI-Hub oracle_proxy intersected with baseline Paddle oracle_proxy; unchanged across all comparisons",
        "comparable_field_count": len(comparable),
        "baseline_aihub": _metrics(ai_base, comparable, "improved"),
        "after_aihub": _metrics(ai_after, comparable, "improved"),
        "after_paddle": _metrics(paddle_after, comparable, "improved"),
        "changed_aihub_fields": [
            {
                "document_id": key[0],
                "field": key[1],
                "before": ai_base[key]["improved"],
                "after": ai_after.get(key, {}).get("improved"),
            }
            for key in sorted(comparable)
            if key in ai_after and ai_base[key]["improved"] != ai_after[key]["improved"]
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"comparable_fields": len(comparable), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
