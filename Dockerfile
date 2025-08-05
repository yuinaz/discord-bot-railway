# ======================
# SatpamBot Dockerfile
# ======================

# Gunakan base image Python ringan
FROM python:3.10-slim

# Install dependency sistem (Tesseract OCR, dll)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set direktori kerja
WORKDIR /app

# Salin semua file ke dalam container
COPY . .

# Install dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Jalankan aplikasi
CMD ["python", "main.py"]
