# bookmyslot-ai-service

Python FastAPI microservice for AI-powered dental X-ray analysis using YOLOv8.

## Architecture

```
React App
    |
Node Backend (BookMySlot API)
    |
bookmyslot-ai-service  <-- this service
    |
YOLOv8 (best.pt)
    |
Detection JSON
```

## Project Structure

```
bookmyslot-ai-service/
├── app/
│   ├── main.py        # FastAPI routes
│   ├── model.py       # YOLOv8 inference logic
│   └── schemas.py     # Pydantic response models
├── models/
│   └── best.pt        # ← place your trained model here (not committed to git)
├── uploads/           # Temporary image storage during inference (auto-cleaned)
├── requirements.txt
├── Dockerfile
└── .gitignore
```

## Model Setup

The trained model file (`best.pt`) is **not committed to git**.

Download it from Colab/Google Drive and place it at:
```
models/best.pt
```

Or set the `MODEL_PATH` environment variable to point to another location.

### Save from Colab
```python
from google.colab import drive
drive.mount('/content/drive')
!cp /content/runs/detect/train/weights/best.pt /content/drive/MyDrive/bookmyslot-best.pt
```
Then download from Google Drive to `models/best.pt`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_PATH` | `models/best.pt` | Path to the trained YOLOv8 model |
| `CONFIDENCE_THRESHOLD` | `0.25` | Minimum confidence score for detections |
| `PORT` | `8000` | Server port (set automatically by Render) |

## Running Locally

```bash
cd bookmyslot-ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### `GET /`
Health check.
```json
{ "service": "BookMySlot AI", "status": "running" }
```

### `POST /analyse-xray`
Analyse a dental X-ray image.

**Request:** `multipart/form-data` with field `file` (JPEG/PNG/WebP/BMP)

**Success response:**
```json
{
  "success": true,
  "analysis": {
    "findings": [
      {
        "class_id": 0,
        "label": "Finding Type 1",
        "confidence": 91.0,
        "location": { "x": 100.0, "y": 200.0, "width": 300.0, "height": 400.0 }
      }
    ]
  }
}
```

**Error response:**
```json
{ "success": false, "message": "Invalid X-ray image" }
```

## Class Mapping

Based on DENTEX `category_id_1` labels:

| Class ID | Label |
|---|---|
| 0 | Finding Type 1 |
| 1 | Finding Type 2 |
| 2 | Finding Type 3 |
| 3 | Finding Type 4 |

Labels will be updated once DENTEX taxonomy is validated.

## Deployment on Render

1. Create a new **Web Service** on Render
2. Connect this repository
3. Set **Root Directory** to `bookmyslot-ai-service`
4. **Build command:** `pip install -r requirements.txt`
5. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `MODEL_PATH=models/best.pt`
   - `CONFIDENCE_THRESHOLD=0.25`
7. Upload `best.pt` to Render's persistent disk or download it at startup

## Node Backend Integration

The Node.js backend should call this service via HTTP:

```js
const formData = new FormData();
formData.append('file', imageBuffer, { filename: 'xray.jpg', contentType: 'image/jpeg' });

const response = await fetch('https://your-ai-service.onrender.com/analyse-xray', {
  method: 'POST',
  body: formData,
});

const result = await response.json();
```
