# Issues & Fixes Log — bookmyslot-ai-service

A running record of every real problem encountered during development and deployment, and the exact fix applied.

---

## Issue 1 — OOM crash on Render (out of memory)

**Platform:** Render Free Tier  
**Symptom:** Service started fine but crashed with an out-of-memory (OOM) kill signal the moment the first `/analyse-xray` request came in. Render free tier has only 512MB RAM. YOLOv8 + PyTorch requires ~1.5GB minimum.  
**Root cause:** `requirements.txt` was installing the full GPU version of PyTorch (`torch==2.5.1`) which pulls CUDA libraries even on CPU-only servers, bloating memory usage.  
**Fix:** Switched to CPU-only PyTorch build using the dedicated wheel index:
```
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.5.1+cpu
torchvision==0.20.1+cpu
```
**Result:** Memory usage dropped enough to run on Render's 512MB tier, but inference was still slow. Eventually migrated to HuggingFace Spaces (16GB RAM, no OOM risk).

---

## Issue 2 — Render build failed when `download_model.py` was in build command

**Platform:** Render  
**Symptom:** Build step failed with a file not found or import error when the build command was `pip install -r requirements.txt && python download_model.py`.  
**Root cause:** `download_model.py` was not committed to git (it was gitignored), so Render had no file to run. Also, the model download should happen at startup (runtime), not at build time — build containers are ephemeral and the downloaded file would not persist.  
**Fix:** Changed Render build command to just `pip install -r requirements.txt`. Model download stays in the startup logic inside `app/model.py`.

---

## Issue 3 — `git push` to HuggingFace blocked in Replit shell

**Platform:** Replit shell  
**Symptom:** Running `git push huggingface main` in the Replit shell produced:
```
fatal: unable to read askpass response from 'replit-git-askpass'
```
Even after embedding credentials in the remote URL, a second error appeared:
```
fatal: expected 'acknowledgments'
```
**Root cause:** Replit's shell uses a custom git credential helper (`replit-git-askpass`) that intercepts git operations and blocks credential prompts for non-GitHub remotes. Additionally, Replit's internal proxy blocks git protocol v2 handshakes with external servers like HuggingFace.  
**Fix:** Push from a **local machine terminal** instead of the Replit shell. The Replit shell cannot reliably push to HuggingFace regardless of how credentials are provided.

---

## Issue 4 — `git remote set-url` failed with "No such remote"

**Platform:** Replit shell  
**Symptom:**
```
error: No such remote 'huggingface'
```
**Root cause:** `git remote set-url` and `git remote remove` both require the remote to already exist. The remote `huggingface` was never added with `git remote add` — only `set-url` was attempted.  
**Fix:** Use `git remote add` (not `set-url`) when adding a remote for the first time:
```bash
git remote add huggingface https://USERNAME:TOKEN@huggingface.co/spaces/USERNAME/bookmyslot-ai-service
```

---

## Issue 5 — HuggingFace Space shows "Missing configuration in README"

**Platform:** HuggingFace Spaces  
**Symptom:** After creating a Space, the Space page shows:
```
configuration error
Missing configuration in README
```
**Root cause:** HuggingFace Spaces require a specific YAML frontmatter block at the very top of `README.md` in the root of the git repository. If `README.md` is missing this block, or is not at the root, the Space cannot determine which SDK to use.  
**Fix:** Add the following YAML block as the very first thing in `README.md`:
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
```
**Important:** For Docker Spaces, the correct field is `app_port` (not `app_file`, which is for Gradio/Streamlit). Do NOT include `sdk_version` — that field is only for Gradio/Streamlit.  
**How to apply it reliably:** Edit `README.md` directly on the HuggingFace website (Space → Files → README.md → pencil icon) before doing any git push. Doing it in the browser guarantees the correct content is on the remote before your code arrives.

---

## Issue 6 — Push rejected: "fetch first" / divergent branches

**Platform:** HuggingFace git remote  
**Symptom:**
```
! [rejected] main -> main (fetch first)
```
or:
```
fatal: Need to specify how to reconcile divergent branches.
```
**Root cause:** HuggingFace creates an initial commit when you create a Space (containing the default README). Your local repo was initialized independently with `git init`, so it has no common history with the HuggingFace remote — the branches are "unrelated".  
**Fix (Option A — pull then push):**
```bash
git pull huggingface main --allow-unrelated-histories --no-rebase
git push huggingface main
```
**Fix (Option B — force push, simpler):**
```bash
git push huggingface main --force
```
Option B is safe here because you want your code to replace the HuggingFace default commit entirely.

---

## Issue 7 — README frontmatter present locally but HuggingFace still shows config error

**Platform:** HuggingFace Spaces  
**Symptom:** Local `README.md` has the correct `---` frontmatter. Push succeeds. But HuggingFace still shows "Missing configuration in README".  
**Root cause:** The user was pushing from the **monorepo root directory**, not from inside `bookmyslot-ai-service/`. HuggingFace reads `README.md` from the root of the git repository being pushed. When pushing the monorepo, `README.md` (with frontmatter) is at `bookmyslot-ai-service/README.md` — a subdirectory — not at the repo root. HuggingFace never sees it.  
**Fix:** Navigate **into** `bookmyslot-ai-service/` and create a standalone git repo there before pushing:
```bash
cd bookmyslot-ai-service
git init
git add .
git commit -m "Initial deployment"
git remote add huggingface https://USERNAME:TOKEN@huggingface.co/spaces/USERNAME/bookmyslot-ai-service
git push huggingface main --force
```
When pushing from inside `bookmyslot-ai-service/`, the `README.md` is at the root of that git repo, and HuggingFace finds it correctly.

---

## Issue 8 — Docker build fails: `libgl1-mesa-glx` not found

**Platform:** HuggingFace Spaces Docker build  
**Symptom:** Build log shows:
```
E: Package 'libgl1-mesa-glx' has no installation candidate
```
**Root cause:** `libgl1-mesa-glx` was renamed/replaced in Debian Bookworm (Debian 12), which is the base for `python:3.11-slim`. The package is now split — the OpenGL library is in `libgl1` directly.  
**Fix:** Replace `libgl1-mesa-glx` with `libgl1` in the Dockerfile. Also add `libgomp1` which is required by PyTorch for OpenMP multithreading:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
```

---

## Quick reference — what to do when things go wrong

| Error message | Go to |
|---|---|
| `replit-git-askpass` / `expected 'acknowledgments'` | Issue 3 — push from local machine |
| `No such remote 'huggingface'` | Issue 4 — use `git remote add` not `set-url` |
| `Missing configuration in README` | Issue 5 — edit README in browser, Issue 7 — push from inside subfolder |
| `fetch first` / `divergent branches` | Issue 6 — use `--force` push |
| `libgl1-mesa-glx has no installation candidate` | Issue 8 — use `libgl1` instead |
| OOM / memory kill on Render | Issue 1 — use CPU-only PyTorch or migrate to HuggingFace |
