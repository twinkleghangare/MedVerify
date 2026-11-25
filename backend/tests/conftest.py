import io
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def load_database_once():
    """Load the real backend/data databases once for the whole test session."""
    if not db.loaded:
        db.load()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="white").save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def qr_medicine_png_bytes():
    """A QR code image encoding the name of a medicine known to be in the
    genuine-medicines dataset, so the full QR->DB pipeline can be exercised."""
    qrcode = pytest.importorskip("qrcode")
    known_name = db.genuine_names_list[0] if db.genuine_names_list else "okacet"
    img = qrcode.make(known_name)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read(), known_name
