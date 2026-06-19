import io
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import AnalyseResponse, HealthResponse
from app import model as model_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Colour palette per class_id — distinct, readable on greyscale X-rays
_CLASS_COLOURS = {
    0: (255, 180, 0),    # Caries — amber
    1: (255, 80, 80),    # Deep Caries — red
    2: (80, 200, 120),   # Periapical Lesion — green
    3: (100, 180, 255),  # Impacted Tooth — blue
}
_DEFAULT_COLOUR = (220, 220, 220)

_startup_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_error
    try:
        logger.info("Pre-loading YOLO model at startup...")
        model_service.load_model()
        logger.info("Model ready.")
    except Exception as exc:
        _startup_error = str(exc)
        logger.error("STARTUP ERROR — model failed to load: %s", exc)
    yield


app = FastAPI(title="BookMySlot AI Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/test", response_class=HTMLResponse)
def test_ui():
    html = (_STATIC_DIR / "test.html").read_text()
    return HTMLResponse(content=html)


@app.get("/", response_model=HealthResponse)
def health_check():
    if _startup_error:
        return HealthResponse(service="BookMySlot AI", status=f"error: {_startup_error}")
    return HealthResponse(service="BookMySlot AI", status="running")


async def _save_upload(file: UploadFile) -> tuple[Path, bytes]:
    """Save upload to a temp file; return (path, raw_bytes)."""
    suffix = Path(file.filename or "image").suffix or ".jpg"
    tmp_path = UPLOADS_DIR / f"{uuid.uuid4()}{suffix}"
    contents = await file.read()
    tmp_path.write_bytes(contents)
    return tmp_path, contents


def _annotate_image(image_bytes: bytes, findings: list) -> bytes:
    """Draw bounding boxes and labels onto the image; return PNG bytes."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    img_w, img_h = img.size

    try:
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:
        font_label = ImageFont.load_default()
        font_small = font_label

    for finding in findings:
        loc = finding["location"]
        colour = _CLASS_COLOURS.get(finding["class_id"], _DEFAULT_COLOUR)
        fill_colour = colour + (40,)   # semi-transparent fill

        cx, cy, w, h = loc["x"], loc["y"], loc["width"], loc["height"]
        x1 = max(0, cx - w / 2)
        y1 = max(0, cy - h / 2)
        x2 = min(img_w, cx + w / 2)
        y2 = min(img_h, cy + h / 2)

        draw.rectangle([x1, y1, x2, y2], outline=colour, fill=fill_colour, width=2)

        label_text = f"{finding['label']} ({finding['confidence']:.0f}%)"
        bbox = draw.textbbox((0, 0), label_text, font=font_label)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad = 3

        tag_x1 = x1
        tag_y1 = max(0, y1 - text_h - pad * 2)
        tag_x2 = x1 + text_w + pad * 2
        tag_y2 = y1

        draw.rectangle([tag_x1, tag_y1, tag_x2, tag_y2], fill=colour + (210,))
        draw.text((tag_x1 + pad, tag_y1 + pad), label_text, fill=(0, 0, 0), font=font_label)

    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out.read()


@app.post("/analyse-xray", response_model=AnalyseResponse)
async def analyse_xray(file: UploadFile = File(...)):
    if _startup_error:
        return AnalyseResponse(
            success=False,
            message=f"AI service unavailable: {_startup_error}",
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        return AnalyseResponse(
            success=False,
            message="Invalid X-ray image. Supported formats: JPEG, PNG, WebP, BMP.",
        )

    tmp_path, _ = await _save_upload(file)

    try:
        try:
            findings = model_service.run_inference(str(tmp_path))
        except FileNotFoundError as exc:
            logger.error("Model not found: %s", exc)
            detail = str(exc) if DEBUG else "model file not found"
            return AnalyseResponse(success=False, message=f"AI service unavailable: {detail}")
        except Exception as exc:
            logger.exception("Inference error: %s", exc)
            detail = str(exc) if DEBUG else "inference failed"
            return AnalyseResponse(success=False, message=f"AI service unavailable: {detail}")

        return AnalyseResponse(
            success=True,
            analysis={"findings": findings},
        )

    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/analyse-xray/annotated")
async def analyse_xray_annotated(file: UploadFile = File(...)):
    """
    Same as /analyse-xray but returns the original image with bounding boxes
    and labels drawn on it as a PNG, useful for visual verification.
    """
    if _startup_error:
        return AnalyseResponse(
            success=False,
            message=f"AI service unavailable: {_startup_error}",
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        return AnalyseResponse(
            success=False,
            message="Invalid X-ray image. Supported formats: JPEG, PNG, WebP, BMP.",
        )

    tmp_path, raw_bytes = await _save_upload(file)

    try:
        try:
            findings = model_service.run_inference(str(tmp_path))
        except FileNotFoundError as exc:
            logger.error("Model not found: %s", exc)
            detail = str(exc) if DEBUG else "model file not found"
            return AnalyseResponse(success=False, message=f"AI service unavailable: {detail}")
        except Exception as exc:
            logger.exception("Inference error: %s", exc)
            detail = str(exc) if DEBUG else "inference failed"
            return AnalyseResponse(success=False, message=f"AI service unavailable: {detail}")

        annotated_png = _annotate_image(raw_bytes, findings)

        return StreamingResponse(
            io.BytesIO(annotated_png),
            media_type="image/png",
            headers={
                "X-Finding-Count": str(len(findings)),
                "Content-Disposition": "inline; filename=annotated.png",
            },
        )

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
