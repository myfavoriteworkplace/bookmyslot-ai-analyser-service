# API Endpoints

Base URL (Hugging Face): `https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space`  
Base URL (local dev): `http://localhost:8000`

---

## GET `/`

**Purpose:** Health check — confirms the service is running and the model loaded successfully.

**Response:** JSON

```bash
curl https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/
```

**Success response:**
```json
{
  "service": "BookMySlot AI",
  "status": "running"
}
```

**Error response (model failed to load):**
```json
{
  "service": "BookMySlot AI",
  "status": "error: Model not found at 'models/best.pt' ..."
}
```

---

## GET `/test`

**Purpose:** Browser-based visual test tool. Upload an X-ray image and see the JSON findings or the annotated image directly in the browser — no curl or frontend required.

**How to use:** Open this URL in a browser, drag-and-drop an X-ray image, and click either **Analyse** or **Annotate**.

```
https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/test
```

---

## POST `/analyse-xray`

**Purpose:** Accept a dental X-ray image, run YOLOv8 inference, and return all detected findings as structured JSON. Findings are deduplicated using per-class NMS (inside YOLO) and a second cross-class IoU suppression pass.

**Request:** `multipart/form-data` with a single field `file` (JPEG, PNG, WebP, or BMP).

**Response:** JSON

```bash
curl -X POST \
  https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/analyse-xray \
  -F "file=@/path/to/xray.jpg"
```

**Local dev:**
```bash
curl -X POST http://localhost:8000/analyse-xray \
  -F "file=@/path/to/xray.jpg"
```

**Success response:**
```json
{
  "success": true,
  "analysis": {
    "findings": [
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
      },
      {
        "class_id": 3,
        "label": "Impacted Tooth",
        "confidence": 74.0,
        "location": {
          "x": 180.0,
          "y": 310.5,
          "width": 60.2,
          "height": 72.8
        }
      }
    ]
  },
  "message": null
}
```

**Location fields** — all values are in pixels, relative to the original image:
| Field | Description |
|---|---|
| `x` | Centre X of the bounding box |
| `y` | Centre Y of the bounding box |
| `width` | Width of the bounding box |
| `height` | Height of the bounding box |

**Class IDs:**
| `class_id` | `label` |
|---|---|
| 0 | Caries |
| 1 | Deep Caries |
| 2 | Periapical Lesion |
| 3 | Impacted Tooth |

**Error response:**
```json
{
  "success": false,
  "analysis": null,
  "message": "AI service unavailable: model file not found"
}
```

**Supported formats:** `image/jpeg`, `image/png`, `image/webp`, `image/bmp`

---

## POST `/analyse-xray/annotated`

**Purpose:** Same inference as `/analyse-xray`, but instead of returning JSON it returns the original X-ray image with bounding boxes and labels rendered on it as a PNG. Useful for visual verification of detection quality without building a frontend.

**Request:** `multipart/form-data` with a single field `file` (same formats as above).

**Response:** `image/png` binary stream, with one extra header:

| Header | Description |
|---|---|
| `X-Finding-Count` | Number of findings drawn on the image |
| `Content-Disposition` | `inline; filename=annotated.png` |

**Colour coding:**
| Class | Colour |
|---|---|
| Caries | Amber `#FFB400` |
| Deep Caries | Red `#FF5050` |
| Periapical Lesion | Green `#50C878` |
| Impacted Tooth | Blue `#64B4FF` |

```bash
curl -X POST \
  https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/analyse-xray/annotated \
  -F "file=@/path/to/xray.jpg" \
  --output annotated.png
```

**Local dev:**
```bash
curl -X POST http://localhost:8000/analyse-xray/annotated \
  -F "file=@/path/to/xray.jpg" \
  --output annotated.png
```

Then open `annotated.png` to inspect the result.

**Check finding count from header only (no file save):**
```bash
curl -X POST \
  https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/analyse-xray/annotated \
  -F "file=@/path/to/xray.jpg" \
  -o /dev/null \
  -D - | grep x-finding-count
```

---

## Interactive API Docs (FastAPI built-in)

FastAPI automatically generates interactive API documentation:

| Doc type | URL |
|---|---|
| Swagger UI | `https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/docs` |
| ReDoc | `https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/redoc` |

---

## Environment Variables (tunable without code changes)

| Variable | Default | Description |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | `0.55` | Minimum confidence for a detection to be kept |
| `NMS_IOU_THRESHOLD` | `0.30` | IoU threshold for YOLO's per-class NMS |
| `MAX_DETECTIONS` | `30` | Maximum number of boxes YOLO will return |
| `CROSS_CLASS_IOU_THRESHOLD` | `0.50` | IoU threshold for the post-YOLO cross-class suppression pass |
| `MODEL_PATH` | `models/best.pt` | Path to the YOLOv8 weights file |
| `MODEL_DOWNLOAD_URL` | *(empty)* | Google Drive shareable link; model auto-downloads if file is missing |
| `DEBUG` | `false` | Set to `true` to expose full error messages in API responses |
