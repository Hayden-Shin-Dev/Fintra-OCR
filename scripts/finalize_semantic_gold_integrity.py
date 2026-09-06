"""Build one final, conservative Gold-integrity gate report.

This report joins only source/Gold audit artifacts. It deliberately excludes
OCR, extractor, and FINAL-HOLDOUT #2 from every Gold decision.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_status(root: Path) -> Counter:
    counts: Counter = Counter()
    for path in root.glob("*/semantic_gold_fields.json"):
        for field in read(path):
            counts[str(field.get("status"))] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accurate-semantic", type=Path, required=True)
    parser.add_argument("--balanced-semantic", type=Path, required=True)
    parser.add_argument("--accurate-conservative", type=Path, required=True)
    parser.add_argument("--balanced-conservative", type=Path, required=True)
    parser.add_argument("--accurate-integrity", type=Path, required=True)
    parser.add_argument("--balanced-integrity", type=Path, required=True)
    parser.add_argument("--accurate-completeness", type=Path, required=True)
    parser.add_argument("--balanced-completeness", type=Path, required=True)
    parser.add_argument("--accurate-reconciliation", type=Path, required=True)
    parser.add_argument("--balanced-reconciliation", type=Path, required=True)
    parser.add_argument("--scale-accurate", type=Path, required=True)
    parser.add_argument("--scale-balanced", type=Path, required=True)
    parser.add_argument("--tl-schema", type=Path, required=True)
    parser.add_argument("--evaluator-accurate", type=Path, required=True)
    parser.add_argument("--evaluator-balanced", type=Path, required=True)
    parser.add_argument("--evaluator-mismatch", type=Path, required=True)
    parser.add_argument("--known-defect-closure", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    accurate_sem = read(args.accurate_semantic)
    balanced_sem = read(args.balanced_semantic)
    accurate_cons = read(args.accurate_conservative / "gold_metrics.json")
    balanced_cons = read(args.balanced_conservative / "gold_metrics.json")
    accurate_integrity = read(args.accurate_integrity)
    balanced_integrity = read(args.balanced_integrity)
    accurate_complete = read(args.accurate_completeness)
    balanced_complete = read(args.balanced_completeness)
    accurate_recon = read(args.accurate_reconciliation)
    balanced_recon = read(args.balanced_reconciliation)
    scale_accurate = read(args.scale_accurate)
    scale_balanced = read(args.scale_balanced)
    tl_schema = read(args.tl_schema)
    evaluator_accurate = read(args.evaluator_accurate)
    evaluator_balanced = read(args.evaluator_balanced)
    mismatch = read(args.evaluator_mismatch)
    known = read(args.known_defect_closure)
    conservative_counts = {
        "accurate75": dict(count_status(args.accurate_conservative)),
        "balanced300": dict(count_status(args.balanced_conservative)),
    }

    gates = {
        "training_tl_provenance_scanned": tl_schema.get("tl_archive_count", 0) > 0 and tl_schema.get("semantic_field_keys_observed") == [],
        "accurate_source_geometry": accurate_integrity.get("status") == "PASS" and accurate_integrity.get("source_payload_token_geometry_equal_cases") == accurate_integrity.get("cases"),
        "balanced_source_geometry": balanced_integrity.get("status") == "PASS" and balanced_integrity.get("source_payload_token_geometry_equal_cases") == balanced_integrity.get("cases"),
        "accurate_scale_invariance": scale_accurate.get("status") == "PASS" and scale_accurate.get("failures") == 0,
        "balanced_scale_invariance": scale_balanced.get("status") == "PASS" and scale_balanced.get("failures") == 0,
        "accurate_mechanical_row_checks": accurate_complete.get("cases_with_noncontiguous_row_indices") == 0 and accurate_complete.get("cases_with_duplicate_source_tokens_across_rows") == 0,
        "balanced_mechanical_row_checks": balanced_complete.get("cases_with_noncontiguous_row_indices") == 0 and balanced_complete.get("cases_with_duplicate_source_tokens_across_rows") == 0,
        "accurate_denominator_reconciliation": accurate_recon.get("transition_reconciliation_status") == "PASS",
        "balanced_denominator_reconciliation": balanced_recon.get("transition_reconciliation_status") == "PASS",
        "historical_accurate_pair_consistency": evaluator_accurate.get("status") == "PASS",
        "historical_balanced_pair_consistency": evaluator_balanced.get("status") == "PASS",
        "all_unverified_available_fields_removed_from_conservative_denominator": all(value.get("available", 0) == 0 for value in conservative_counts.values()),
        "semantic_role_verification": all(
            item.get("semantic_role_integrity") is True
            for item in (accurate_sem, balanced_sem)
        ),
        "original_image_header_layout_semantic_review": all(
            item.get("image_semantic_review_complete") is True
            for item in (accurate_sem, balanced_sem)
        ),
        "new_available_field_semantic_justification": all(
            item.get("semantic_classification", {}).get("CANNOT_VERIFY", 0) == 0
            for item in (accurate_sem, balanced_sem)
        ),
        "true_semantic_row_field_completeness": all(
            item.get("row_cannot_verify") == 0
            for item in (accurate_sem, balanced_sem)
        ),
        "known_defect_semantic_closure": (
            known.get("metrics", {}).get("records", 0) > 0
            and known.get("metrics", {}).get("classifications", {}).get("CANNOT_VERIFY", 0) == 0
        ),
        "historical_625_vs_626_root_cause_closed": mismatch.get("root_cause_status") == "REPRODUCED",
        "final_holdout_2_not_accessed": all(
            item.get("final_holdout_2_accessed") is False
            for item in (
                accurate_sem, balanced_sem, accurate_integrity, balanced_integrity,
                accurate_complete, balanced_complete, accurate_recon, balanced_recon,
                scale_accurate, scale_balanced, tl_schema, evaluator_accurate,
                evaluator_balanced, mismatch, known.get("metrics", {}),
            )
        ),
    }
    gates["gold_freeze_ready"] = all(gates.values())
    summary = {
        "gold_candidate": "semantic-v3.3-candidate9",
        "conservative_gold": {
            "accurate75": {"path": str(args.accurate_conservative), "status_counts": conservative_counts["accurate75"], "changed_fields": accurate_cons.get("changed_fields")},
            "balanced300": {"path": str(args.balanced_conservative), "status_counts": conservative_counts["balanced300"], "changed_fields": balanced_cons.get("changed_fields")},
        },
        "semantic_audit": {
            "accurate75": accurate_sem,
            "balanced300": balanced_sem,
        },
        "known_defect_closure": known.get("metrics", {}),
        "historical_evaluator_mismatch": mismatch,
        "gates": gates,
        "gold_freeze_ready": gates["gold_freeze_ready"],
        "decision": "NO: semantic roles, image/header/layout review, true completeness, and historical 625-side reproduction are not fully evidenced in local artifacts.",
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "gold_integrity_final_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Final Gold integrity gate",
        "",
        "## Scope",
        "",
        "This report completes the available source-only and mechanical Gold checks. It does not modify semantic-v2/v3/v3.1/v3.2/candidate9, does not read OCR or extractor output, and did not access FINAL-HOLDOUT #2.",
        "",
        "## Completed checks",
        "",
        f"- Original Training TL archives scanned: {tl_schema.get('tl_archive_count')} archives / {tl_schema.get('tl_json_entry_count')} JSON entries.",
        "- Original TL provenance: exact manifest-referenced ZIP entries were loaded; source_annotation is treated as downstream serialized data, not as original TL.",
        f"- Accurate75 source geometry: {accurate_integrity.get('source_payload_token_geometry_equal_cases')}/{accurate_integrity.get('cases')}; Balanced300: {balanced_integrity.get('source_payload_token_geometry_equal_cases')}/{balanced_integrity.get('cases')}.",
        f"- Scale invariance: Accurate75 {scale_accurate.get('status')}; Balanced300 {scale_balanced.get('status')}.",
        f"- Denominator transition/reconciliation: Accurate75 {accurate_recon.get('transition_reconciliation_status')}; Balanced300 {balanced_recon.get('transition_reconciliation_status')}.",
        f"- Conservative Gold denominator: Accurate75 {conservative_counts['accurate75']}; Balanced300 {conservative_counts['balanced300']}.",
        "- All fields lacking decisive independent semantic proof were converted to ambiguous_gt in separate conservative roots; original Gold roots remain unchanged.",
        "",
        "## Semantic status",
        "",
        f"- Accurate75 semantic audit: {accurate_sem.get('semantic_classification')}; image files present {accurate_sem.get('images_present')}/{accurate_sem.get('cases')}.",
        f"- Balanced300 semantic audit: {balanced_sem.get('semantic_classification')}; image files present {balanced_sem.get('images_present')}/{balanced_sem.get('cases')}.",
        "- Image file existence/hash/dimensions were checked, but exhaustive pixel-level header/layout semantic sign-off was not performed by a labeled semantic source. A word-level TL file has no semantic field roles.",
        f"- Known-defect closure: {known.get('metrics', {}).get('classifications')}; old/new differences alone are not called verified mapping errors.",
        "",
        "## Historical 625 vs 626",
        "",
        f"- Current preserved pair: {mismatch.get('current_pair_status')}.",
        "- The preserved v3.2 CI count is 626 = 605 exact + 21 normalized-only.",
        f"- Historical 625-side reproduced: {mismatch.get('historical_claim', {}).get('reproduced')}.",
        f"- Closure status: {mismatch.get('root_cause_status')}. The 625-side input/report is absent, so its one-row cause cannot be proven.",
        "",
        "## Final decision",
        "",
        f"GOLD_FREEZE_READY = {'YES' if gates['gold_freeze_ready'] else 'NO'}",
        "",
        "Reason for NO: semantic-role verification, exhaustive image/header/layout review, denominator semantic justification, true semantic row completeness, known-defect semantic closure, and exact historical 625-side reproduction are not all available as independent evidence. This is a conservative integrity result, not an extractor score.",
        "",
        "## Gate JSON",
        "",
        str(args.output_dir / "gold_integrity_final_metrics.json"),
    ]
    (args.output_dir / "GOLD_INTEGRITY_FINAL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"gold_freeze_ready": gates["gold_freeze_ready"], "gates": gates}, ensure_ascii=False))


if __name__ == "__main__":
    main()
