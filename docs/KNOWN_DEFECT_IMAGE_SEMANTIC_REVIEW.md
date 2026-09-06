# Known Gold defect image semantic review

This is a separate human visual-review record. It is not a Gold generator and
does not read OCR or extractor output. The reviewed images are the preserved
Training case image.png files; the source token indices come from the
manifest-referenced original AI-Hub Training TL entry.

## Review results

| case | field | visible semantic structure | source evidence | classification |
|---|---|---|---|---|
| bl01-081-IMG_OCR_6_T_BL_004108 | port_of_loading | Port of Loading cell is the left port cell; its value is OHSE, JAPAN | TL indices 12,13 | VERIFIED_GOLD_MAPPING_ERROR |
| bl01-081-IMG_OCR_6_T_BL_004108 | port_of_discharge | Port of Discharge cell is the right port cell; its value is GUINES, FRANCE | TL indices 14,15 | VERIFIED_GOLD_MAPPING_ERROR |
| bl02-081-IMG_OCR_6_T_BL_009123 | port_of_loading | Port of Loading cell contains LOMOND, CANADA | TL indices 55,56 | VERIFIED_GOLD_MAPPING_ERROR |
| bl02-081-IMG_OCR_6_T_BL_009123 | port_of_discharge | Port of Discharge cell contains LATCHI, CYPRUS | TL indices 63,64 | VERIFIED_GOLD_MAPPING_ERROR |
| inv01-084-IMG_OCR_6_T_NV_003885 | items[0].description | Item Description column row 1 contains Fire Extinguisher, Fire Suppression; 1111.39 is in the HS Code column | TL indices 50-53 | VERIFIED_GOLD_MAPPING_ERROR |
| inv01-084-IMG_OCR_6_T_NV_003885 | items[1].description | Item Description column row 2 contains Plate Glass Artifacts; 7134.60 is in the HS Code column | TL indices 64-66 | VERIFIED_GOLD_MAPPING_ERROR |
| inv01-084-IMG_OCR_6_T_NV_003885 | items[2].description | Item Description column row 3 contains Connector, Rear; 0149.02 is in the HS Code column | TL indices 72,73 | VERIFIED_GOLD_MAPPING_ERROR |
| inv01-082-IMG_OCR_6_T_NV_003882 | items[1].description | Description of Good(s) row 2 contains PLUG-WAX INJECTION HOLE; Prism is in the separate Shipping mark column | TL indices 56-58 | VERIFIED_GOLD_MAPPING_ERROR |

The classification means the old Gold assignment is contradicted by the
visible label/column structure and the new source-token assignment is
supported by that image review. It does not imply that every other field in
the same document has been semantically verified.

## Limitations

This review covers the eight previously known defects only. It is not an
exhaustive review of all Accurate75 or Balanced300 available fields. Those
fields remain outside the trusted denominator until the same independent
image/header/layout evidence is recorded or are conservatively marked
ambiguous_gt.

FINAL-HOLDOUT #2 was not accessed.
