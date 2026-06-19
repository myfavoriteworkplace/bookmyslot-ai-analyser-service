"""
Run during Render build to pre-download best.pt into the image.
This eliminates model download time on every cold start.

Render build command:
  pip install -r requirements.txt && python download_model.py
"""
import os
import sys
from pathlib import Path

MODEL_PATH = os.getenv("MODEL_PATH", "models/best.pt")
MODEL_DOWNLOAD_URL = os.getenv("MODEL_DOWNLOAD_URL", "")
MIN_MODEL_SIZE_BYTES = 1 * 1024 * 1024

model_path = Path(MODEL_PATH)

if model_path.exists() and model_path.stat().st_size >= MIN_MODEL_SIZE_BYTES:
    print(f"Model already present at {model_path} ({model_path.stat().st_size / 1024 / 1024:.1f} MB) — skipping download.")
    sys.exit(0)

if not MODEL_DOWNLOAD_URL:
    print("MODEL_DOWNLOAD_URL not set — skipping build-time download.")
    print("Model will be downloaded at runtime on first startup.")
    sys.exit(0)

print(f"Downloading model from Google Drive to {model_path} ...")
model_path.parent.mkdir(parents=True, exist_ok=True)

try:
    import gdown
    gdown.download(MODEL_DOWNLOAD_URL, str(model_path), quiet=False, fuzzy=True)
except Exception as exc:
    print(f"WARNING: Build-time download failed: {exc}")
    print("Model will be downloaded at runtime on first startup instead.")
    sys.exit(0)

if not model_path.exists() or model_path.stat().st_size < MIN_MODEL_SIZE_BYTES:
    actual = model_path.stat().st_size if model_path.exists() else 0
    print(f"WARNING: Downloaded file is {actual} bytes — not a valid model.")
    print("Check MODEL_DOWNLOAD_URL is publicly shared on Google Drive.")
    if model_path.exists():
        model_path.unlink()
    sys.exit(0)

print(f"Model downloaded successfully ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")
