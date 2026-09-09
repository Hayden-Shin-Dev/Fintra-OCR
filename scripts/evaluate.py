"""Evaluate reviewed ground truth against output; missing expected fields count as failures.
Gold format: {"document_type": "commercial_invoice", "fields": {"invoice_number": "...", "buyer": null}, "items": [{"quantity": "10"}]}
Only explicitly annotated fields are scored; items are aligned by human-verified row order.
"""
import argparse
import json
from pathlib import Path

def evaluate(gold, result):
    pairs = []
    for name,value in gold.get("fields",{}).items():
        pairs.append((value,result.get("fields",{}).get(name,{}).get("value")))
    expected_rows, actual_rows = gold.get("items",[]),result.get("items",[])
    for i,row in enumerate(expected_rows):
        actual = actual_rows[i] if i < len(actual_rows) else {}
        pairs.extend((value,actual.get(name,{}).get("value")) for name,value in row.items())
    populated = [(a,b) for a,b in pairs if b is not None]
    expected = [(a,b) for a,b in pairs if a is not None]
    return {"type_correct":gold["document_type"]==result["document_type"],
        "annotated_fields":len(pairs), "exact_matches":sum(a==b for a,b in pairs),
        "extraction_precision":sum(a==b for a,b in populated)/len(populated) if populated else None,
        "non_null_coverage":sum(b is not None for a,b in expected)/len(expected) if expected else None,
        "false_non_null":sum(a is None and b is not None for a,b in pairs),
        "missing_non_null":sum(a is not None and b is None for a,b in pairs),
        "extra_rows":max(0,len(actual_rows)-len(expected_rows)),
        "missing_rows":max(0,len(expected_rows)-len(actual_rows))}
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("gold");parser.add_argument("result")
    args=parser.parse_args()
    print(json.dumps(evaluate(json.loads(Path(args.gold).read_text(encoding="utf-8")),json.loads(Path(args.result).read_text(encoding="utf-8"))),indent=2))
