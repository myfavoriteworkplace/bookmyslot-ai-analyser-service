# BookMySlot AI Service — Backend Integration Guide

Base URL (production):
```
https://bookmyslot-ai-analyser-service.onrender.com
```

---

## API Reference

### 1. Health Check

**`GET /`**

Check whether the service is running and the model is loaded.

#### Request
No body or headers required.

```bash
curl https://bookmyslot-ai-analyser-service.onrender.com/
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

> Use this endpoint as a readiness probe before sending X-ray images.

---

### 2. Analyse X-Ray

**`POST /analyse-xray`**

Submit a dental X-ray image for AI analysis. Returns detected findings with confidence scores and bounding box positions.

#### Request

| Property | Value |
|---|---|
| Method | `POST` |
| Content-Type | `multipart/form-data` |
| Field name | `file` |
| Accepted formats | `image/jpeg`, `image/png`, `image/webp`, `image/bmp` |

```bash
curl -X POST 'https://bookmyslot-ai-analyser-service.onrender.com/analyse-xray' \
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

All errors return HTTP `200` with `success: false`. Check `message` for the reason.

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

## Node.js Backend Integration

### Install dependency
```bash
npm install form-data node-fetch
# or if already on Node 18+: native fetch is available, only need form-data
npm install form-data
```

### Helper module — `services/aiService.js`

```js
const FormData = require('form-data');
const fetch = require('node-fetch'); // omit if Node 18+

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'https://bookmyslot-ai-analyser-service.onrender.com';

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

  const response = await fetch(`${AI_SERVICE_URL}/analyse-xray`, {
    method: 'POST',
    body: form,
    headers: form.getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`AI service HTTP error: ${response.status}`);
  }

  return response.json();
}

/**
 * Check if the AI service is healthy.
 * @returns {Promise<boolean>}
 */
async function isAiServiceHealthy() {
  try {
    const response = await fetch(`${AI_SERVICE_URL}/`);
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
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });

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

Add to your Node backend `.env`:

```
AI_SERVICE_URL=https://bookmyslot-ai-analyser-service.onrender.com
```

---

## Important Notes

### Render free tier cold starts
On Render's free plan, the service sleeps after 15 minutes of inactivity. The first request after sleep can take **20–40 seconds**. Options:
- Upgrade to a paid Render instance (always-on)
- Call `GET /` as a wake-up ping before sending the image
- Set up an external uptime monitor (e.g. UptimeRobot) to ping `GET /` every 10 minutes

### File size limit
The AI service has no explicit size limit set. Keep uploads under **10 MB** for reliable performance. Apply a limit in your Node multer config (shown above).

### Timeout
Set a generous timeout on your Node fetch call — model inference on CPU can take **5–15 seconds** per image:

```js
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 30000); // 30s

const response = await fetch(`${AI_SERVICE_URL}/analyse-xray`, {
  method: 'POST',
  body: form,
  headers: form.getHeaders(),
  signal: controller.signal,
}).finally(() => clearTimeout(timeout));
```
