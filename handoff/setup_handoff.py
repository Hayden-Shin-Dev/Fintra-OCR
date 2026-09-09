"""Install into this bundle's .fintra-venv; never modify the team's Python.

Network is used only by the explicitly requested pip install / model pull.
GPU runtime option reproduces the original Windows CUDA-12.6 configuration;
other GPUs/driver platforms need their own Paddle compatibility verification.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import venv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, choices=["none", "cpu", "gpu-cu126"])
    parser.add_argument("--pull-model", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        parser.error("Use Python 3.10, 3.11 or 3.12; Python 3.11 was tested in CI")
    wheels = sorted((root / "dist").glob("fintraocr-*.whl"))
    if len(wheels) != 1:
        parser.error("Expected exactly one engine wheel in dist/. Use the built handoff ZIP.")
    environment = root / ".fintra-venv"
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    probe = "import importlib.metadata as m; print(*[d.metadata['Name'].lower() for d in m.distributions()], sep=chr(10))"
    check = subprocess.run([str(python), "-c", probe], text=True, capture_output=True, check=True)
    installed = set(check.stdout.splitlines())
    if args.runtime == "cpu" and "paddlepaddle-gpu" in installed:
        parser.error("This isolated environment already uses GPU Paddle. Do not install CPU and GPU Paddle together.")
    if args.runtime == "gpu-cu126" and "paddlepaddle" in installed:
        parser.error("This isolated environment already uses CPU Paddle. Create a separate bundle/environment for GPU.")
    extras = "ui,test" if args.runtime == "none" else "ocr,ui,test"
    command = [str(python), "-m", "pip", "install", str(wheels[0]) + "[" + extras + "]"]
    constraints = root / "runtime-constraints.txt"
    if args.runtime != "none" and constraints.exists():
        command += ["-c", str(constraints)]
    subprocess.run(command, check=True)
    if args.runtime == "cpu":
        subprocess.run([str(python), "-m", "pip", "install", "paddlepaddle==3.3.1"], check=True)
    elif args.runtime == "gpu-cu126":
        subprocess.run([str(python), "-m", "pip", "install", "paddlepaddle-gpu==3.3.1", "--index-url", "https://www.paddlepaddle.org.cn/packages/stable/cu126/"], check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    if args.pull_model:
        ollama = shutil.which("ollama")
        if not ollama:
            parser.error("Install and start local Ollama first, then rerun with --pull-model. Python setup is retained.")
        subprocess.run([ollama, "pull", "qwen3.5:4b"], check=True)
    print("Engine Python:", python)
    print("Offline smoke: ", python, root / "smoke_handoff.py")
    print("Live environment check:", python, root / "doctor.py")


if __name__ == "__main__":
    main()
