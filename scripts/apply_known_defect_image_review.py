"""Join explicit human image-review decisions to source-only defect records."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.records.read_text(encoding="utf-8"))
    reviews = {
        (item["case_id"], item["field_name"]): item
        for item in json.loads(args.review.read_text(encoding="utf-8"))
    }
    audited = []
    for record in records:
        item = dict(record)
        review = reviews.get((record["case_id"], record["field_name"]))
        if review is None:
            item["classification"] = "CANNOT_VERIFY"
            item["semantic_reason"] = "No explicit image review decision was supplied"
        else:
            item["classification"] = review["classification"]
            item["visible_anchor"] = review["visible_anchor"]
            item["visible_value_position"] = review["visible_value_position"]
            item["semantic_reason"] = "Image/header/table structure independently reviewed"
        item["prediction_blind"] = True
        item["ocr_read"] = False
        item["extractor_read"] = False
        item["final_holdout_2_accessed"] = False
        audited.append(item)
    result = {
        "records": len(audited),
        "classifications": dict(Counter(item["classification"] for item in audited)),
        "records_source": str(args.records),
        "review_source": str(args.review),
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"metrics": result, "records": audited}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
