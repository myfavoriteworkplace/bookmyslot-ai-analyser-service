# Deploy bookmyslot-ai-service on Hugging Face Spaces

Free tier — 16GB RAM — no cold starts — no OOM issues.

---

## Before you start

You need:
- A [Hugging Face account](https://huggingface.co/join) (free)
- Your trained `best.pt` model file (downloaded from Google Drive/Colab)
- Git installed on your machine

---

## Part 1 — Create a Hugging Face account

1. Go to [huggingface.co/join](https://huggingface.co/join)
2. Sign up with email
3. Verify your email

---

## Part 2 — Upload your model file to Hugging Face Model Hub

Your `best.pt` is ~22MB — store it in a dedicated model repo so your Space can load it at startup.

### Step 1 — Create a new Model repository

1. Log in to Hugging Face
2. Click your profile picture (top-right) → **New Model**
3. Fill in:
   - **Model name:** `bookmyslot-dentex`
   - **Visibility:** Public (required for free Space to access it)
4. Click **Create model**

### Step 2 — Upload best.pt to the model repo

**Option A — via the website (easiest):**
1. Go to your new model repo page
2. Click **Add file** → **Upload files**
3. Drag and drop your `best.pt` file
4. Commit message: `Add trained DENTEX YOLOv8 model`
5. Click **Commit changes to main**

**Option B — via Git (if file is large or you prefer CLI):**
```bash
# Install Git LFS first (handles large files)
git lfs install

# Clone your model repo
git clone https://huggingface.co/YOUR_USERNAME/bookmyslot-dentex
cd bookmyslot-dentex

# Copy your model in
cp /path/to/best.pt .

# Track .pt files with Git LFS
git lfs track "*.pt"
git add .gitattributes best.pt
git commit -m "Add trained DENTEX YOLOv8 model"
git push
```

### Step 3 — Note your model URL

Your model file is now at:
```
https://huggingface.co/YOUR_USERNAME/bookmyslot-dentex/resolve/main/best.pt
```

Keep this URL — you'll need it in Part 4.

---

## Part 3 — Create a Hugging Face Space

1. Click your profile picture → **New Space**
2. Fill in:
   - **Space name:** `bookmyslot-ai-service`
   - **License:** MIT (or your preference)
   - **SDK:** **Docker** ← important, select Docker
   - **Visibility:** Public (free tier requires public)
3. Click **Create Space**

You'll land on an empty Space with a default `README.md`.

---

## Part 4 — Add a Space secret for your model URL

Hugging Face Spaces support secrets (like Render env vars).

1. In your Space → **Settings** tab
2. Scroll to **Repository secrets**
3. Click **New secret**
4. Add:
   - **Name:** `MODEL_DOWNLOAD_URL`
   - **Value:** `https://huggingface.co/YOUR_USERNAME/bookmyslot-dentex/resolve/main/best.pt`
5. Click **Save**

> Using the HuggingFace model URL directly instead of Google Drive is more reliable — no "Anyone with link" permission issues.

---

## Part 5 — Update your Dockerfile for Hugging Face

Hugging Face Spaces require the app to listen on **port 7860** (not 8000).

Update `bookmyslot-ai-service/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p models uploads

ENV MODEL_PATH=models/best.pt
ENV CONFIDENCE_THRESHOLD=0.25
ENV MODEL_DOWNLOAD_URL=""

# Hugging Face Spaces uses port 7860
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

## Part 6 — Push your code to the Space

Hugging Face Spaces are Git repositories. You push code to them just like GitHub.

### Step 1 — Get your Space's Git URL

In your Space → **Files** tab → **Clone repository** button

URL format:
```
https://huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service
```

### Step 2 — Add HuggingFace as a remote to your local repo

```bash
cd bookmyslot-ai-service

# Initialize git if not already done
git init

# Add Hugging Face Space as remote
git remote add huggingface https://huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service
```

### Step 3 — Push the service code

```bash
git add .
git commit -m "Initial deployment"
git push huggingface main
```

You'll be prompted for credentials:
- **Username:** your HuggingFace username
- **Password:** your HuggingFace **access token** (not your password — see step below)

### Step 4 — Create a HuggingFace access token (for git push)

1. HuggingFace → Profile → **Settings** → **Access Tokens**
2. Click **New token**
3. Name: `deployment`
4. Role: **Write**
5. Copy the token — use it as your git password

---

## Part 7 — Watch the build

1. Go to your Space page: `https://huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service`
2. Click the **Logs** tab (top-right of the Space)
3. Watch the Docker build + startup

Expected log sequence:
```
Building Docker image...
Successfully built
Pre-loading YOLO model at startup...
Downloading model from HuggingFace...
Model downloaded successfully (21.5 MB)
Loading YOLO model from models/best.pt
Model loaded successfully
Model ready.
Application startup complete.
Uvicorn running on http://0.0.0.0:7860
```

First build takes 3–5 minutes (Docker image + dependencies). Subsequent builds use the cache and are faster.

---

## Part 8 — Test your live Space

Your Space is live at:
```
https://YOUR_USERNAME-bookmyslot-ai-service.hf.space
```

**Health check:**
```bash
curl https://YOUR_USERNAME-bookmyslot-ai-service.hf.space/
```

Expected:
```json
{ "service": "BookMySlot AI", "status": "running" }
```

**X-ray analysis:**
```bash
curl -X POST 'https://YOUR_USERNAME-bookmyslot-ai-service.hf.space/analyse-xray' \
  --form 'file=@/path/to/xray.png'
```

**In Postman:**
```
POST https://YOUR_USERNAME-bookmyslot-ai-service.hf.space/analyse-xray
Body → form-data → key: file, type: File, value: your xray image
```

---

## Part 9 — Update your Node backend

Change `AI_SERVICE_URL` in your Node backend `.env`:

```
AI_SERVICE_URL=https://YOUR_USERNAME-bookmyslot-ai-service.hf.space
```

---

## Advantages over Render (why this is better)

| | Render Free | Hugging Face Spaces |
|---|---|---|
| RAM | 512MB 💥 | **16GB** ✅ |
| Sleeps after inactivity | Yes (15 min) | **No** ✅ |
| OOM on inference | Yes 💥 | **Never** ✅ |
| Cold start | ~35s | **None** ✅ |
| Model storage | Google Drive (fragile) | HuggingFace Hub (reliable) ✅ |
| Cost | Free | **Free** ✅ |

---

## Troubleshooting

**Build fails with `port already in use`:**
Make sure `Dockerfile` uses port `7860` not `8000`.

**Model not downloading:**
Check the `MODEL_DOWNLOAD_URL` secret in Space Settings → Repository secrets.
Verify the model repo is **Public**.

**`git push` asks for password:**
Use your HuggingFace **Access Token** (not your account password). Create one at Settings → Access Tokens.

**Space shows "Building" for more than 10 minutes:**
Check the Logs tab for errors. Most common cause is a missing system dependency in the Dockerfile.

**CORS error from frontend:**
The Space URL is `https://YOUR_USERNAME-bookmyslot-ai-service.hf.space` — make sure this is what your Node backend calls, not the Render URL.
