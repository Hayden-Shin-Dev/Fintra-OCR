# AI-Hub logistics runtime

The official logistics model runs in a subprocess so the existing PaddleOCR
`.venv` remains untouched. The worker loads the official `OCRMaskRCNN`
detector (ResNet-50/FPN/mask head) and `vitstr_small_patch16_224` recognizer,
then emits Fintra's shared `OCRPrediction` objects.

## Selective model extraction

Do not expand the 93GB `AI모델.zip` archive as a whole. Extract only:

- the official `source_code` tree;
- `configs/transit_config.py`;
- the logistics detector and recognizer checkpoints;
- the logistics dictionary/recognizer metadata.

The adapter accepts these locations explicitly because the checkpoints are
normally stored outside the source tree.

## Isolated Windows runtime

The tested fallback is Python 3.12 in `.venv-aihub-cpu` with the pinned
packages in `requirements-aihub-cpu.txt`. Docker and WSL are optional. The
runtime is intentionally separate from the Paddle environment.

```powershell
py -3.12 -m venv .venv-aihub-cpu
.venv-aihub-cpu\Scripts\python -m pip install -r requirements-aihub-cpu.txt
.venv-aihub-cpu\Scripts\python scripts/run_aihub_sample.py data/sample.zip `
  --source-root C:\path\to\source_code `
  --dictionary C:\path\to\transit_recog_model_info.txt `
  --detector-config C:\path\to\transit_config.py `
  --detector-checkpoint C:\path\to\transit_detection_model.pth `
  --recognizer-checkpoint C:\path\to\transit_recog_model.pth `
  --runtime-python .venv-aihub-cpu\Scripts\python.exe `
  --device cpu
```

The one-image proof and lightweight 31-document A/B outputs are under
`analysis/aihub_sample_e2e/` and `analysis/aihub_paddle_ab.json`. These are
real detector/recognizer outputs; recognizer confidence is computed from
token probabilities and is never mocked.
