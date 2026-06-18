import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import AnalyseResponse, HealthResponse
from app import model as model_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="BookMySlot AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
def health_check():
    return HealthResponse(service="BookMySlot AI", status="running")


@app.post("/analyse-xray", response_model=AnalyseResponse)
async def analyse_xray(file: UploadFile = File(...)):
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        return AnalyseResponse(
            success=False,
            message="Invalid X-ray image. Supported formats: JPEG, PNG, WebP, BMP.",
        )

    tmp_path = UPLOADS_DIR / f"{uuid.uuid4()}{Path(file.filename or 'image').suffix}"

    try:
        contents = await file.read()
        if len(contents) == 0:
            return AnalyseResponse(success=False, message="Uploaded file is empty.")

        tmp_path.write_bytes(contents)

        try:
            findings = model_service.run_inference(str(tmp_path))
        except FileNotFoundError as exc:
            logger.error("Model not found: %s", exc)
            return AnalyseResponse(success=False, message="AI service unavailable: model not loaded.")
        except Exception as exc:
            logger.exception("Inference error: %s", exc)
            return AnalyseResponse(success=False, message="AI service unavailable.")

        return AnalyseResponse(
            success=True,
            analysis={"findings": findings},
        )

    finally:
        if tmp_path.exists():
            tmp_path.unlink()
