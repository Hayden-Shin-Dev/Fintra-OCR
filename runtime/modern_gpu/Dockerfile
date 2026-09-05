FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements-recognition.txt /tmp/requirements-recognition.txt

RUN pip install --no-cache-dir -r /tmp/requirements-recognition.txt

COPY vendor/original_recognition /opt/fintra/vendor/original_recognition
COPY modern_recognition.py /opt/fintra/modern_recognition.py
COPY compare_recognition.py /opt/fintra/compare_recognition.py
WORKDIR /project
