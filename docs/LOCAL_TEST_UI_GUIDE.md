# Local test UI

The Streamlit review UI is a thin client of the backend extraction contract.
It does not contain document-specific extraction logic.

From the project root, inside the validated Paddle environment:

```powershell
python -m pip install -r requirements-ui.txt
streamlit run app.py -- --device gpu --mode accurate
```

Choose `Commercial Invoice`, `Packing List`, or `B/L`, upload one image, and
review the returned canonical JSON. The UI provides:

- selected-field or all-field evidence-box highlighting;
- extracted value, status, confidence, source text, and bbox;
- OCR runtime and region count;
- collapsible raw OCR regions;
- the complete evidence-bearing canonical response.

For a CPU smoke test use `--device cpu`. GPU execution is intentionally an
operator action in the validated Paddle environment.
