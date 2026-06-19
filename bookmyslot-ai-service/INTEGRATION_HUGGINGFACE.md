# BookMySlot AI Service — Hugging Face Spaces Integration Guide

Base URL (production):
```
https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space
```

---

## API Reference

### 1. Health Check

**`GET /`**

Check whether the service is running and the model is loaded.

#### Request
No body or headers required.

```bash
curl https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/
```

#### Success Response — `200 OK`
```json
{
  "service": "BookMySlot AI",
  "status": "running"
}
```

#### Error Response — model failed to load — `200 OK`
```json
{
  "service": "BookMySlot AI",
  "status": "error: Model not found at 'models/best.pt' and MODEL_DOWNLOAD_URL is not set."
}
```

> Always call this endpoint first before sending X-ray images to confirm the model is ready.

---

### 2. Interactive API Docs

FastAPI auto-generates a Swagger UI available at:

```
https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/docs
```

Use this to test the API directly in your browser — no code or Postman needed.

---

### 3. Analyse X-Ray

**`POST /analyse-xray`**

Submit a dental X-ray image for AI analysis. Returns detected findings with confidence scores and bounding box positions.

#### Request

| Property | Value |
|---|---|
| Method | `POST` |
| Content-Type | `multipart/form-data` |
| Field name | `file` |
| Accepted formats | `image/jpeg`, `image/png`, `image/webp`, `image/bmp` |
| Max recommended size | 10 MB |

```bash
curl -X POST 'https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space/analyse-xray' \
  --header 'accept: application/json' \
  --form 'file=@/path/to/xray.png'
```

---

#### Success Response — `200 OK`

```json
{
  "success": true,
  "analysis": {
    "findings": [
      {
        "class_id": 0,
        "label": "Finding Type 1",
        "confidence": 91.5,
        "location": {
          "x": 312.4,
          "y": 215.8,
          "width": 48.2,
          "height": 36.7
        }
      },
      {
        "class_id": 2,
        "label": "Finding Type 3",
        "confidence": 76.3,
        "location": {
          "x": 540.1,
          "y": 198.4,
          "width": 52.0,
          "height": 41.5
        }
      }
    ]
  },
  "message": null
}
```

**No findings detected:**
```json
{
  "success": true,
  "analysis": {
    "findings": []
  },
  "message": null
}
```

---

#### Error Responses — `200 OK`

All errors return HTTP `200` with `success: false`. Always check the `success` field — never rely on HTTP status alone.

| Scenario | `message` value |
|---|---|
| Model not loaded / download failed | `"AI service unavailable: <reason>"` |
| Unsupported file format | `"Invalid X-ray image. Supported formats: JPEG, PNG, WebP, BMP."` |
| Empty file uploaded | `"Uploaded file is empty."` |
| Inference crash | `"AI service unavailable: inference failed"` |

```json
{
  "success": false,
  "analysis": null,
  "message": "AI service unavailable: model file not found"
}
```

---

## Response Schema

### `AnalyseResponse`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `success` | `boolean` | No | `true` if analysis ran successfully |
| `analysis` | `Analysis \| null` | Yes | Present only when `success: true` |
| `message` | `string \| null` | Yes | Present only when `success: false` |

### `Analysis`

| Field | Type | Description |
|---|---|---|
| `findings` | `Finding[]` | Array of detected findings (empty array = no findings) |

### `Finding`

| Field | Type | Description |
|---|---|---|
| `class_id` | `integer` | DENTEX class ID (0–3) |
| `label` | `string` | Human-readable label (`"Finding Type 1"` to `"Finding Type 4"`) |
| `confidence` | `float` | Confidence score as percentage (0–100) |
| `location` | `Location` | Bounding box in pixel coordinates |

### `Location`

| Field | Type | Description |
|---|---|---|
| `x` | `float` | X coordinate of bounding box centre |
| `y` | `float` | Y coordinate of bounding box centre |
| `width` | `float` | Bounding box width in pixels |
| `height` | `float` | Bounding box height in pixels |

### Class Mapping

| `class_id` | `label` | Description |
|---|---|---|
| `0` | `"Caries"` | Tooth decay / cavity |
| `1` | `"Deep Caries"` | Advanced decay reaching the pulp |
| `2` | `"Periapical Lesion"` | Infection or abscess at the root tip |
| `3` | `"Impacted Tooth"` | Tooth that has not fully erupted |

---

## Node.js Backend Integration (Render → Hugging Face)

### Install dependency
```bash
npm install form-data
# node-fetch only needed if on Node < 18
npm install node-fetch
```

### Helper module — `services/aiService.js`

```js
const FormData = require('form-data');
// Remove the line below if you are on Node 18+ (native fetch is built-in)
const fetch = require('node-fetch');

const AI_SERVICE_URL =
  process.env.AI_SERVICE_URL ||
  'https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space';

/**
 * Analyse a dental X-ray image buffer.
 * @param {Buffer} imageBuffer - Raw image bytes
 * @param {string} filename - Original filename (e.g. 'xray.png')
 * @param {string} mimeType - MIME type (e.g. 'image/jpeg')
 * @returns {Promise<AnalyseResponse>}
 */
async function analyseXray(imageBuffer, filename, mimeType) {
  const form = new FormData();
  form.append('file', imageBuffer, { filename, contentType: mimeType });

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000); // 60s timeout

  try {
    const response = await fetch(`${AI_SERVICE_URL}/analyse-xray`, {
      method: 'POST',
      body: form,
      headers: form.getHeaders(),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`AI service HTTP error: ${response.status}`);
    }

    return response.json();
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Check if the AI service is healthy and model is loaded.
 * @returns {Promise<boolean>}
 */
async function isAiServiceHealthy() {
  try {
    const response = await fetch(`${AI_SERVICE_URL}/`, { timeout: 10000 });
    const data = await response.json();
    return data.status === 'running';
  } catch {
    return false;
  }
}

module.exports = { analyseXray, isAiServiceHealthy };
```

### Express route — `routes/xray.js`

```js
const express = require('express');
const multer = require('multer');
const { analyseXray } = require('../services/aiService');

const router = express.Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10 MB
});

/**
 * POST /api/xray/analyse
 * Accepts multipart image, forwards to AI service, returns findings.
 */
router.post('/analyse', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, message: 'No image file provided.' });
    }

    const result = await analyseXray(
      req.file.buffer,
      req.file.originalname,
      req.file.mimetype
    );

    if (!result.success) {
      return res.status(502).json({
        success: false,
        message: result.message || 'AI analysis failed.',
      });
    }

    return res.json({
      success: true,
      findings: result.analysis.findings,
    });

  } catch (err) {
    if (err.name === 'AbortError') {
      return res.status(504).json({
        success: false,
        message: 'AI service timed out. Please try again.',
      });
    }
    console.error('AI service error:', err);
    return res.status(503).json({
      success: false,
      message: 'AI service is currently unavailable. Please try again.',
    });
  }
});

module.exports = router;
```

### TypeScript types (if using TS backend)

```ts
export interface Location {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Finding {
  class_id: number;
  label: string;
  confidence: number;
  location: Location;
}

export interface Analysis {
  findings: Finding[];
}

export interface AnalyseResponse {
  success: boolean;
  analysis: Analysis | null;
  message: string | null;
}
```

---

## Environment Variable

Add to your Node backend `.env` on Render:

```
AI_SERVICE_URL=https://itsmyfavoriteworkplace-bookmyslot-ai-service.hf.space
```

---

## Hugging Face Spaces — Important Notes

### Sleep / Cold Starts (Free Tier)
On the **free tier**, Hugging Face Spaces go to sleep after **48 hours of inactivity**. When a sleeping Space receives a request, it wakes up — but the first request will time out while the container boots and the YOLO model loads (can take **30–60 seconds**).

Options to handle this:
- Send a `GET /` ping before the real request, and retry once if it fails
- Set up an external uptime monitor (e.g. [UptimeRobot](https://uptimerobot.com)) to ping `GET /` every 20 minutes
- Upgrade to a paid Hugging Face Space (always-on)

**Wake-up ping pattern in Node.js:**
```js
async function wakeAndAnalyse(imageBuffer, filename, mimeType) {
  // Try to wake the space first
  await isAiServiceHealthy().catch(() => {});
  // Wait a moment if it was sleeping
  await new Promise(resolve => setTimeout(resolve, 3000));
  return analyseXray(imageBuffer, filename, mimeType);
}
```

### Model File
The YOLO model (`models/best.pt`) is **not stored in the Space's git repo** (too large). It is downloaded at startup from Google Drive using the `MODEL_DOWNLOAD_URL` environment variable.

Set this in your Hugging Face Space settings:
1. Go to your Space → **Settings** → **Variables and secrets**
2. Add a secret: `MODEL_DOWNLOAD_URL` = your Google Drive shareable link

If this is not set, the health check will return:
```json
{ "status": "error: Model not found at 'models/best.pt' and MODEL_DOWNLOAD_URL is not set." }
```

### Persistent Storage
Hugging Face free Spaces do **not** have persistent storage. The `uploads/` folder (used for temporary inference files) is ephemeral and cleared on each restart — this is fine since files are deleted immediately after inference.

### Timeout Recommendation
Set your Node.js fetch timeout to **60 seconds** minimum. Inference on CPU can take 5–15 seconds, and cold starts add extra time on top.

### File Size Limit
Keep uploads under **10 MB**. Apply the limit in your multer config (shown above).

---

## Error Scenarios — Quick Reference

| Scenario | Where it fails | What you see | How to handle |
|---|---|---|---|
| Space is sleeping | First request after inactivity | Fetch timeout / connection refused | Ping `GET /`, wait 5s, retry |
| Model not downloaded | Startup / `GET /` | `status: "error: ..."` | Set `MODEL_DOWNLOAD_URL` in HF Space secrets |
| Wrong file format | `POST /analyse-xray` | `success: false`, message about format | Validate MIME type before sending |
| Empty file | `POST /analyse-xray` | `success: false`, `"Uploaded file is empty."` | Check buffer length before sending |
| Inference crash | `POST /analyse-xray` | `success: false`, `"AI service unavailable: inference failed"` | Log and surface a user-friendly error |
| Network timeout | Your Node backend | `AbortError` | Catch `AbortError`, return 504 to client |
| HF Space down | Any request | Connection refused or 5xx | Return 503, alert via monitoring |
