# Dockerfile (auto 2025-08-09T12:25:01.103453Z)
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-ind && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip && pip install -r requirements.txt
EXPOSE 10000

CMD ["python","main.py"]
