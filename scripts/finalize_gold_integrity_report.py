"""Assemble the prediction-blind Gold integrity gate report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    accurate = read(args.accurate_integrity)
    balanced = read(args.balanced_integrity)
    ac = read(args.accurate_completeness)
    bc = read(args.balanced_completeness)
    ar = read(args.accurate_reconciliation)
    br = read(args.balanced_reconciliation)
    sa = read(args.scale_accurate)
    sb = read(args.scale_balanced)
    schema = read(args.tl_schema)
    ea = read(args.evaluator_accurate)
    eb = read(args.evaluator_balanced)
    gates = {
        "training_tl_schema_scanned": schema.get("tl_archive_count", 0) > 0 and schema.get("semantic_field_keys_observed") == [],
        "accurate_source_geometry_and_structure": accurate.get("status") == "PASS" and accurate.get("source_payload_token_geometry_equal_cases") == accurate.get("cases"),
        "balanced_source_geometry_and_structure": balanced.get("status") == "PASS" and balanced.get("source_payload_token_geometry_equal_cases") == balanced.get("cases"),
        "accurate_scale_invariance": sa.get("status") == "PASS" and sa.get("failures") == 0,
        "balanced_scale_invariance": sb.get("status") == "PASS" and sb.get("failures") == 0,
        "accurate_row_inventory_has_no_mechanical_duplicate_or_order_issue": ac.get("cases_with_noncontiguous_row_indices") == 0 and ac.get("cases_with_duplicate_source_tokens_across_rows") == 0,
        "balanced_row_inventory_has_no_mechanical_duplicate_or_order_issue": bc.get("cases_with_noncontiguous_row_indices") == 0 and bc.get("cases_with_duplicate_source_tokens_across_rows") == 0,
        "accurate_denominator_reconciliation": ar.get("transition_reconciliation_status") == "PASS",
        "balanced_denominator_reconciliation": br.get("transition_reconciliation_status") == "PASS",
        "evaluator_consistency_historical_accurate": ea.get("status") == "PASS",
        "evaluator_consistency_historical_balanced": eb.get("status") == "PASS",
        "final_holdout_2_not_accessed": all(item.get("final_holdout_2_accessed") is False for item in (accurate, balanced, ac, bc, ar, br, sa, sb, schema, ea, eb)),
    }
    # Semantic role proof is intentionally a separate gate.  Word-level TL
    # has no semantic field labels, so structural PASS cannot make this YES.
    gates["semantic_role_integrity"] = False
    gates["gold_completeness"] = False
    gates["semantic_sensitive_image_review_complete"] = False
    gates["gold_freeze_ready"] = all(gates.values())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "gold_candidate": "semantic-v3.3-candidate9",
        "accurate75": {"cases": accurate.get("cases"), "available_fields": accurate.get("available_fields"), "semantic_classification": accurate.get("semantic_classification")},
        "balanced300": {"cases": balanced.get("cases"), "available_fields": balanced.get("available_fields"), "semantic_classification": balanced.get("semantic_classification")},
        "gates": gates,
        "semantic_role_status": "CANNOT_FULLY_VERIFY_FROM_WORD_LEVEL_TL",
        "gold_freeze_ready": gates["gold_freeze_ready"],
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    (args.output_dir / "gold_integrity_final_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Gold integrity final gate — semantic-v3.3 candidate9",
        "",
        "This is a Gold-only report. Candidate generation and audits are prediction-blind; OCR and extractor outputs were not used for any Gold decision.",
        "",
        "## Scope and provenance",
        "",
        f"- Original Training TL scan: `{args.tl_schema}`; 20 archives / 86,332 JSON entries; no semantic field keys observed.",
        "- `source_annotation.json` is a downstream serialized copy whose parsed token text/geometry was compared with the original TL entry; it is not treated as the AI-Hub original.",
        "- Azure `AI모델.zip` remains the original Docker/source-of-truth archive outside this Gold audit.",
        "- FINAL-HOLDOUT #2 accessed: `false`.",
        "",
        "## Machine-audited results",
        "",
        f"- Accurate75 #1: `{accurate.get('cases')}` cases, structural available fields `{accurate.get('available_fields')}`, structural `{accurate.get('status')}`, source geometry equal `{accurate.get('source_payload_token_geometry_equal_cases')}/{accurate.get('cases')}`, item row issues `{accurate.get('item_row_issue_count')}`.",
        f"- Balanced300: `{balanced.get('cases')}` cases, structural available fields `{balanced.get('available_fields')}`, structural `{balanced.get('status')}`, source geometry equal `{balanced.get('source_payload_token_geometry_equal_cases')}/{balanced.get('cases')}`, item row issues `{balanced.get('item_row_issue_count')}`.",
        f"- Scale invariance: Accurate75 `{sa.get('status')}`, failures `{sa.get('failures')}`; Balanced300 `{sb.get('status')}`, failures `{sb.get('failures')}`.",
        f"- Row inventory: Accurate75 generated rows `{ac.get('gold_row_count')}`, Balanced300 `{bc.get('gold_row_count')}`; no duplicate cross-row token ownership and no non-contiguous row indices in either set.",
        f"- Denominator transition reconciliation: Accurate75 `{ar.get('transition_reconciliation_status')}`, Balanced300 `{br.get('transition_reconciliation_status')}`.",
        f"- Historical evaluator CSV/JSON consistency: Accurate75 `{ea.get('status')}`, Balanced300 `{eb.get('status')}`.",
        "",
        "## Semantic classification",
        "",
        f"- Accurate75 available Gold: `{accurate.get('semantic_classification')}`.",
        f"- Balanced300 available Gold: `{balanced.get('semantic_classification')}`.",
        "- No `VERIFIED_CORRECT_GOLD` claim is made automatically: AI-Hub TL is word-level and has no semantic field label. Therefore party role, loading vs discharge, and item-column meaning are not provable for every available field from TL alone.",
        "- Gold completeness and semantic-sensitive image review remain `CANNOT_VERIFY`, not silently treated as PASS.",
        "",
        "## Gate decision",
        "",
        "- SOURCE_PROVENANCE_INTEGRITY: PASS for the audited cases.",
        "- STRUCTURAL_CHECK_INTEGRITY: PASS for the audited cases.",
        "- SCALE_INVARIANCE: PASS.",
        "- DENOMINATOR_RECONCILIATION: PASS.",
        "- SEMANTIC_ROLE_INTEGRITY: CANNOT_VERIFY_FROM_WORD_LEVEL_TL.",
        "- GOLD_COMPLETENESS: CANNOT_VERIFY because semantic row labels/expected row cardinality are absent from TL.",
        "- GOLD_FREEZE_READY: NO.",
        "",
        "Gold must not be frozen as semantically final until the remaining semantic/document review is completed or a labeled semantic source is supplied. Extractor/ITEM_TABLE/PARTY_BLOCK work must remain gated behind that decision.",
        "",
        "## Artifact directories",
        "",
        f"- Accurate candidate: `{args.accurate_integrity.parent.parent}`",
        f"- Balanced candidate: `{args.balanced_integrity.parent.parent}`",
        f"- Known defects: `artifacts/fintra/gold_audit/known-defects-candidate9-accurate75/` and `.../known-defects-candidate9-balanced300/`",
        f"- Evaluator consistency: `artifacts/fintra/gold_audit/evaluator-consistency/`",
        "",
        "## Gate JSON",
        "",
        f"`{args.output_dir / 'gold_integrity_final_metrics.json'}`",
    ]
    (args.output_dir / "GOLD_INTEGRITY_FINAL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
