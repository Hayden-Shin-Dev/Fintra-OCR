# Testing

Run the dependency-free unit suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

The tests cover schema validation, OCR adapter/extractor behavior,
normalization, cross-document rules, and the downstream review contract. They
use synthetic in-memory OCR regions only; they do not read `sample.zip` or the
ignored AI-Hub artifacts.

The real Modern OCR 15-document evaluation remains recorded separately in
`MODERN_DETECTION_E2E_RESULT.md` and its local ignored artifact directory.
