"""Evaluate deterministic cross-document validation rules on explicit fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fintra.domain.schema import (
    BillOfLading,
    CommercialInvoice,
    DocumentMetadata,
    LedgerTransaction,
    LineItem,
    PackingList,
    ambiguous,
    evidence,
    missing,
)
from fintra.validation.engine import validate_transaction


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    rule_id: str
    expected_status: str
    build: Callable[[], tuple[LedgerTransaction, CommercialInvoice | None, PackingList | None, BillOfLading | None]]


def _metadata(document_id: str, document_type: str) -> DocumentMetadata:
    return DocumentMetadata(document_id, document_type, source_file=f"{document_id}.json", extraction_status="extracted")


def _invoice(*, total="100.00", buyer="BUYER LTD", seller="SELLER LTD", quantity="10", ambiguous_total=False, missing_total=False, quantity_state="extracted") -> CommercialInvoice:
    total_field = ambiguous(source_text="two total amounts") if ambiguous_total else missing() if missing_total else evidence(total, source_text=f"Total {total}")
    quantity_field = ambiguous(source_text="multiple quantities") if quantity_state == "ambiguous" else missing() if quantity_state == "missing" else evidence(quantity, source_text=f"Qty {quantity}")
    return CommercialInvoice(
        metadata=_metadata("invoice-1", "Commercial Invoice"),
        total_amount=total_field,
        buyer=evidence(buyer, source_text=buyer),
        seller=evidence(seller, source_text=seller),
        items=[LineItem(quantity=quantity_field)],
    )


def _packing(*, quantity="10", gross="50", unit="KG", packages="2", consignee="BUYER LTD", quantity_state="extracted", gross_state="extracted", package_state="extracted") -> PackingList:
    def field(value, state, label):
        return ambiguous(source_text=f"multiple {label}s") if state == "ambiguous" else missing() if state == "missing" else evidence(value, source_text=f"{label} {value}")
    return PackingList(
        metadata=_metadata("packing-1", "Packing List"),
        consignee=evidence(consignee, source_text=consignee),
        items=[LineItem(quantity=field(quantity, quantity_state, "quantity"))],
        gross_weight=field(gross, gross_state, "gross weight"),
        weight_unit=evidence(unit, source_text=unit),
        package_count=field(packages, package_state, "package count"),
    )


def _bl(*, gross="50", unit="KG", packages="2", consignee="BUYER LTD", shipment_date="2024-01-02", gross_state="extracted", package_state="extracted", shipment_state="extracted", consignee_state="extracted", ambiguous_consignee=False) -> BillOfLading:
    def field(value, state, label):
        return ambiguous(source_text=f"multiple {label}s") if state == "ambiguous" else missing() if state == "missing" else evidence(value, source_text=f"{label} {value}")
    return BillOfLading(
        metadata=_metadata("bl-1", "B/L"),
        consignee=ambiguous(source_text="two consignee blocks") if ambiguous_consignee else field(consignee, consignee_state, "consignee"),
        gross_weight=field(gross, gross_state, "gross weight"),
        weight_unit=evidence(unit, source_text=unit),
        package_count=field(packages, package_state, "package count"),
        shipment_date=field(shipment_date, shipment_state, "shipment date"),
    )


def _ledger(*, amount="100.00", counterparty="BUYER LTD", date="2024-01-02", amount_state="extracted", counterparty_state="extracted", date_state="extracted") -> LedgerTransaction:
    def field(value, state, label):
        return ambiguous(source_text=f"two {label}s") if state == "ambiguous" else missing() if state == "missing" else evidence(value, source_text=f"{label} {value}")
    return LedgerTransaction(
        transaction_id="ledger-1",
        amount=field(amount, amount_state, "amount"),
        counterparty=field(counterparty, counterparty_state, "counterparty"),
        recognition_date=field(date, date_state, "recognition date"),
    )


def _scenario(rule_id: str, suffix: str, expected: str, build) -> Scenario:
    return Scenario(f"{rule_id.lower()}-{suffix}", rule_id, expected, build)


def scenarios() -> list[Scenario]:
    return [
        _scenario("LEDGER-INVOICE-AMOUNT", "match", "match", lambda: (_ledger(), _invoice(), None, None)),
        _scenario("LEDGER-INVOICE-AMOUNT", "mismatch", "mismatch", lambda: (_ledger(amount="101.00"), _invoice(), None, None)),
        _scenario("LEDGER-INVOICE-AMOUNT", "insufficient", "insufficient_evidence", lambda: (_ledger(amount_state="missing"), _invoice(), None, None)),
        _scenario("LEDGER-INVOICE-COUNTERPARTY", "match", "match", lambda: (_ledger(), _invoice(), None, None)),
        _scenario("LEDGER-INVOICE-COUNTERPARTY", "mismatch", "mismatch", lambda: (_ledger(counterparty="OTHER LTD"), _invoice(), None, None)),
        _scenario("LEDGER-INVOICE-COUNTERPARTY", "review", "review_required", lambda: (_ledger(counterparty_state="ambiguous"), _invoice(), None, None)),
        _scenario("LEDGER-INVOICE-COUNTERPARTY", "insufficient", "insufficient_evidence", lambda: (_ledger(counterparty_state="missing"), _invoice(), None, None)),
        _scenario("INVOICE-PACKING-QUANTITY", "match", "match", lambda: (_ledger(), _invoice(), _packing(), None)),
        _scenario("INVOICE-PACKING-QUANTITY", "mismatch", "mismatch", lambda: (_ledger(), _invoice(), _packing(quantity="11"), None)),
        _scenario("INVOICE-PACKING-QUANTITY", "insufficient", "insufficient_evidence", lambda: (_ledger(), _invoice(), _packing(quantity_state="missing"), None)),
        _scenario("PACKING-BL-GROSS-WEIGHT", "match", "match", lambda: (_ledger(), None, _packing(), _bl())),
        _scenario("PACKING-BL-GROSS-WEIGHT", "mismatch", "mismatch", lambda: (_ledger(), None, _packing(), _bl(gross="51"))),
        _scenario("PACKING-BL-GROSS-WEIGHT", "review", "review_required", lambda: (_ledger(), None, _packing(gross_state="ambiguous"), _bl())),
        _scenario("PACKING-BL-GROSS-WEIGHT", "insufficient", "insufficient_evidence", lambda: (_ledger(), None, _packing(), _bl(unit="LB"))),
        _scenario("PACKING-BL-PACKAGE-COUNT", "match", "match", lambda: (_ledger(), None, _packing(), _bl())),
        _scenario("PACKING-BL-PACKAGE-COUNT", "mismatch", "mismatch", lambda: (_ledger(), None, _packing(packages="3"), _bl())),
        _scenario("PACKING-BL-PACKAGE-COUNT", "review", "review_required", lambda: (_ledger(), None, _packing(package_state="ambiguous"), _bl())),
        _scenario("PACKING-BL-PACKAGE-COUNT", "insufficient", "insufficient_evidence", lambda: (_ledger(), None, _packing(package_state="missing"), _bl())),
        _scenario("PARTY-CONSISTENCY", "match", "match", lambda: (_ledger(), None, _packing(), _bl())),
        _scenario("PARTY-CONSISTENCY", "mismatch", "mismatch", lambda: (_ledger(), None, _packing(consignee="OTHER LTD"), _bl())),
        _scenario("PARTY-CONSISTENCY", "review", "review_required", lambda: (_ledger(), None, _packing(), _bl(ambiguous_consignee=True))),
        _scenario("PARTY-CONSISTENCY", "insufficient", "insufficient_evidence", lambda: (_ledger(), None, _packing(consignee="BUYER LTD"), _bl(consignee_state="missing"))),
        _scenario("RECOGNITION-SHIPMENT-DATE", "match", "match", lambda: (_ledger(), None, None, _bl())),
        _scenario("RECOGNITION-SHIPMENT-DATE", "mismatch", "mismatch", lambda: (_ledger(date="2024-01-03"), None, None, _bl())),
        _scenario("RECOGNITION-SHIPMENT-DATE", "insufficient", "insufficient_evidence", lambda: (_ledger(date_state="missing"), None, None, _bl())),
    ]


def evaluate(output_dir: Path) -> dict:
    rows = []
    for scenario in scenarios():
        ledger, invoice, packing, bl = scenario.build()
        findings = validate_transaction(ledger, invoice, packing, bl)
        finding = next((item for item in findings if item.rule_id == scenario.rule_id), None)
        actual = finding.status.value if finding else "missing_rule"
        rows.append({
            "scenario_id": scenario.scenario_id,
            "rule_id": scenario.rule_id,
            "expected_status": scenario.expected_status,
            "actual_status": actual,
            "correct": actual == scenario.expected_status,
            "left_value": finding.left_value if finding else None,
            "right_value": finding.right_value if finding else None,
            "message": finding.message if finding else "Rule did not produce a finding",
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "validation_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    correct = sum(row["correct"] for row in rows)
    actual_counts = Counter(row["actual_status"] for row in rows)

    def precision(status: str) -> float:
        predicted = [row for row in rows if row["actual_status"] == status]
        return sum(row["correct"] for row in predicted) / len(predicted) if predicted else 0.0

    def expected_correctness(status: str) -> float:
        expected = [row for row in rows if row["expected_status"] == status]
        return sum(row["correct"] for row in expected) / len(expected) if expected else 0.0

    metrics = {
        "schema_version": "fintra-ocr-v2.validation-evaluation.v1",
        "scenarios": total,
        "correct": correct,
        "rule_accuracy": correct / total if total else 0.0,
        "actual_status_counts": dict(actual_counts),
        "match_precision": precision("match"),
        "mismatch_precision": precision("mismatch"),
        "review_required_correctness": expected_correctness("review_required"),
        "insufficient_evidence_correctness": expected_correctness("insufficient_evidence"),
        "rules": sorted({row["rule_id"] for row in rows}),
    }
    (output_dir / "validation_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Validation engine evaluation", "",
        "This report evaluates the deterministic validation engine against explicit positive, negative, ambiguous, and insufficient-evidence fixtures. It is a rule-engine evaluation, not a claim about full production transaction coverage.", "",
        "## Metrics", "",
        f"- Rule accuracy: {metrics['rule_accuracy']:.6f} ({correct}/{total})",
        f"- Match precision: {metrics['match_precision']:.6f}",
        f"- Mismatch precision: {metrics['mismatch_precision']:.6f}",
        f"- Review-required correctness: {metrics['review_required_correctness']:.6f}",
        f"- Insufficient-evidence correctness: {metrics['insufficient_evidence_correctness']:.6f}", "",
        "## Rules evaluated", "",
    ]
    lines.extend(f"- `{rule}`" for rule in metrics["rules"])
    lines += ["", "## Incorrect cases", ""]
    incorrect = [row for row in rows if not row["correct"]]
    lines.extend(f"- `{row['scenario_id']}`: expected `{row['expected_status']}`, actual `{row['actual_status']}`" for row in incorrect)
    if not incorrect:
        lines.append("None.")
    (output_dir / "VALIDATION_EVALUATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    metrics = evaluate(args.output_dir)
    print(json.dumps({key: metrics[key] for key in ("scenarios", "rule_accuracy", "match_precision", "mismatch_precision")}, indent=2))
    print(f"VALIDATION_RESULTS={args.output_dir / 'validation_results.csv'}")
    print(f"VALIDATION_METRICS={args.output_dir / 'validation_metrics.json'}")


if __name__ == "__main__":
    main()
