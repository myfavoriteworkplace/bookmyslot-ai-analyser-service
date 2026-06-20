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


def validate_xray_image(image_path: str) -> tuple[bool, str]:
    """
    Heuristic pre-screen: is this image plausibly a dental X-ray?

    Returns (is_valid, error_message).
    If the validation itself errors for any reason, returns (True, "") so
    legitimate requests are never silently blocked.

    Two checks:
    1. Colour/saturation check — X-rays are near-monochrome; colour photos
       have high per-pixel RGB divergence.
    2. Contrast check — X-rays have a wide, high-variance intensity range;
       solid-colour, near-white, or near-black images are rejected.
    """
    try:
        from PIL import Image

        img = Image.open(image_path).convert("RGB")

        # --- 1. Grayscale / colour check ---
        # Downsample to 64×64 for speed; enough for a statistical check.
        small = img.resize((64, 64), Image.BILINEAR)
        pixels = list(small.getdata())  # list of (R, G, B) tuples

        mean_saturation = sum(max(r, g, b) - min(r, g, b) for r, g, b in pixels) / len(pixels)

        # X-rays are near-monochrome (saturation ≈ 0–15).
        # Colour photos typically score 40–120+.
        if mean_saturation > 30:
            return False, (
                "This image appears to be a colour photograph, not an X-ray. "
                "Please upload a genuine grayscale dental X-ray image."
            )

        # --- 2. Contrast / intensity distribution check ---
        gray = img.convert("L").resize((128, 128), Image.BILINEAR)
        pxs = list(gray.getdata())

        intensity_range = max(pxs) - min(pxs)
        mean_val = sum(pxs) / len(pxs)
        std_dev = (sum((p - mean_val) ** 2 for p in pxs) / len(pxs)) ** 0.5

        # Reject flat/near-blank images: solid colour, near-white, near-black.
        if intensity_range < 60 or std_dev < 15:
            return False, (
                "This image has insufficient contrast to be a valid X-ray. "
                "Please upload a genuine dental X-ray image."
            )

        return True, ""

    except Exception:
        # Never block a request due to a validation bug.
        return True, ""


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
