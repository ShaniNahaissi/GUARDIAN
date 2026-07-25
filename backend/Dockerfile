FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime libs required by OpenCV/ONNX on Debian slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY trained_model/guardian_backend_model.onnx /app/trained_model/guardian_backend_model.onnx
COPY trained_model/names.txt /app/trained_model/names.txt
COPY trained_model/yolov8n_person.onnx /app/trained_model/yolov8n_person.onnx

COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

ENV GUARDIAN_TLS_ENABLED=1 \
    GUARDIAN_TLS_AUTO_CERT=1

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD []
