"""
MedVerify backend API.

Endpoints:
  GET  /health                 -> liveness + dependency status check
  POST /verify/text            -> verify by medicine name (+ optional company)
  POST /verify/image           -> full pipeline: QR/OCR + database + CNN checks

Run locally:
  uvicorn app.main:app --reload --port 8000

Then e.g.:
  curl -X POST http://localhost:8000/verify/text \
       -H "Content-Type: application/json" \
       -d '{"medicine_name": "Dolo 650"}'
"""
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app import config, cnn_inference, groq_assist
from app.database import DatabaseLoadError, db
from app.matching import verify_medicine
from app.ocr_pipeline import medverify_text_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medverify.main")

# --------------------------------------------------------------------------
# Optional rate limiting. slowapi is a small free/open-source wrapper around
# an in-memory token bucket; if it isn't installed, the app still runs, it
# just doesn't rate-limit (a warning is logged so this isn't silent).
# --------------------------------------------------------------------------
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMITING_ENABLED = True
except ImportError:
    limiter = None
    RATE_LIMITING_ENABLED = False
    logger.warning("slowapi not installed — API rate limiting is DISABLED. `pip install slowapi` to enable it.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db.load()
    except DatabaseLoadError as e:
        # Don't take the whole API down over a data file problem: log it loudly,
        # keep the server up, and let /health + verify endpoints report the
        # real "database not loaded" state to callers instead of the process
        # refusing to start at all.
        logger.critical("MedVerify database failed to load: %s", e)

    cnn_inference.load_models()
    yield


app = FastAPI(title="MedVerify API", version="1.1.0", lifespan=lifespan)

if RATE_LIMITING_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow the frontend to call this API from a different origin.
# MEDVERIFY_CORS_ORIGINS defaults to "*" for local development. Set it to your
# real deployed frontend origin(s) in production (see .env.example) — this API
# doesn't use cookies/credentials, so "*" is not a data-leak risk here, but it
# is still best practice to scope it down once you have a real frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Centralized error handling: never leak stack traces / internals to callers.
# --------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status": "INVALID_INPUT", "reason": "Request validation failed", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"status": "ERROR", "reason": "An internal error occurred. Please try again."},
    )


class TextVerifyRequest(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=config.MAX_TEXT_FIELD_LEN)
    company_name: Optional[str] = Field(None, max_length=config.MAX_TEXT_FIELD_LEN)
    batch_number: Optional[str] = Field(None, max_length=config.MAX_TEXT_FIELD_LEN)
    expiry_date: Optional[str] = Field(None, max_length=config.MAX_TEXT_FIELD_LEN)


class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=groq_assist.MAX_QUESTION_LEN)


class ChatRequest(BaseModel):
    # The verification result dict the frontend already has from a prior
    # /verify/text or /verify/image call — used to ground the chat's answers
    # in real data instead of letting the model invent facts about the medicine.
    context: dict
    question: str = Field(..., min_length=1, max_length=groq_assist.MAX_QUESTION_LEN)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


@app.get("/")
def index():
    frontend_path = os.path.join(os.path.dirname(config.BASE_DIR), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"status": "ok", "message": "MedVerify API is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_loaded": db.loaded,
        "models": cnn_inference.models_status(),
        "qr_ocr": _scanning_status(),
        "rate_limiting_enabled": RATE_LIMITING_ENABLED,
        "ai_explanation_available": groq_assist.is_available(),
    }


def _scanning_status():
    from app import ocr_pipeline
    return {
        "qr_available": ocr_pipeline.QR_AVAILABLE,
        "ocr_available": ocr_pipeline.OCR_AVAILABLE,
        "rapid_ocr_available": getattr(ocr_pipeline, "RAPID_OCR_AVAILABLE", False),
        "tesseract_cmd_override": config.TESSERACT_CMD,
    }


def _apply_rate_limit(limit_str: str):
    """Returns a decorator that applies the given limit if slowapi is available,
    otherwise a no-op decorator."""
    if RATE_LIMITING_ENABLED:
        return limiter.limit(limit_str)
    return lambda func: func


@app.post("/verify/text")
@_apply_rate_limit(config.RATE_LIMIT_TEXT)
def verify_text(request: Request, payload: TextVerifyRequest, explain: bool = False):
    """Verify a medicine purely by name (and optional company), no image involved.

    ?explain=true adds an optional plain-language AI explanation of the
    result (see groq_assist.py) — off by default so the core verification
    response stays fast and doesn't depend on a third-party API being up.
    """
    result = verify_medicine(
        payload.medicine_name,
        company_name=payload.company_name,
        batch_number=payload.batch_number,
        expiry_date=payload.expiry_date,
    )
    if explain:
        result["ai_explanation"] = groq_assist.explain_result(result)
    return result


def _sanitized_extension(filename: Optional[str], content_type: Optional[str] = None) -> Optional[str]:
    if filename:
        raw_ext = os.path.splitext(filename)[1].lower()
        if raw_ext:
            return raw_ext if raw_ext in config.ALLOWED_IMAGE_EXTENSIONS else None
    # If no explicit extension was given (e.g. "blob" or direct frame capture), infer from content-type
    ct_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/pjpeg": ".jpg",
        "image/png": ".png",
        "image/x-png": ".png",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/x-ms-bmp": ".bmp",
    }
    if content_type and content_type.lower() in ct_map:
        return ct_map[content_type.lower()]
    return None


@app.post("/verify/image")
@_apply_rate_limit(config.RATE_LIMIT_IMAGE)
async def verify_image(request: Request, file: UploadFile = File(...), explain: bool = False):
    """
    Full pipeline for an uploaded medicine package photo:
      1. QR/Barcode decode -> DB lookup, OR OCR -> fuzzy match -> DB lookup
      2. Autoencoder anomaly check (packaging looks statistically normal or not)
      3. Synthetic classifier check (demo signal, see cnn_inference.py note)

    ?explain=true adds an optional plain-language AI explanation of the
    database_verification result (see groq_assist.py) — off by default.
    """
    ct = (file.content_type or "").lower().strip()
    ext = _sanitized_extension(file.filename, ct)

    if ct and ct not in config.ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {file.content_type}")

    if ext is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension. Allowed: {sorted(config.ALLOWED_IMAGE_EXTENSIONS)}",
        )

    temp_path = os.path.join(config.UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")

    # --- Enforce a max upload size by streaming in chunks rather than trusting
    #     a Content-Length header (which can be absent or spoofed) or reading
    #     the whole body into memory unbounded. ---
    bytes_written = 0
    chunk_size = 1024 * 1024
    try:
        with open(temp_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max size is {config.MAX_UPLOAD_MB} MB.",
                    )
                f.write(chunk)
    except HTTPException:
        _safe_remove(temp_path)
        raise
    except OSError as e:
        _safe_remove(temp_path)
        logger.error("Failed writing upload to disk: %s", e)
        raise HTTPException(status_code=500, detail="Could not store the uploaded file")
    finally:
        await file.close()

    if bytes_written == 0:
        _safe_remove(temp_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        # These are all synchronous, CPU-bound calls (Tesseract OCR, OpenCV
        # preprocessing, pandas/fuzzy-match lookups) — running them directly
        # in this async handler blocks the whole event loop until they
        # finish. Confirmed as a real production issue: on a single-worker
        # deployment, this made the *entire* backend stop responding to
        # every request (even /health) for the full duration of one image
        # scan, which looked to the platform like a hung/dead process and
        # got the worker killed and restarted. Running them in a thread
        # pool keeps the event loop free to keep serving other requests
        # (including /health) while this one grinds through OCR.
        text_result = await run_in_threadpool(medverify_text_pipeline, temp_path)
        anomaly_result = await run_in_threadpool(cnn_inference.check_anomaly, temp_path)
        classifier_result = await run_in_threadpool(cnn_inference.classify_image, temp_path)

        if explain:
            text_result["ai_explanation"] = await run_in_threadpool(groq_assist.explain_result, text_result)

        return {
            "database_verification": text_result,
            "anomaly_check": anomaly_result,
            "synthetic_classifier": classifier_result,
        }
    finally:
        _safe_remove(temp_path)


@app.post("/chat")
@_apply_rate_limit(config.RATE_LIMIT_TEXT)
def chat(request: Request, payload: ChatRequest):
    """
    Free-form Q&A about a medicine the user already verified — "what is this
    for", "what are common side effects", etc. Grounded in the real
    verification result (payload.context) the frontend already has; this
    endpoint never re-decides GENUINE/COUNTERFEIT/UNVERIFIED/NOT_FOUND
    itself (see groq_assist.chat_about_medicine's system prompt).

    Gracefully returns {"available": false, "reason": "..."} — never an
    error — if Groq isn't configured, times out, or errors.
    """
    history = [{"role": t.role, "content": t.content} for t in payload.history]
    return groq_assist.chat_about_medicine(payload.context, payload.question, history)


def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:  # pragma: no cover - defensive
        logger.warning("Could not remove temp file %s: %s", path, e)
