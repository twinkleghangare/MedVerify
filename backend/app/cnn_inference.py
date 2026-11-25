"""
Loads the two trained CNN models produced in Colab and exposes inference
functions for the API layer:

  - Autoencoder  -> anomaly detection (trained on genuine images only)
  - Classifier   -> binary genuine/counterfeit CNN (MobileNetV2, trained on
                    genuine + synthetic-corrupted images — demo-grade only,
                    see README for the caveat on this model)

Everything here is optional and defensive by design:
  - If TensorFlow itself isn't installed, the whole module degrades to
    "models not available" instead of taking the API down. This matters
    because the text/OCR verification endpoints have nothing to do with
    TensorFlow and should keep working even on a machine that never
    installed it.
  - If the .keras files aren't present yet (e.g. still training in Colab),
    the corresponding function returns a clear "model not available"
    result instead of crashing.
  - If inference itself throws (corrupt image slipping through, OOM, etc.)
    the error is caught and turned into a clear result instead of a 500.
"""
import logging
import os

import numpy as np
from PIL import Image

from app import config

logger = logging.getLogger("medverify.cnn")

_autoencoder = None
_classifier = None
_anomaly_threshold = None
_tf_available = False


def _load_tf():
    """Import TensorFlow lazily so the rest of the API can run without it installed
    if you only need the text/OCR verification endpoints."""
    import tensorflow as tf  # noqa: F401
    return tf


def load_models():
    """Call once at startup. Never raises — any failure here (TensorFlow not
    installed, model files missing/corrupt, etc.) degrades to the relevant
    check reporting "not available" rather than taking the whole API down."""
    global _autoencoder, _classifier, _anomaly_threshold, _tf_available

    try:
        tf = _load_tf()
        _tf_available = True
    except ImportError as e:
        logger.warning(
            "TensorFlow not installed — anomaly & classifier checks disabled "
            "(text/OCR verification is unaffected): %s", e
        )
        return
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Unexpected error importing TensorFlow: %s", e)
        return

    try:
        if os.path.exists(config.AUTOENCODER_MODEL_PATH):
            _autoencoder = tf.keras.models.load_model(config.AUTOENCODER_MODEL_PATH)
            logger.info("Loaded autoencoder from %s", config.AUTOENCODER_MODEL_PATH)
        else:
            logger.warning(
                "Autoencoder model not found at %s — anomaly checks disabled",
                config.AUTOENCODER_MODEL_PATH,
            )
    except Exception as e:
        logger.error("Failed to load autoencoder model: %s", e)
        _autoencoder = None

    try:
        if os.path.exists(config.ANOMALY_THRESHOLD_PATH):
            with open(config.ANOMALY_THRESHOLD_PATH) as f:
                _anomaly_threshold = float(f.read().strip())
            logger.info("Loaded anomaly threshold: %s", _anomaly_threshold)
    except (OSError, ValueError) as e:
        logger.error("Failed to load anomaly threshold: %s", e)
        _anomaly_threshold = None

    try:
        if os.path.exists(config.CLASSIFIER_MODEL_PATH):
            _classifier = tf.keras.models.load_model(config.CLASSIFIER_MODEL_PATH)
            logger.info("Loaded classifier from %s", config.CLASSIFIER_MODEL_PATH)
        else:
            logger.warning(
                "Classifier model not found at %s — synthetic classifier checks disabled",
                config.CLASSIFIER_MODEL_PATH,
            )
    except Exception as e:
        logger.error("Failed to load classifier model: %s", e)
        _classifier = None


def models_status() -> dict:
    """Used by /health so callers can see what's actually active."""
    return {
        "tensorflow_available": _tf_available,
        "autoencoder_loaded": _autoencoder is not None and _anomaly_threshold is not None,
        "classifier_loaded": _classifier is not None,
    }


def check_anomaly(image_path: str) -> dict:
    """Reconstruction-error based anomaly check using the autoencoder."""
    if _autoencoder is None or _anomaly_threshold is None:
        return {"available": False, "reason": "Autoencoder model not loaded"}

    try:
        size = config.AUTOENCODER_IMG_SIZE
        im = Image.open(image_path).convert("RGB").resize((size, size))
        arr = np.expand_dims(np.array(im) / 255.0, 0)

        recon = _autoencoder.predict(arr, verbose=0)
        err = float(np.mean((arr - recon) ** 2))

        return {
            "available": True,
            "reconstruction_error": err,
            "threshold": _anomaly_threshold,
            "status": "SUSPICIOUS" if err > _anomaly_threshold else "LOOKS_GENUINE",
        }
    except Exception as e:
        logger.error("Anomaly check failed for %s: %s", os.path.basename(image_path), e)
        return {"available": False, "reason": "Anomaly check failed on this image"}


def classify_image(image_path: str) -> dict:
    """Binary genuine/counterfeit prediction from the MobileNetV2 classifier.

    NOTE: this model was trained on synthetically corrupted images standing in
    for 'counterfeit' (blur/noise/color-shift/warp), not real counterfeit
    packaging. Treat its output as a demo signal, not a reliable real-world
    counterfeit detector, until trained on real counterfeit photos.
    """
    if _classifier is None:
        return {"available": False, "reason": "Classifier model not loaded"}

    try:
        size = config.CLASSIFIER_IMG_SIZE
        im = Image.open(image_path).convert("RGB").resize(size)
        arr = np.expand_dims(np.array(im) / 255.0, 0)

        pred = float(_classifier.predict(arr, verbose=0)[0][0])
        # class_indices from training: {'counterfeit': 0, 'genuine': 1} (alphabetical)
        label = "GENUINE" if pred >= 0.5 else "COUNTERFEIT"

        return {
            "available": True,
            "raw_score": pred,
            "status": label,
            "note": "Trained on synthetic counterfeit images — demo signal only, not proof",
        }
    except Exception as e:
        logger.error("Classifier check failed for %s: %s", os.path.basename(image_path), e)
        return {"available": False, "reason": "Classifier check failed on this image"}
