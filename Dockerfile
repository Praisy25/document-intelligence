FROM python:3.13-slim

# Install Tesseract OCR and required system libraries
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Application directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY backend /app/backend
COPY frontend /app/frontend

# Allow Python to find the backend package
ENV PYTHONPATH=/app/backend

# Start FastAPI
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}