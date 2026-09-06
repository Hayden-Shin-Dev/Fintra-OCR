# Accurate75 #1 Generalization-Development Analysis

This report uses only the Accurate75 #1 development set, its frozen Paddle
recognition JSON, the prepared semantic gold, and the current extractor. The
untouched Accurate75 #2 holdout is not read, evaluated, or used for tuning.

## Evaluation boundary

- Development set: `artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1`
- Frozen OCR source: `artifacts/fintra/train-scale-v1/paddle-ocr-accurate-holdout/cases`
- Current extractor evaluation: `artifacts/fintra/_tmp_eval_after_fragment3`
- Gold and OCR are unchanged by this iteration.
- The final holdout allowlist is `artifacts/fintra/train-scale-v1/parallel/accurate-final-balanced75.txt` and remains reserved.

The current Accurate75 #1 result is 362/518 (69.884%). By document type:

| Type | Correct | Applicable | Accuracy |
|---|---:|---:|---:|
| Commercial Invoice | 110 | 181 | 60.77% |
| Packing List | 110 | 154 | 71.43% |
| B/L | 142 | 183 | 77.60% |

Using the existing primary-field definition, the same run gives 166/205
(80.98%) overall: CI 51/74 (68.92%), Packing List 58/69 (84.06%), and B/L
57/62 (91.94%).

The current raw-OCR-recoverable but not correctly extracted set contains 105
rows. The diagnostic subtype split is:

| Cause | Count |
|---|---:|
| Candidate generation | 72 |
| Row selection | 15 |
| Normalization | 13 |
| Candidate ranking | 5 |

These are diagnostic labels, not gold-generation rules. They indicate where
the active extractor and the raw-evidence diagnostic disagree.

## Generalization clusters

All five source groups for each document family are represented in the
development failures. The largest current field clusters are:

| Document type | Field | Candidate-generation rows |
|---|---|---:|
| Commercial Invoice | item description | 15 |
| B/L | port of loading | 8 |
| Commercial Invoice | buyer | 6 |
| Packing List | item description | 6 |
| Packing List | unit | 5 |
| Packing List | consignee | 5 |
| B/L | goods description | 4 |
| B/L | port of discharge | 3 |
| B/L | vessel | 3 |

### OCR region fragmentation

Paddle sometimes emits a large line plus a smaller contained duplicate, such
as a duplicated legal suffix or a numeric prefix. Combining both regions
caused values such as a party suffix or amount fragment to be appended twice.
This was a document-independent geometry/text issue. The extractor now drops
contained short fragments when the smaller text is a duplicate, while keeping
independent one-letter alphabetic regions. This is the accepted generalized
change in commit `055d28f`.

### Table row/column and semantic mapping boundary

The remaining CI description and table-value clusters are not safe targets for
literal matching. Several development gold rows place a numeric amount or a
different row's value in an item-description field. A typed row resolver must
reject such values rather than learn the development gold projection. These
rows are therefore evidence of a gold/semantic-projection mismatch or an
ambiguous row association until independently re-audited; no case-specific
rule was added.

### B/L port section mapping

The B/L port failures are frequently paired swaps. In inspected examples, the
OCR values sit directly below their respective `PORT OF LOADING` and `PORT OF
DISCHARGE` labels, while the prepared development gold assigns the opposite
values. Changing the resolver to reproduce that swap would violate document
semantics and would not generalize. These rows are retained as benchmark
caveats, not converted into a resolver patch.

### B/L goods/party and Packing table candidates

The remaining goods, party, unit, and description errors include mixed-line
OCR regions, adjacent row text, and partial suffixes. They do not yet form a
single high-confidence mechanism that improves all three regression sets.
The current fragment rule addresses the repeated region-duplication part;
the remaining mixed-row cases require a separate typed row/section analysis
before any change is safe.

## Candidate-generator probe

The independent normalized `Layout` strategy was evaluated as a diagnostic
only; it was not made active. Its result was 74/518 (14.29%): CI 33/181,
Packing List 26/154, and B/L 15/183. An oracle union of fields correct under
the active output or the Layout output was 365/518 (70.46%), only three rows
above the current active result. This union is not deployable because it uses
the gold outcome to select between outputs; it therefore does not justify an
active union architecture.

## Regression gate

After the accepted change:

- Accurate75 #1: 344/518 -> 362/518
- Fast balanced300: unchanged at 1673/2339 (71.53%)
- DEV-60 semantic-v3.1: 386/475 -> 398/475 (83.79%)
- Full unittest suite: pass (73 tests)

Because no remaining high-frequency cluster is both unambiguously an
extractor defect and safe to fix without benchmark leakage, no additional
resolver patch is accepted in this iteration. Accurate75 #2 remains an
untouched final holdout and is not evaluated here.
