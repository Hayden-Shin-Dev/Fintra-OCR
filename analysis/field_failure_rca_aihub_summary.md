# AI-Hub field failure root-cause summary

- Failure count: 18
- Classification counts: `{"EXTRACTION_MISSING": 1, "OCR_MISSING": 16, "WRONG_SELECTION": 1}`
- `OCR_MISSING` means the expected value was not sufficiently present in raw OCR; it is not an extractor defect.
- Expected bbox is a semantic GT field bbox only when the reconstructed oracle provides one. Otherwise the report marks it unavailable; matched raw OCR bboxes are listed separately.

## Failure table

| document | type | field | class | expected | output | raw evidence | bbox source |
|---|---|---|---|---|---|---|---|
| IMG_OCR_6_T_BL_001677 | bill_of_lading | consignee | EXTRACTION_MISSING | "Tlease proydde compleee name" | null | True | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_BL_002596 | bill_of_lading | consignee | WRONG_SELECTION | "LERN TECHNOLOGY GROUP" | "LERN TECHNOLOGY GROUP" | True | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_000322 | commercial_invoice | amount | OCR_MISSING | {"value": 39583.47, "symbol": "$", "currency_code": null} | "$39,583.7" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001677 | commercial_invoice | amount | OCR_MISSING | {"value": 12003.64, "symbol": "$", "currency_code": null} | "$12,003.6" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001677 | commercial_invoice | invoice_no | OCR_MISSING | "210217" | "895-353-5469" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001774 | commercial_invoice | amount | OCR_MISSING | {"value": 38904.35, "symbol": "$", "currency_code": null} | "$38900435" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001825 | commercial_invoice | amount | OCR_MISSING | {"value": 30333.65, "symbol": "$", "currency_code": null} | "$30,333.6" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001825 | commercial_invoice | invoice_no | OCR_MISSING | "233963" | "233965" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001943 | commercial_invoice | amount | OCR_MISSING | {"value": 19000.01, "symbol": "$", "currency_code": null} | null | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001943 | commercial_invoice | currency | OCR_MISSING | {"code": "USD", "symbol": null} | null | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_001943 | commercial_invoice | invoice_no | OCR_MISSING | "311992" | "311999" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_002913 | commercial_invoice | amount | OCR_MISSING | {"value": 49180.67, "symbol": "$", "currency_code": null} | "$49,180.7" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_002913 | commercial_invoice | currency | OCR_MISSING | {"code": "CAD", "symbol": null} | "$" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_002913 | commercial_invoice | invoice_no | OCR_MISSING | "807797" | "316-937-4094" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_BL_003578 | bill_of_lading | consignee | OCR_MISSING | "QHOENIX TELECOM" | "WINNIE,," | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_003235 | commercial_invoice | amount | OCR_MISSING | {"value": 3985.55, "symbol": "$", "currency_code": null} | null | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_NV_003382 | commercial_invoice | quantity | OCR_MISSING | {"items": [{"value": 30, "unit": null}]} | null | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |
| IMG_OCR_6_T_PL_004301 | packing_list | quantity | OCR_MISSING | {"items": [{"value": 1, "unit": null}, {"value": 4, "unit": null}, {"value": 3, "unit": null}]} | "4 | 3" | False | oracle_fields[field].bbox; semantic GT field bbox unavailable |

## Per-failure evidence

### 1. IMG_OCR_6_T_BL_001677 / consignee

- Status/class: `EXTRACTION_MISSING`; extractor status `missing`
- Oracle expected value: `"Tlease proydde compleee name"`
- Expected raw text: ``
- Expected bbox: `null` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `True`
- Raw matches: `[{"index": null, "text": "CONSGNEE Tlease proydde compleee name", "bbox": [[95, 407], [479, 407], [479, 427], [95, 427]], "confidence": 0.8516995878247696, "agreement": 0.8615384615384616}]`
- Selected candidate: `{"value": null, "raw_text": "", "source_indices": [], "bbox": null, "predictions": []}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `False`
- Root cause: expected OCR evidence exists, but label/value attachment did not produce a valid field candidate

### 2. IMG_OCR_6_T_BL_002596 / consignee

- Status/class: `WRONG_SELECTION`; extractor status `found`
- Oracle expected value: `"LERN TECHNOLOGY GROUP"`
- Expected raw text: `LERN TECHNOLOGY GROUP`
- Expected bbox: `[[79, 687], [358, 687], [358, 710], [79, 710]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `True`
- Raw matches: `[{"index": null, "text": "LERN TECHNOLOGY GROUP", "bbox": [[79, 689], [357, 689], [357, 708], [79, 708]], "confidence": 0.9892358520331271, "agreement": 1.0}]`
- Selected candidate: `{"value": "LERN TECHNOLOGY GROUP", "raw_text": "LERN TECHNOLOGY GROUP", "source_indices": [96, 82, 49], "bbox": [[79, 689], [357, 689], [357, 708], [79, 708]], "predictions": [{"index": 96, "text": "LERN", "bbox": [[79, 689], [131, 689], [131, 708], [79, 708]], "confidence": 0.9932254319251885}, {"index": 82, "text": "TECHNOLOGY", "bbox": [[136, 689], [276, 689], [276, 708], [136, 708]], "confidence": 0.9756883382479408}, {"index": 49, "text": "GROUP", "bbox": [[286, 689], [357, 689], [357, 708], [286, 708]], "confidence": 0.9987937859262521}]}`
- Stored-vs-reconstructed oracle conflict: `True`; true failure under reconstructed oracle: `False`
- Root cause: stored regression oracle and reconstructed GT oracle disagree; treat the stored failure as oracle disagreement/manual review

### 3. IMG_OCR_6_T_NV_000322 / amount

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `{"value": 39583.47, "symbol": "$", "currency_code": null}`
- Expected raw text: `$39,583.47`
- Expected bbox: `[[938, 1793], [1063, 1793], [1063, 1827], [938, 1827]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "$39,583.7", "raw_text": "$39,583.7", "source_indices": [45], "bbox": [[937, 1799], [1065, 1799], [1065, 1825], [937, 1825]], "predictions": [{"index": 45, "text": "$39,583.7", "bbox": [[937, 1799], [1065, 1799], [1065, 1825], [937, 1825]], "confidence": 0.8335585396652275}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 4. IMG_OCR_6_T_NV_001677 / amount

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `{"value": 12003.64, "symbol": "$", "currency_code": null}`
- Expected raw text: `$12,003.64`
- Expected bbox: `[[938, 1793], [1100, 1793], [1100, 1828], [938, 1828]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "$12,003.6", "raw_text": "$12,003.6", "source_indices": [163], "bbox": [[937, 1799], [1105, 1799], [1105, 1828], [937, 1828]], "predictions": [{"index": 163, "text": "$12,003.6", "bbox": [[937, 1799], [1105, 1799], [1105, 1828], [937, 1828]], "confidence": 0.935555076499309}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 5. IMG_OCR_6_T_NV_001677 / invoice_no

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `"210217"`
- Expected raw text: `210217`
- Expected bbox: `[[830, 293], [938, 293], [938, 327], [830, 327]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "895-353-5469", "raw_text": "895-353-5469", "source_indices": [90], "bbox": [[829, 367], [1035, 367], [1035, 395], [829, 395]], "predictions": [{"index": 90, "text": "895-353-5469", "bbox": [[829, 367], [1035, 367], [1035, 395], [829, 395]], "confidence": 0.9648265638469309}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 6. IMG_OCR_6_T_NV_001774 / amount

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `{"value": 38904.35, "symbol": "$", "currency_code": null}`
- Expected raw text: `$38,904.35`
- Expected bbox: `[[938, 1793], [1063, 1793], [1063, 1827], [938, 1827]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "$38900435", "raw_text": "$38900435", "source_indices": [56], "bbox": [[937, 1799], [1065, 1799], [1065, 1825], [937, 1825]], "predictions": [{"index": 56, "text": "$38900435", "bbox": [[937, 1799], [1065, 1799], [1065, 1825], [937, 1825]], "confidence": 0.8810467966089573}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 7. IMG_OCR_6_T_NV_001825 / amount

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `{"value": 30333.65, "symbol": "$", "currency_code": null}`
- Expected raw text: `$30,333.65`
- Expected bbox: `[[938, 1793], [1054, 1793], [1054, 1828], [938, 1828]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "$30,333.6", "raw_text": "$30,333.6", "source_indices": [44], "bbox": [[938, 1797], [1056, 1797], [1056, 1825], [938, 1825]], "predictions": [{"index": 44, "text": "$30,333.6", "bbox": [[938, 1797], [1056, 1797], [1056, 1825], [938, 1825]], "confidence": 0.9942746450408715}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 8. IMG_OCR_6_T_NV_001825 / invoice_no

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `"233963"`
- Expected raw text: `233963`
- Expected bbox: `[[830, 293], [910, 293], [910, 328], [830, 328]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "233965", "raw_text": "233965", "source_indices": [116], "bbox": [[831, 298], [912, 298], [912, 322], [831, 322]], "predictions": [{"index": 116, "text": "233965", "bbox": [[831, 298], [912, 298], [912, 322], [831, 322]], "confidence": 0.8742671391598912}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 9. IMG_OCR_6_T_NV_001943 / amount

- Status/class: `OCR_MISSING`; extractor status `missing`
- Oracle expected value: `{"value": 19000.01, "symbol": "$", "currency_code": null}`
- Expected raw text: `$19,000.01`
- Expected bbox: `[[938, 1793], [1080, 1793], [1080, 1826], [938, 1826]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": null, "raw_text": "", "source_indices": [], "bbox": null, "predictions": []}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 10. IMG_OCR_6_T_NV_001943 / currency

- Status/class: `OCR_MISSING`; extractor status `missing`
- Oracle expected value: `{"code": "USD", "symbol": null}`
- Expected raw text: `USD`
- Expected bbox: `[[1377, 1861], [1432, 1861], [1432, 1892], [1377, 1892]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": null, "raw_text": "", "source_indices": [], "bbox": null, "predictions": []}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 11. IMG_OCR_6_T_NV_001943 / invoice_no

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `"311992"`
- Expected raw text: `311992`
- Expected bbox: `[[830, 293], [927, 293], [927, 327], [830, 327]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "311999", "raw_text": "311999", "source_indices": [98], "bbox": [[831, 300], [929, 300], [929, 326], [831, 326]], "predictions": [{"index": 98, "text": "311999", "bbox": [[831, 300], [929, 300], [929, 326], [831, 326]], "confidence": 0.8952177124152044}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 12. IMG_OCR_6_T_NV_002913 / amount

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `{"value": 49180.67, "symbol": "$", "currency_code": null}`
- Expected raw text: `$49,180.67`
- Expected bbox: `[[938, 1793], [1080, 1793], [1080, 1828], [938, 1828]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "$49,180.7", "raw_text": "$49,180.7", "source_indices": [130], "bbox": [[938, 1799], [1080, 1799], [1080, 1826], [938, 1826]], "predictions": [{"index": 130, "text": "$49,180.7", "bbox": [[938, 1799], [1080, 1799], [1080, 1826], [938, 1826]], "confidence": 0.9364587547281473}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 13. IMG_OCR_6_T_NV_002913 / currency

- Status/class: `OCR_MISSING`; extractor status `ambiguous`
- Oracle expected value: `{"code": "CAD", "symbol": null}`
- Expected raw text: `CAD`
- Expected bbox: `[[1377, 1861], [1439, 1861], [1439, 1890], [1377, 1890]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "$", "raw_text": "$49,180.7", "source_indices": [130], "bbox": [[938, 1799], [1080, 1799], [1080, 1826], [938, 1826]], "predictions": [{"index": 130, "text": "$49,180.7", "bbox": [[938, 1799], [1080, 1799], [1080, 1826], [938, 1826]], "confidence": 0.9364587547281473}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 14. IMG_OCR_6_T_NV_002913 / invoice_no

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `"807797"`
- Expected raw text: `807797`
- Expected bbox: `[[830, 293], [924, 293], [924, 328], [830, 328]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "316-937-4094", "raw_text": "316-937-4094", "source_indices": [67], "bbox": [[829, 368], [1006, 368], [1006, 395], [829, 395]], "predictions": [{"index": 67, "text": "316-937-4094", "bbox": [[829, 368], [1006, 368], [1006, 395], [829, 395]], "confidence": 0.9649232290973259}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 15. IMG_OCR_6_T_BL_003578 / consignee

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `"QHOENIX TELECOM"`
- Expected raw text: `QHOENIX TELECOM`
- Expected bbox: `[[122, 395], [391, 395], [391, 427], [122, 427]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "WINNIE,,", "raw_text": "WINNIE,,", "source_indices": [60], "bbox": [[396, 430], [549, 430], [549, 457], [396, 457]], "predictions": [{"index": 60, "text": "WINNIE,,", "bbox": [[396, 430], [549, 430], [549, 457], [396, 457]], "confidence": 0.8133022902807806}]}`
- Stored-vs-reconstructed oracle conflict: `True`; true failure under reconstructed oracle: `False`
- Root cause: stored regression oracle and reconstructed GT oracle disagree; treat the stored failure as oracle disagreement/manual review

### 16. IMG_OCR_6_T_NV_003235 / amount

- Status/class: `OCR_MISSING`; extractor status `missing`
- Oracle expected value: `{"value": 3985.55, "symbol": "$", "currency_code": null}`
- Expected raw text: `$3,985.55`
- Expected bbox: `[[332, 1619], [440, 1619], [440, 1648], [332, 1648]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": null, "raw_text": "", "source_indices": [], "bbox": null, "predictions": []}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 17. IMG_OCR_6_T_NV_003382 / quantity

- Status/class: `OCR_MISSING`; extractor status `missing`
- Oracle expected value: `{"items": [{"value": 30, "unit": null}]}`
- Expected raw text: `30`
- Expected bbox: `[[368, 499], [391, 499], [391, 516], [368, 516]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": null, "raw_text": "", "source_indices": [], "bbox": null, "predictions": []}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it

### 18. IMG_OCR_6_T_PL_004301 / quantity

- Status/class: `OCR_MISSING`; extractor status `found`
- Oracle expected value: `{"items": [{"value": 1, "unit": null}, {"value": 4, "unit": null}, {"value": 3, "unit": null}]}`
- Expected raw text: `1 4 3`
- Expected bbox: `[[930, 1133], [946, 1133], [946, 1401], [930, 1401]]` (oracle_fields[field].bbox; semantic GT field bbox unavailable)
- Expected text in raw OCR: `False`
- Raw matches: `[]`
- Selected candidate: `{"value": "4 | 3", "raw_text": "4 3", "source_indices": [60, 56], "bbox": [[931, 1258], [946, 1258], [946, 1403], [931, 1403]], "predictions": [{"index": 60, "text": "4", "bbox": [[931, 1258], [945, 1258], [945, 1278], [931, 1278]], "confidence": 0.9991781115350136}, {"index": 56, "text": "3", "bbox": [[931, 1376], [946, 1376], [946, 1403], [931, 1403]], "confidence": 0.9889183643488778}]}`
- Stored-vs-reconstructed oracle conflict: `False`; true failure under reconstructed oracle: `True`
- Root cause: expected value was not present as a sufficiently matching raw OCRPrediction; extractor rules cannot recover it
