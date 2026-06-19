# Deploy bookmyslot-ai-service on Hugging Face Spaces

Free tier — 16GB RAM — no cold starts — no OOM issues.

> This guide includes every minor issue encountered during real deployment and how to fix them.

---

## Before you start

You need:
- A [Hugging Face account](https://huggingface.co/join) (free)
- Your trained `best.pt` model file (downloaded from Google Drive/Colab)
- Git installed on your **local machine** (not Replit shell — Replit's git credential helper blocks external remotes)
- Your local copy of the `bookmyslot-ai-service/` folder

---

## Part 1 — Create a Hugging Face account

1. Go to **https://huggingface.co/join**
2. Fill in username, email, password
3. Click **Create account**
4. Verify your email by clicking the link sent to your inbox
5. You are now logged in

---

## Part 2 — Upload your model file to Hugging Face Model Hub

Store `best.pt` in a dedicated model repository so the Space downloads it reliably at startup — more reliable than Google Drive links.

### Step 1 — Create a Model repository

1. Click your **profile picture** (top-right corner)
2. Click **New Model** from the dropdown menu
3. Fill in:
   - **Owner:** your username (pre-filled)
   - **Model name:** `bookmyslot-dentex`
   - **License:** `mit`
   - **Visibility:** ✅ **Public** ← must be Public or the Space cannot access it
4. Click **Create model**

### Step 2 — Upload best.pt

1. On your model repo page, click the **Files** tab
2. Click **Add file** button → **Upload files**
3. Drag and drop your `best.pt` file onto the upload box
4. Wait for the progress bar to reach 100% (~10–30 seconds for 22MB)
5. In the **Commit changes** section at the bottom type: `Add trained DENTEX YOLOv8 model`
6. Click **Commit changes to main**

### Step 3 — Get the direct download URL

After uploading:
1. Click on `best.pt` in the file list
2. **Right-click the Download button → Copy link address**

The URL format is:
```
https://huggingface.co/YOUR_USERNAME/bookmyslot-dentex/resolve/main/best.pt
```

**Save this URL** — you need it in Part 4.

---

## Part 3 — Create the Docker Space

> ⚠️ If you already created a Space that is showing a "configuration error", delete it first:
> Space → **Settings** tab → scroll to the bottom → **Delete this Space** → confirm.
> Then follow these steps to recreate it correctly.

1. Click your **profile picture** → **New Space**
2. Fill in:
   - **Owner:** your username (pre-filled)
   - **Space name:** `bookmyslot-ai-service`
   - **License:** `mit`
   - **Select the Space SDK:** click **Docker** ← critical — NOT Gradio, NOT Streamlit
   - **Docker template:** `Blank` (first option)
   - **Visibility:** ✅ **Public**
3. Click **Create Space**

You land on the Space page. It shows a default `README.md` with a template.

---

## Part 4 — Fix the README.md immediately (CRITICAL — do this before pushing code)

> ⚠️ This is the most common failure point. HuggingFace requires a specific YAML block at the top of `README.md`. If it is missing or wrong, the Space shows "Missing configuration in README" and will not build.
> Do this step **in the browser** before any git push.

1. On your Space page, click the **Files** tab
2. Click `README.md` in the file list
3. Click the **pencil/edit icon** (top-right of the file content area)
4. **Select all text (Ctrl+A) and delete everything**
5. Paste exactly this:

```
---
title: Bookmyslot AI Service
emoji: 🦷
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

BookMySlot dental X-ray AI analysis service.
```

6. Scroll down → click **Commit changes to main**

The configuration error disappears immediately after saving. The Space will show "Building" briefly, then pause waiting for the Dockerfile.

> **Why this must be done in the browser first:**
> When you push code via git, HuggingFace checks `README.md` for the YAML block. If the push contains a `README.md` without the block, or if there is a merge conflict on `README.md`, the Space enters an error state. Editing in the browser first guarantees the correct README is in place before your code arrives.

---

## Part 5 — Create a HuggingFace Access Token

You need this to push code via git.

1. Click your **profile picture** → **Settings**
2. In the left sidebar, click **Access Tokens**
3. Click **New token**
4. Fill in:
   - **Token name:** `deployment`
   - **Role:** **Write**
5. Click **Generate a token**
6. **Copy the token immediately** — it starts with `hf_` and you cannot see it again after leaving the page

---

## Part 6 — Add Space secrets (environment variables)

1. On your Space → click **Settings** tab
2. Scroll to **Repository secrets**
3. Add these three secrets one by one (click **New secret** for each):

| Name | Value |
|---|---|
| `MODEL_DOWNLOAD_URL` | `https://huggingface.co/YOUR_USERNAME/bookmyslot-dentex/resolve/main/best.pt` |
| `MODEL_PATH` | `models/best.pt` |
| `CONFIDENCE_THRESHOLD` | `0.25` |

4. Click **Save** after each one

---

## Part 7 — Push code from your local machine

> ⚠️ Use your **local machine terminal**, not the Replit shell.
> Replit's shell uses `replit-git-askpass` which blocks credential prompts for external services like HuggingFace and causes `fatal: expected 'acknowledgments'` errors.

Open a terminal on your local machine and run:

### Step 1 — Clone or copy the service folder locally

If you are working from this repo, pull it to your local machine:
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME
cd YOUR_REPO_NAME/bookmyslot-ai-service
```

Or if you already have the folder locally, navigate into it:
```bash
cd path/to/bookmyslot-ai-service
```

### Step 2 — Initialize git (if not already a git repo)

```bash
git init
git add .
git commit -m "Initial deployment to HuggingFace Spaces"
```

### Step 3 — Add HuggingFace as a git remote

Embed your access token directly in the URL to avoid credential prompts:

```bash
git remote add huggingface https://YOUR_USERNAME:YOUR_HF_TOKEN@huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service
```

Replace:
- `YOUR_USERNAME` → your HuggingFace username (e.g. `itsmyfavoriteworkplace`)
- `YOUR_HF_TOKEN` → your token from Step 5 (e.g. `hf_AbCdEfGh...`)

Verify it was added:
```bash
git remote -v
```
You should see two `huggingface` lines.

### Step 4 — Pull the HuggingFace initial commit first

HuggingFace creates an initial commit when you create the Space (the README you edited in Part 4). You must pull it before pushing:

```bash
git pull huggingface main --allow-unrelated-histories
```

If git opens a text editor (vim) for the merge commit message:
- Press **Escape**, then type `:wq`, then press **Enter**

If git opens nano:
- Press **Ctrl+X**, then **Y**, then **Enter**

### Step 5 — Push your code

```bash
git push huggingface main
```

If push is rejected with "fetch first" error, force push:
```bash
git push huggingface main --force
```

Successful output looks like:
```
Enumerating objects: 18, done.
Writing objects: 100% (18/18)
To https://huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service
   abc1234..def5678  main -> main
```

---

## Part 8 — Watch the build

1. Go to: `https://huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service`
2. Click the **Logs** tab → select **Build logs**
3. Watch the Docker build:

```
Step 1/8 : FROM python:3.11-slim
Step 2/8 : RUN apt-get update...
Step 3/8 : COPY requirements.txt
Step 4/8 : RUN pip install...      ← takes 2-3 minutes
Step 5/8 : COPY . .
...
Successfully built ✅
```

4. Switch to **Container logs** to watch the service start:

```
Pre-loading YOLO model at startup...
Downloading model from HuggingFace...
Model downloaded successfully (21.5 MB)
Loading YOLO model from models/best.pt
Model loaded successfully
Model ready.
Application startup complete.
Uvicorn running on http://0.0.0.0:7860
```

**Total first-build time: 4–6 minutes.**

Subsequent builds use Docker layer cache and take ~1 minute.

---

## Part 9 — Test your live service

Your Space URL is always:
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

**X-ray analysis (curl):**
```bash
curl -X POST 'https://YOUR_USERNAME-bookmyslot-ai-service.hf.space/analyse-xray' \
  --form 'file=@/path/to/xray.png'
```

**X-ray analysis (Postman):**
- Method: `POST`
- URL: `https://YOUR_USERNAME-bookmyslot-ai-service.hf.space/analyse-xray`
- Body: `form-data`
- Key: `file` | Type: `File` | Value: select your X-ray image
- Use **Desktop Agent** (not Cloud Agent) — Cloud Agent has a 30-second timeout

---

## Part 10 — Update your Node backend

In your Node.js backend `.env` file:
```
AI_SERVICE_URL=https://YOUR_USERNAME-bookmyslot-ai-service.hf.space
```

---

## Advantages over Render

| | Render Free | Hugging Face Spaces |
|---|---|---|
| RAM | 512MB 💥 OOM | **16GB** ✅ |
| Sleeps after inactivity | Yes (15 min) | **No** ✅ |
| OOM on YOLOv8 inference | Yes 💥 | **Never** ✅ |
| Cold start | ~35s | **None** ✅ |
| Model storage | Google Drive (unreliable) | HuggingFace Hub ✅ |
| Postman timeout | Yes (30s Cloud Agent) | **No** ✅ |
| Cost | Free | **Free** ✅ |

---

## Troubleshooting

### "Missing configuration in README"
HuggingFace cannot find the required YAML block in `README.md`.

Fix: Edit `README.md` directly in the browser (Space → Files → README.md → pencil icon). Paste the YAML block from Part 4 at the very top. Commit. Error clears immediately.

Do NOT rely on git push to fix this — do it in the browser first.

---

### `fatal: unable to read askpass response from 'replit-git-askpass'`
You are pushing from the Replit shell. Replit blocks credential prompts for external services.

Fix: Push from your **local machine terminal** instead.

---

### `fatal: expected 'acknowledgments'`
Git protocol version 2 is being blocked by Replit's proxy.

Fix: Push from your **local machine terminal** instead. If you must use Replit, prefix with:
```bash
git -c protocol.version=0 pull huggingface main --allow-unrelated-histories
```

---

### `[rejected] main -> main (fetch first)`
HuggingFace has a commit you don't have locally (the initial README commit).

Fix:
```bash
git pull huggingface main --allow-unrelated-histories
git push huggingface main
```
Or skip the pull entirely:
```bash
git push huggingface main --force
```

---

### `error: No such remote 'huggingface'`
The remote was never added. Run:
```bash
git remote add huggingface https://YOUR_USERNAME:YOUR_HF_TOKEN@huggingface.co/spaces/YOUR_USERNAME/bookmyslot-ai-service
```

---

### Space shows "Your space is in error"
Check **Logs → Container logs** for the specific error. Common causes:
- `MODEL_DOWNLOAD_URL` secret not set — add it in Settings → Repository secrets
- Model repo is not Public — go to your model repo → Settings → change to Public
- Port mismatch — confirm `Dockerfile` uses `7860` not `8000`

---

### Model download fails silently (tiny file downloaded)
The `MODEL_DOWNLOAD_URL` secret points to a private HuggingFace model repo.

Fix: Go to your model repo (`huggingface.co/YOUR_USERNAME/bookmyslot-dentex`) → Settings → change Visibility to **Public**.

---

### Build fails immediately after push
The `README.md` frontmatter was overwritten by your push with a version that doesn't have it.

Fix: Edit `README.md` in the browser again (Part 4). Then push again with:
```bash
git push huggingface main --force
```

---

## Quick reference

| Thing | Value |
|---|---|
| Model repo name | `bookmyslot-dentex` |
| Space name | `bookmyslot-ai-service` |
| Space SDK | Docker |
| App port | `7860` |
| Model URL pattern | `https://huggingface.co/USERNAME/bookmyslot-dentex/resolve/main/best.pt` |
| Live service URL | `https://USERNAME-bookmyslot-ai-service.hf.space` |
| Secret name | `MODEL_DOWNLOAD_URL` |
