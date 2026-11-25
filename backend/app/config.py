"""
Central configuration for the MedVerify backend.
Adjust these paths to wherever you place the database files and trained models
after downloading them from Google Drive / Colab.

Anything that differs between environments (dev machine vs. a real deployment)
is read from environment variables, with safe defaults for local development.
Copy .env.example to .env and adjust it for your environment.
"""
import os

# Base directory of this project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------
# Database files (exported from your Colab dataset folder)
# ---------------------------------------------------------------
DATA_DIR = os.path.join(BASE_DIR, "data")

GENUINE_MEDICINES_PATH = os.path.join(DATA_DIR, "Real_Medicines_dataset.xlsx")
BANNED_COMPANIES_PATH = os.path.join(DATA_DIR, "Banned_Pharma_Companies.xlsx")
MEDICINE_DETAILS_PATH = os.path.join(DATA_DIR, "Medicine_Details.csv")

# ---------------------------------------------------------------
# Trained model files (exported from Colab after training)
# ---------------------------------------------------------------
MODELS_DIR = os.path.join(BASE_DIR, "app", "models", "weights")

AUTOENCODER_MODEL_PATH = os.path.join(MODELS_DIR, "medverify_autoencoder_final.keras")
ANOMALY_THRESHOLD_PATH = os.path.join(MODELS_DIR, "anomaly_threshold.txt")
CLASSIFIER_MODEL_PATH = os.path.join(MODELS_DIR, "medverify_classifier_final.keras")

# ---------------------------------------------------------------
# Image processing settings
# ---------------------------------------------------------------
AUTOENCODER_IMG_SIZE = 128
CLASSIFIER_IMG_SIZE = (224, 224)

# Fuzzy-match sensitivity (0-1, higher = stricter)
FUZZY_MATCH_CUTOFF = 0.6

# Temp upload directory for incoming images via the API
UPLOAD_DIR = os.path.join(BASE_DIR, "tmp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------------
# Security / API hardening (override via environment variables)
# ---------------------------------------------------------------

# Comma-separated list of allowed origins for the frontend.
# In production, set MEDVERIFY_CORS_ORIGINS to your real deployed frontend
# origin(s), e.g. "https://medverify.example.com". "*" is only safe for
# local development because this API has no cookies/credentials.
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("MEDVERIFY_CORS_ORIGINS", "*").split(",") if o.strip()
]

# Maximum accepted upload size, in megabytes.
MAX_UPLOAD_MB = float(os.environ.get("MEDVERIFY_MAX_UPLOAD_MB", "8"))
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)

# Only these extensions / content-types are accepted for uploaded images.
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/x-png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
    "application/octet-stream",
}

# Reject absurdly large pixel dimensions before decoding fully (decompression-bomb guard).
MAX_IMAGE_PIXELS = 40_000_000  # ~40MP

# Downscale any image larger than this (on the longest side) before OCR
# processing. Keeps memory/CPU cost bounded regardless of the original
# phone photo's resolution — see ocr_pipeline.py's load_image_any_format().
MAX_IMAGE_DIMENSION = int(os.environ.get("MEDVERIFY_MAX_IMAGE_DIMENSION", "1600"))

# Max length accepted for free-text fields (defense in depth; Pydantic also enforces this).
MAX_TEXT_FIELD_LEN = 200

# Simple in-process rate limit for the public endpoints (requires the optional
# slowapi dependency; if it's not installed, rate limiting is silently skipped
# rather than crashing the app — see main.py).
RATE_LIMIT_TEXT = os.environ.get("MEDVERIFY_RATE_LIMIT_TEXT", "30/minute")
RATE_LIMIT_IMAGE = os.environ.get("MEDVERIFY_RATE_LIMIT_IMAGE", "10/minute")

# Set to "production" to disable verbose/debug behaviors.
ENVIRONMENT = os.environ.get("MEDVERIFY_ENV", "development")

# Explicit path to the tesseract.exe / tesseract binary. Optional — leave unset
# to rely on Tesseract being on the system PATH. Set this if OCR reports
# "tesseract is not installed or it's not in your PATH" even after installing
# it (very common on Windows when the installer doesn't update PATH, or a
# terminal window was opened before PATH was updated). Example:
#   MEDVERIFY_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_CMD = os.environ.get("MEDVERIFY_TESSERACT_CMD", "").strip() or None

# ---------------------------------------------------------------
# Optional AI explanation layer (Groq — free API, fast open-source models)
# ---------------------------------------------------------------
# Get a free key at https://console.groq.com/keys — no credit card needed.
# Leave unset and this feature simply stays "not available"; nothing else
# in the app depends on it (core verification never uses an LLM to decide
# GENUINE/COUNTERFEIT — only to explain a decision already made by the
# real database/OCR/QR logic).
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip() or None
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_TIMEOUT_SECONDS = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "8"))
