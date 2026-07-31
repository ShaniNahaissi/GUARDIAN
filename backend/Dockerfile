FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Python 3.11 (matches previous python:3.11-slim base) + runtime libs required by OpenCV/ONNX.
# onnxruntime-gpu (pinned to 1.20.2 in requirements.txt) needs CUDA 12 + cuDNN 9 to actually
# use the GPU instead of silently falling back to CPU -- see bl/detection/providers.py.
# 12.8 specifically matches this deploy server's driver (570.211.01, max supported CUDA 12.8);
# newer onnxruntime-gpu releases require CUDA 13, which this driver doesn't support.
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    openssl \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && rm -rf /var/lib/apt/lists/*

COPY trained_model/guardian_backend_model.onnx /app/trained_model/guardian_backend_model.onnx
COPY trained_model/names.txt /app/trained_model/names.txt
COPY trained_model/yolov8n_person.onnx /app/trained_model/yolov8n_person.onnx
COPY trained_model/temporal_action_weights.npz /app/trained_model/temporal_action_weights.npz

COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh

COPY backend/requirements.txt /app/requirements.txt
RUN python3.11 -m pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

ENV GUARDIAN_TLS_ENABLED=1 \
    GUARDIAN_TLS_AUTO_CERT=1

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD []
