# MedVerify backend image.
# NOTE: this pulls in TensorFlow, so the resulting image is large (~2GB+).
# The API works fine without TensorFlow (see cnn_inference.py) — if you don't
# need the CNN anomaly/classifier checks, remove the `tensorflow` line from
# requirements.txt before building for a much smaller image.
FROM python:3.11-slim

# System dependencies needed for QR/barcode (zbar) and OCR (tesseract).
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data and model directories are expected to be mounted as volumes in
# docker-compose.yml (they contain large files that don't belong baked
# into the image, and the model files are optional).
RUN mkdir -p /app/tmp_uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
