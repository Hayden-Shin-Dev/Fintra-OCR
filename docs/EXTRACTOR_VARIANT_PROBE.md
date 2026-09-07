# Extractor variant probe

All variants below use frozen OCR and frozen `MVP_DEVELOPMENT_GOLD_V4` (the
DEV60 row uses its historical legacy Gold contract). No OCR or Gold was
modified. Full row-level output is at
`artifacts/fintra/extractor-rebuild/probe/variant_field_results.csv`.

| Set / variant | Overall | OCR recoverable | Correct among recoverable | CI | PL | B/L |
|---|---:|---:|---:|---:|---:|---:|
| Accurate75 active | 377/653 (57.73%) | 570/653 | 361/570 (63.33%) | 47.50% | 67.68% | 67.14% |
| Accurate75 table | 328/653 (50.23%) | 570/653 | 312/570 (54.74%) | 47.50% | 49.05% | 67.14% |
| Accurate75 layout | 245/653 (37.52%) | 570/653 | 245/570 (42.98%) | 48.75% | 33.84% | 0.00% |
| Accurate75 fragment-off | 308/653 (47.17%) | 570/653 | 292/570 (51.23%) | 45.31% | 53.99% | 30.00% |
| Fast300 active | 1687/2409 (70.03%) | 2096/2409 | 1677/2096 (80.01%) | 78.12% | 64.95% | 57.00% |
| Fast300 table | 1553/2409 (64.47%) | 2096/2409 | 1543/2096 (73.62%) | 78.12% | 51.68% | 57.00% |
| Fast300 layout | 1332/2409 (55.29%) | 2096/2409 | 1332/2096 (63.55%) | 74.95% | 44.36% | 18.77% |
| DEV60 active | 113/410 (27.56%) | 209/410 | 112/209 (53.59%) | 36.59% | 42.54% | 7.19% |

The complete report also contains legacy, typed, ordered, typed-ordered, and
fragment-on-active rows. The active strategy is the only tested option that
preserved the current three-set behavior; the alternative layout/table
variants were not promoted.
