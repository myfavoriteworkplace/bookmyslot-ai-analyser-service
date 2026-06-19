import os
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "models/best.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))
NMS_IOU_THRESHOLD = float(os.getenv("NMS_IOU_THRESHOLD", "0.30"))
MAX_DETECTIONS = int(os.getenv("MAX_DETECTIONS", "30"))
CROSS_CLASS_IOU_THRESHOLD = float(os.getenv("CROSS_CLASS_IOU_THRESHOLD", "0.50"))
MODEL_DOWNLOAD_URL = os.getenv("MODEL_DOWNLOAD_URL", "")

MIN_MODEL_SIZE_BYTES = 1 * 1024 * 1024

# DENTEX dataset category_id_1 → dental disease name
CLASS_MAPPING = {
    0: "Caries",
    1: "Deep Caries",
    2: "Periapical Lesion",
    3: "Impacted Tooth",
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
            "Check that MODEL_DOWNLOAD_URL points to a valid, publicly shared Google Drive file."
        )

    actual_size = model_path.stat().st_size
    if actual_size < MIN_MODEL_SIZE_BYTES:
        model_path.unlink()
        raise RuntimeError(
            f"Downloaded file is only {actual_size} bytes — this is not a valid model file. "
            "Google Drive may have returned an HTML error page. "
            "Make sure the file is shared as 'Anyone with the link' (Viewer)."
        )

    logger.info("Model downloaded successfully (%.1f MB)", actual_size / 1024 / 1024)


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


def _iou(box_a: dict, box_b: dict) -> float:
    """Compute IoU between two xywh-centre boxes."""
    ax1 = box_a["x"] - box_a["width"] / 2
    ay1 = box_a["y"] - box_a["height"] / 2
    ax2 = box_a["x"] + box_a["width"] / 2
    ay2 = box_a["y"] + box_a["height"] / 2

    bx1 = box_b["x"] - box_b["width"] / 2
    by1 = box_b["y"] - box_b["height"] / 2
    bx2 = box_b["x"] + box_b["width"] / 2
    by2 = box_b["y"] + box_b["height"] / 2

    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h

    area_a = box_a["width"] * box_a["height"]
    area_b = box_b["width"] * box_b["height"]
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0


def _cross_class_nms(findings: List[dict], iou_threshold: float) -> List[dict]:
    """
    Suppress overlapping boxes across different classes.
    Findings must be sorted by confidence descending before calling.
    For any two boxes whose IoU exceeds iou_threshold, the lower-confidence
    one is dropped regardless of class.
    """
    kept = []
    suppressed = set()

    for i, candidate in enumerate(findings):
        if i in suppressed:
            continue
        kept.append(candidate)
        for j in range(i + 1, len(findings)):
            if j in suppressed:
                continue
            if _iou(candidate["location"], findings[j]["location"]) > iou_threshold:
                suppressed.add(j)

    return kept


def run_inference(image_path: str) -> List[dict]:
    model = load_model()

    results = model.predict(
        source=image_path,
        conf=CONFIDENCE_THRESHOLD,
        iou=NMS_IOU_THRESHOLD,
        max_det=MAX_DETECTIONS,
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
                    "label": CLASS_MAPPING.get(class_id, f"Unknown ({class_id})"),
                    "confidence": confidence,
                    "location": {
                        "x": round(x, 2),
                        "y": round(y, 2),
                        "width": round(w, 2),
                        "height": round(h, 2),
                    },
                }
            )

    findings.sort(key=lambda f: f["confidence"], reverse=True)
    findings = _cross_class_nms(findings, CROSS_CLASS_IOU_THRESHOLD)

    return findings
