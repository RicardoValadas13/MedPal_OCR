import base64
import binascii

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from openai import OpenAI

from .config import get_settings
from .models import Base64ImageRequest, PrescriptionResponse
from .services.ocr import extract_prescription

app = FastAPI(title="MedPal Prescription OCR", version="0.1.0")

_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured. Set it in your .env file.",
        )
    return OpenAI(api_key=settings.openai_api_key)


def _validate_image(image_bytes: bytes, mime_type: str) -> None:
    settings = get_settings()
    if mime_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{mime_type}'. Allowed: {sorted(_ALLOWED_MIME)}.",
        )
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image.")
    if len(image_bytes) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="Image too large.")


def _run(image_bytes: bytes, mime_type: str) -> PrescriptionResponse:
    _validate_image(image_bytes, mime_type)
    try:
        return extract_prescription(_client(), image_bytes, mime_type)
    except HTTPException:
        raise
    except Exception as exc:  # surface model / parsing failures to the caller
        raise HTTPException(status_code=502, detail=f"OCR failed: {exc}") from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/prescriptions", response_model=PrescriptionResponse)
async def read_prescription(file: UploadFile = File(...)):
    """Read a prescription from a multipart image upload and return structured JSON."""
    image_bytes = await file.read()
    return _run(image_bytes, file.content_type or "image/jpeg")


@app.post("/v1/prescriptions:base64", response_model=PrescriptionResponse)
def read_prescription_base64(req: Base64ImageRequest):
    """Read a prescription from a base64-encoded image (backend-to-backend calls)."""
    try:
        image_bytes = base64.b64decode(req.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {exc}") from exc
    return _run(image_bytes, req.mime_type)
