import os
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "models/best.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.25"))
MODEL_DOWNLOAD_URL = os.getenv("MODEL_DOWNLOAD_URL", "")

CLASS_MAPPING = {
    0: "Finding Type 1",
    1: "Finding Type 2",
    2: "Finding Type 3",
    3: "Finding Type 4",
}

_model = None


def _download_model(model_path: Path) -> None:
    if not MODEL_DOWNLOAD_URL:
        raise FileNotFoundError(
            f"Model not found at '{model_path}' and MODEL_DOWNLOAD_URL is not set. "
            "Either place best.pt in the models/ directory or set MODEL_DOWNLOAD_URL "
            "to a Google Drive shareable link."
        )

    logger.info("Model not found locally. Downloading from Google Drive...")
    model_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import gdown
        gdown.download(MODEL_DOWNLOAD_URL, str(model_path), quiet=False, fuzzy=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to download model from Google Drive: {exc}") from exc

    if not model_path.exists():
        raise RuntimeError(
            "Download appeared to succeed but model file was not found. "
            "Check that MODEL_DOWNLOAD_URL is a valid Google Drive link with public access."
        )

    logger.info("Model downloaded successfully to %s", model_path)


def load_model():
    global _model
    if _model is not None:
        return _model

    model_path = Path(MODEL_PATH)

    if not model_path.exists():
        _download_model(model_path)

    from ultralytics import YOLO

    logger.info("Loading YOLO model from %s", model_path)
    _model = YOLO(str(model_path))
    logger.info("Model loaded successfully")
    return _model


def run_inference(image_path: str) -> List[dict]:
    model = load_model()

    results = model.predict(
        source=image_path,
        conf=CONFIDENCE_THRESHOLD,
        verbose=False,
    )

    findings = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for box in boxes:
            class_id = int(box.cls[0].item())
            confidence = round(float(box.conf[0].item()) * 100, 1)

            x, y, w, h = box.xywh[0].tolist()

            findings.append(
                {
                    "class_id": class_id,
                    "label": CLASS_MAPPING.get(class_id, f"Finding Type {class_id + 1}"),
                    "confidence": confidence,
                    "location": {
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "width": round(w, 2),
                        "height": round(h, 2),
                    },
                }
            )

    return findings
