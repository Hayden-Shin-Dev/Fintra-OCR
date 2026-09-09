"""Run with the engine Python. Does not run OCR or LLM inference."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
from urllib.request import urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--require-gpu", action="store_true")
    args = parser.parse_args()
    report = {"python": sys.executable, "versions": {}, "model": args.model,
              "live_inference_tested": False, "errors": []}
    for package in ("fintraocr", "paddleocr", "paddlepaddle", "paddlepaddle-gpu", "tokenizers"):
        try:
            report["versions"][package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            report["versions"][package] = None
    if report["versions"]["paddlepaddle"] and report["versions"]["paddlepaddle-gpu"]:
        report["errors"].append("Both CPU and GPU Paddle packages are installed")
    try:
        import paddle
        report["cuda_compiled"] = bool(paddle.is_compiled_with_cuda())
        report["gpu_count"] = int(paddle.device.cuda.device_count()) if report["cuda_compiled"] else 0
        if args.require_gpu and not report["gpu_count"]:
            report["errors"].append("GPU was required but Paddle reports no usable GPU")
    except Exception as exc:
        report["errors"].append("Paddle unavailable: " + str(exc))
    if not report["versions"]["paddleocr"]:
        report["errors"].append("PaddleOCR is not installed")
    try:
        import fintraocr
        root = Path(fintraocr.__file__).resolve().parent
        report["engine_package"] = str(root)
        report["tokenizer_exists"] = (root / "assets/qwen35-tokenizer.json").is_file()
        if not report["tokenizer_exists"]:
            report["errors"].append("Bundled tokenizer is absent")
    except Exception as exc:
        report["errors"].append("Engine unavailable: " + str(exc))
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            report["installed_models"] = [entry["name"] for entry in json.load(response)["models"]]
        if args.model not in report["installed_models"]:
            report["errors"].append("Requested local Ollama model is not installed")
    except Exception as exc:
        report["errors"].append("Local Ollama unavailable: " + str(exc))
    report["preflight_passed"] = not report["errors"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["preflight_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
