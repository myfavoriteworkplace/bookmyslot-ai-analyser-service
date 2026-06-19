FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p models uploads

ENV MODEL_PATH=models/best.pt
ENV CONFIDENCE_THRESHOLD=0.55
ENV NMS_IOU_THRESHOLD=0.30
ENV MAX_DETECTIONS=30
ENV CROSS_CLASS_IOU_THRESHOLD=0.50
ENV MODEL_DOWNLOAD_URL=""

# Port 7860 required by Hugging Face Spaces
# For Render or other platforms, override with: --port $PORT
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
