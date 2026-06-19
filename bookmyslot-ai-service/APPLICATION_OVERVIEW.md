# BookMySlot AI Service — Application Overview

## What This Service Does

BookMySlot AI Service is a Python microservice that accepts a dental panoramic X-ray image, runs it through a trained YOLOv8 object detection model, and returns a structured list of detected dental findings — with their labels, confidence scores, and bounding box coordinates.

It is one component of the broader BookMySlot healthcare platform. The Node.js backend calls this service over HTTP; no code or models are shared between the two.

---

## The Problem It Solves

Reading a dental panoramic X-ray requires a trained dentist and takes time. This service automates the first-pass screening: it flags regions of concern (cavities, deep caries, impacted wisdom teeth, periapical lesions) so a dentist can focus their attention on the highlighted areas rather than scanning the entire image from scratch.

---

## Architecture

```
Patient / Clinic App
        │
        ▼
Node.js BookMySlot API  (Express)
        │  HTTP POST /analyse-xray
        ▼
bookmyslot-ai-service   (FastAPI + Python)
        │
        ▼
YOLOv8 Inference        (Ultralytics, PyTorch)
        │
        ▼
Structured JSON Findings
```

The AI service is **fully independent** of the Node.js backend — it has no shared database, no shared code, and no shared dependencies. The Node.js API calls it over HTTP and forwards the response to the frontend.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI (Python 3.11) |
| ASGI server | Uvicorn |
| Object detection | YOLOv8 via Ultralytics |
| Deep learning runtime | PyTorch (CPU-only build) |
| Image processing | Pillow, OpenCV (headless) |
| Data validation | Pydantic v2 |
| Deployment | Hugging Face Spaces (Docker SDK, port 7860) |

---

## How Inference Works (Step by Step)

### 1. Image Upload
The client sends a `multipart/form-data` POST request with the X-ray image to `/analyse-xray`. Supported formats are JPEG, PNG, WebP, and BMP.

### 2. Temporary File Save
The image is written to a temporary file in the `uploads/` directory with a UUID filename to prevent collisions. The file is deleted immediately after inference regardless of success or failure.

### 3. YOLOv8 Inference
The YOLOv8 model (`best.pt`) processes the image and returns a list of detected bounding boxes. Three parameters control what gets kept at this stage:

- **Confidence threshold** (`CONFIDENCE_THRESHOLD`, default `0.55`): any detection below this confidence is discarded.
- **IoU threshold for NMS** (`NMS_IOU_THRESHOLD`, default `0.30`): within the same class, overlapping boxes above this IoU are suppressed, keeping only the most confident one.
- **Max detections** (`MAX_DETECTIONS`, default `30`): hard cap on the total number of boxes returned by YOLO.

### 4. Cross-Class IoU Suppression (Post-Processing)
YOLOv8's built-in NMS only suppresses overlapping boxes of the **same class**. This causes crowding in areas where multiple disease types are detected on the same tooth — for example, a "Caries" box and an "Impacted Tooth" box both covering the same region.

To fix this, after YOLO returns its results the service applies a second suppression pass across **all classes combined**:

1. All findings are sorted by confidence (highest first).
2. For every pair of boxes, the IoU is computed.
3. If two boxes from **different classes** overlap by more than `CROSS_CLASS_IOU_THRESHOLD` (default `0.50`), the lower-confidence one is dropped.

This significantly reduces the visual crowding seen in panoramic X-rays.

### 5. JSON Response
Each surviving detection is returned as a finding object:

```json
{
  "class_id": 0,
  "label": "Caries",
  "confidence": 82.4,
  "location": {
    "x": 412.5,
    "y": 230.1,
    "width": 48.3,
    "height": 55.7
  }
}
```

The `location` coordinates are in pixels, relative to the original uploaded image, using the **centre-x / centre-y / width / height** convention (same as YOLO output).

---

## Disease Classes

The model was trained on the [DENTEX dataset](https://github.com/ibrahimethemhamamci/DENTEX) and detects four categories mapped from `category_id_1`:

| Class ID | Label | Description |
|---|---|---|
| 0 | Caries | Tooth decay (cavity) |
| 1 | Deep Caries | Advanced decay reaching near or into the pulp |
| 2 | Periapical Lesion | Infection at the tip of a tooth root |
| 3 | Impacted Tooth | Tooth that has not fully erupted (e.g. wisdom teeth) |

> **Note:** These labels reflect the DENTEX `category_id_1` taxonomy and are not mapped to any assumed clinical severity. The dentist interprets clinical relevance.

---

## Model File (`best.pt`)

The YOLOv8 weights file is **never committed to git** because it is large (typically 50–200 MB). It must be provided at runtime via one of two mechanisms:

1. **Manual placement:** Copy `best.pt` into `bookmyslot-ai-service/models/` before starting the service.
2. **Auto-download:** Set the `MODEL_DOWNLOAD_URL` environment variable to a publicly shared Google Drive link. The service will download the file at startup if it is not found locally.

On Hugging Face Spaces, the model should be stored on a persistent disk or downloaded at startup — it must not be baked into the Docker image if it exceeds ~50 MB.

---

## Visual Test Tool

A built-in HTML test page is served at `/test`. It requires no external tooling:

- Drag-and-drop or browse for an X-ray image
- **Analyse (JSON):** calls `/analyse-xray` and shows a colour-coded findings list
- **Annotate (Image):** calls `/analyse-xray/annotated` and renders the X-ray with bounding boxes drawn on it directly in the browser, with a download button

This is the fastest way to visually verify that the model and deduplication are working correctly after a deployment.

---

## Deployment

The service runs in a Docker container on Hugging Face Spaces (Docker SDK):

- **Port:** 7860 (required by HF Spaces)
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port 7860`
- **CI/CD:** Every push to the `main` branch that touches `bookmyslot-ai-service/**` triggers the GitHub Actions workflow (`.github/workflows/sync-to-hf.yml`), which uses `git subtree split` to push only the `bookmyslot-ai-service/` folder to the HF Space, then runs a smoke test against the health check endpoint.

---

## Local Development

```bash
cd bookmyslot-ai-service
pip install -r requirements.txt
# Place best.pt in models/ or set MODEL_DOWNLOAD_URL
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/test` in a browser to use the visual test tool.

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| CPU-only PyTorch build | Avoids ~1.5 GB of CUDA libraries on GPU-less servers (HF free tier, Render) |
| Temporary file per request, deleted immediately | Prevents accumulation of patient data on disk |
| Model loaded once at startup, reused per request | Avoids multi-second cold starts on every inference call |
| Cross-class NMS as a post-processing step | YOLO's built-in NMS is per-class only; cross-class suppression needed to avoid label crowding on the same tooth |
| All thresholds as environment variables | Enables threshold tuning on HF Spaces without code changes or redeployment |
| AI service fully decoupled from Node.js backend | Allows independent scaling, deployment, and replacement of the AI component |
