"""
Image -> text pipeline: tries QR/Barcode decoding first, falls back to OCR,
then fuzzy-matches the extracted text against the genuine medicines list.
"""
import logging
import os
import re

from PIL import Image, ImageOps, UnidentifiedImageError

from app import config
from app.database import db
from app.matching import verify_medicine

logger = logging.getLogger("medverify.ocr")

# Guard against decompression-bomb style images (huge declared pixel counts
# that are cheap to *store* but expensive/dangerous to decode into memory).
Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS

# cv2, pytesseract, and pyzbar all depend on system-level libraries
# (Tesseract-OCR binary, ZBar shared library) that may not be installed,
# especially on a fresh Windows setup. Importing them at module load time
# would crash the whole API on startup if either is missing. Instead we
# import them lazily/defensively here so the app still starts — QR and OCR
# scanning just report as unavailable instead of taking the server down.
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError as e:
    logger.warning("OpenCV (cv2) not available — image loading via cv2 disabled: %s", e)
    cv2 = None
    CV2_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
    if config.TESSERACT_CMD:
        # Bypasses PATH entirely — set MEDVERIFY_TESSERACT_CMD in .env if
        # Tesseract is installed but not being found on PATH (common on
        # Windows right after installing it, before opening a fresh terminal).
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        logger.info("Using explicit Tesseract path from MEDVERIFY_TESSERACT_CMD: %s", config.TESSERACT_CMD)
except ImportError as e:
    logger.warning("pytesseract not available: %s", e)
    pytesseract = None
    PYTESSERACT_AVAILABLE = False

try:
    from rapidocr_onnxruntime import RapidOCR
    _rapid_ocr = RapidOCR()
    RAPID_OCR_AVAILABLE = True
    logger.info("RapidOCR (onnxruntime) initialized successfully as primary OCR engine")
except Exception as e:
    logger.warning("RapidOCR not available: %s", e)
    _rapid_ocr = None
    RAPID_OCR_AVAILABLE = False

OCR_AVAILABLE = RAPID_OCR_AVAILABLE or PYTESSERACT_AVAILABLE

try:
    from pyzbar.pyzbar import decode
    QR_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning(
        "pyzbar not available (ZBar shared library missing) — QR/barcode scanning disabled: %s", e
    )
    decode = None
    QR_AVAILABLE = False


def load_image_any_format(path: str):
    """Returns (img_cv, pil_img) for backward compatibility with callers'
    tuple-unpacking, but img_cv is always None now — a full-resolution
    duplicate load via cv2.imread() used to happen here and was pure wasted
    memory, since no caller ever used the img_cv return value (confirmed:
    every caller does `_, pil_img = load_image_any_format(...)`). Removing
    it, combined with downscaling pil_img below, meaningfully reduces peak
    memory use on a real phone photo — likely the cause of a real production
    crash (502s) on a memory-constrained deployment.
    pil_img is None (never raises) if the file isn't a valid/decodable
    image — callers must handle that case."""
    try:
        pil_img = Image.open(path)
        pil_img.verify()  # cheaply validate the file is a real, undamaged image
        pil_img = Image.open(path).convert("RGB")  # re-open: verify() consumes the file handle
        # Phone cameras write an EXIF orientation tag instead of physically
        # rotating pixel data; browsers/photo viewers apply it automatically,
        # but PIL and OpenCV do not. Without this, a photo that looks upright
        # to the user (and in the browser) can be loaded here sideways or
        # upside-down, and OCR on the misoriented pixels produces garbage.
        pil_img = ImageOps.exif_transpose(pil_img)
        # Downscale large phone photos before any processing. A modern phone
        # photo is often 3000-4000px+ per side; the multi-variant OCR pass
        # (grayscale + CLAHE + denoise + sharpen, see extract_text_ocr_robust)
        # holds several full-resolution copies in memory at once, and on a
        # memory-constrained deployment (e.g. a 512MB free-tier server) this
        # was confirmed to exhaust memory and crash the whole process on a
        # real phone photo — 1600px is comfortably enough resolution for OCR
        # and cuts memory/CPU cost by roughly 4x+ on a typical 3000px photo.
        max_dim = config.MAX_IMAGE_DIMENSION
        if max(pil_img.size) > max_dim:
            scale = max_dim / max(pil_img.size)
            new_size = (round(pil_img.width * scale), round(pil_img.height * scale))
            pil_img = pil_img.resize(new_size, Image.LANCZOS)
            logger.info("Downscaled image to %s for processing", new_size)
    except (UnidentifiedImageError, OSError, ValueError) as e:
        logger.warning("Could not decode image %s: %s", os.path.basename(path), e)
        return None, None

    return None, pil_img


def extract_text_ocr(pil_img: Image.Image) -> str:
    """Single-pass OCR on the image. Uses RapidOCR (deep learning ONNX) primarily,
    falling back to pytesseract if needed."""
    if not OCR_AVAILABLE:
        return ""

    # Primary: RapidOCR (zero system dependency, deep learning DBNet+CRNN)
    if RAPID_OCR_AVAILABLE and _rapid_ocr is not None:
        try:
            import numpy as np
            arr = np.array(pil_img.convert("RGB"))
            res, _ = _rapid_ocr(arr)
            if res:
                lines = [line[1] for line in res if line and len(line) > 1 and line[1]]
                text = " ".join(lines)
                if text.strip():
                    return text
        except Exception as e:
            logger.warning("RapidOCR extraction failed: %s", e)

    # Fallback: pytesseract (if binary is installed on system)
    if PYTESSERACT_AVAILABLE and pytesseract is not None:
        try:
            return pytesseract.image_to_string(pil_img) or ""
        except Exception as e:
            logger.warning("Pytesseract extraction failed: %s", e)

    return ""


def _preprocess_variants(pil_img: Image.Image):
    """Yields increasingly aggressive preprocessing attempts, in order of
    cost. Each is a real, standard technique for hard OCR inputs:

      - grayscale: cheap baseline, drops color-channel noise
      - CLAHE: adaptive local contrast — the single biggest win found during
        testing against glare on reflective blister foil
      - denoise + CLAHE + sharpen: slower, for the hardest inputs (small
        embossed/printed text on a curved metallic surface)

    Only used when the cheap pass in extract_text_ocr_robust() doesn't
    already produce a confident database match — clean, well-lit photos
    never pay this extra cost.
    """
    if not CV2_AVAILABLE:
        return  # no OpenCV -> can't build these variants; caller's fast path already ran

    import numpy as np
    arr = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    yield Image.fromarray(gray)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)
    yield Image.fromarray(clahe_img)

    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe_img2 = clahe.apply(denoised)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(clahe_img2, -1, kernel)
    yield Image.fromarray(sharp)


def extract_text_ocr_robust(pil_img: Image.Image):
    """Multi-attempt OCR for real-world photos (glare, reflective packaging,
    low light) where a single plain OCR pass often fails outright.

    Strategy: try the cheap unmodified pass first; if it already produces a
    confident medicine-name match, stop there (clean photos stay fast). Only
    if that fails does it escalate through progressively heavier
    preprocessing (see _preprocess_variants), stopping as soon as one
    variant produces a confident match, or falling back to whichever
    variant scored best if none does.

    Returns (best_text, all_text_combined) — best_text is what produced the
    winning match score (used for the medicine-name match), all_text_combined
    is the concatenation of everything tried (used for the banned-company
    scan, since that just needs the name to appear anywhere, not to "win").
    """
    first_pass = extract_text_ocr(pil_img)
    all_texts = [first_pass]

    _, first_score = smart_medicine_match(first_pass)
    if first_score >= 1000:  # exact phrase match — confident, stop here
        return first_pass, first_pass

    best_text, best_score = first_pass, first_score

    for variant in _preprocess_variants(pil_img):
        try:
            text = extract_text_ocr(variant)
        except Exception as e:
            logger.warning("OCR failed on a preprocessing variant: %s", e)
            continue
        if text:
            all_texts.append(text)
            _, score = smart_medicine_match(text)
            if score > best_score:
                best_text, best_score = text, score
            if score >= 1000:
                break  # confident match — no need to try heavier variants

    return best_text, "\n".join(all_texts) if all_texts else (best_text or "")


# Generic pharma/packaging vocabulary that appears on almost every medicine's
# label regardless of which medicine it is (dosage forms, units, common
# label words). These carry no identifying signal, so they're excluded from
# word-overlap scoring — without this, a database name like "Nimesulide
# Tablet 100 mg" can match purely because the word "tablet" appears
# somewhere on literally any tablet's packaging, producing a confident-looking
# but meaningless match. Confirmed as a real false positive during testing.
_GENERIC_LABEL_WORDS = {
    "tablet", "tablets", "capsule", "capsules", "syrup", "injection",
    "cream", "ointment", "drops", "gel", "lotion", "suspension",
    "mg", "ml", "mcg", "gm", "iu", "ip", "bp", "usp", "ltd", "pvt",
    "the", "and", "for", "with", "each", "film", "coated", "contains",
    "sustained", "release", "form", "extended", "plus", "forte",
}

# Common short English filler words that can appear as standalone OCR tokens
# (e.g. "...prescription of a..." contains "of" and "a" as real words) and
# would otherwise be miscounted as identifying evidence once matching
# considers 2-letter words. This list exists specifically so 2-letter
# *brand* codes — "RD", "SR", "XR", "DS", "CD", "LA" etc. are extremely
# common in Indian pharma naming (e.g. "Aciloc RD" is a distinct product
# from plain "Aciloc") — can still count as real distinguishing words
# without reopening the false-positive class the >=3-char rule was
# originally added to close.
_SHORT_STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "at", "is", "by", "or",
    "as", "it", "be", "if", "so", "no", "not", "and",
}


def smart_medicine_match(ocr_text: str, name_list=None):
    """Word-overlap scoring between noisy OCR text and known medicine names.

    Two-tier scoring:
      1. If the medicine's full name appears as a contiguous phrase in the OCR
         text (including hyphenated or unspaced variants like DOLO650), that's
         an unambiguous match — score it far above anything else.
      2. Otherwise, score by how many of the name's *whole, non-generic*
         words (>=2 chars, matched as real tokens, not substrings) appear in
         the OCR text — and require at least two such words (score >= 20)
         before accepting it as a match at all.
    """
    if not ocr_text:
        return None, 0

    if name_list is None:
        name_list = db.genuine_names_list

    # Separate letter-digit boundary for brand codes (e.g. DOLO650 -> DOLO 650)
    expanded = re.sub(r"([a-zA-Z]{3,})(\d+)", r"\1 \2", str(ocr_text))

    ocr_clean = re.sub(r"[^a-zA-Z0-9\s\-\+]", " ", expanded).lower()
    ocr_tokens = set(ocr_clean.split())

    best, best_score, tie_count = None, 0, 0
    for name in name_list:
        name_words = name.split()
        if name_words and all(w in _GENERIC_LABEL_WORDS for w in name_words):
            continue

        name_clean = name.lower()

        if len(name) >= 4 and (
            name_clean in ocr_clean
            or name_clean.replace(" ", "-") in ocr_clean
            or name_clean.replace("-", " ") in ocr_clean
        ):
            # Exact multi-character phrase match — strongest possible signal,
            # always wins over partial word-overlap scoring below.
            score = 1000 + len(name)
        else:
            matched_words = [
                w for w in name_words
                if len(w) >= 2 and w not in _GENERIC_LABEL_WORDS and w not in _SHORT_STOPWORDS and w in ocr_tokens
            ]
            score = len(matched_words) * 10 if len(matched_words) >= 2 else 0

        if score > best_score:
            best, best_score, tie_count = name, score, 1
        elif score == best_score and score > 0:
            tie_count += 1

    if best_score < 1000 and tie_count > 1:
        return None, 0

    return best, best_score


def _decode_qr(pil_img: Image.Image):
    """Returns decoded text from the first readable barcode/QR code, or None.
    If multiple codes are present, only the first is used — callers should
    not assume a single-code image."""
    if not QR_AVAILABLE:
        return None
    try:
        results = decode(pil_img)
    except Exception as e:
        logger.warning("QR/Barcode decode failed: %s", e)
        return None

    if not results:
        return None

    if len(results) > 1:
        logger.info("%d barcodes/QR codes found in image — using the first one", len(results))

    raw = results[0].data
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("QR/Barcode payload was not valid UTF-8 text — ignoring it")
        return None


def find_banned_company_in_text(ocr_text: str):
    """Scans OCR text for any banned-company name printed on the package
    (e.g. after 'Manufactured by: ...'). Returns the matched banned name, or
    None. This is what lets a photo with a genuine-sounding medicine name but
    a banned manufacturer still get flagged — without it, only the medicine
    name from OCR was ever checked, and a banned manufacturer's name printed
    right there on the package was silently ignored."""
    ocr_clean = re.sub(r"[^a-zA-Z0-9\s\-\+.]", " ", ocr_text).lower()
    for banned_name in db.banned_company_list:
        if len(banned_name) >= 4 and banned_name in ocr_clean:
            return banned_name
    return None


_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date_string(date_str: str) -> "datetime | None":
    """Parses date strings like MM/YY, MM/YYYY, DEC 2026 into a datetime object."""
    from datetime import datetime
    if not date_str:
        return None
    s = date_str.strip().lower()
    m1 = re.search(r"^(\d{1,2})[\/\-\.](\d{2,4})$", s)
    if m1:
        month, year = int(m1.group(1)), int(m1.group(2))
        if year < 100:
            year += 2000
        if 1 <= month <= 12 and 1990 <= year <= 2050:
            day = 28 if month == 2 else (30 if month in (4, 6, 9, 11) else 31)
            return datetime(year, month, day)

    m2 = re.search(r"^([a-z]{3,9})[\/\-\.\s\']+(\d{2,4})$", s)
    if m2:
        mon_str = m2.group(1)[:3]
        year = int(m2.group(2))
        if year < 100:
            year += 2000
        month = _MONTH_MAP.get(mon_str)
        if month and 1990 <= year <= 2050:
            day = 28 if month == 2 else (30 if month in (4, 6, 9, 11) else 31)
            return datetime(year, month, day)
    return None


def extract_batch_and_expiry(ocr_text: str) -> dict:
    """Extracts batch/lot numbers and expiry/mfg dates from packaging text,
    and calculates whether the pack is expired."""
    from datetime import datetime
    if not ocr_text:
        return {
            "batch_number": None,
            "expiry_date": None,
            "mfg_date": None,
            "is_expired": None,
            "expiry_status": None,
        }

    batch_no = None
    exp_str = None
    mfg_str = None

    # Batch search
    batch_patterns = [
        r"(?:b(?:\.?\s*no\.?|\.?\s*n\.?|atch\s*no\.?|atch)|lot\s*(?:no\.?)?)\s*[:#\s]?\s*([a-zA-Z0-9\-\/]{3,15})",
        r"\b(?:b\.?n\.?|lot)\s*[:#\s]?\s*([a-zA-Z0-9\-\/]{3,15})",
    ]
    for pat in batch_patterns:
        m = re.search(pat, ocr_text, re.IGNORECASE)
        if m:
            cand = m.group(1).strip().upper()
            if cand not in ("EXP", "MFG", "DATE", "TABLET", "CAPSULE", "PRICE", "MRP"):
                batch_no = cand
                break

    # Expiry search
    exp_patterns = [
        r"(?:exp(?:iry)?\.?\s*(?:dt|date)?|use\s*(?:before|by))\s*[:#\s]?\s*([0-9]{1,2}[\/\-\.][0-9]{2,4}|[a-zA-Z]{3,9}[\/\-\.\s\']+[0-9]{2,4})",
        r"\bexp\.?\s*[:#\s]?\s*([0-9]{1,2}[\/\-\.][0-9]{2,4}|[a-zA-Z]{3,9}[\/\-\.\s\']+[0-9]{2,4})",
    ]
    for pat in exp_patterns:
        m = re.search(pat, ocr_text, re.IGNORECASE)
        if m:
            exp_str = m.group(1).strip()
            break

    # Mfg search
    mfg_patterns = [
        r"(?:mfg|mfd|mfr)\.?\s*(?:dt|date)?\s*[:#\s]?\s*([0-9]{1,2}[\/\-\.][0-9]{2,4}|[a-zA-Z]{3,9}[\/\-\.\s\']+[0-9]{2,4})",
    ]
    for pat in mfg_patterns:
        m = re.search(pat, ocr_text, re.IGNORECASE)
        if m:
            mfg_str = m.group(1).strip()
            break

    is_expired = None
    expiry_status = None
    parsed_exp = parse_date_string(exp_str)
    if parsed_exp:
        now = datetime.now()
        if parsed_exp < now:
            is_expired = True
            expiry_status = f"EXPIRED ({parsed_exp.strftime('%b %Y')})"
        else:
            is_expired = False
            months_left = (parsed_exp.year - now.year) * 12 + (parsed_exp.month - now.month)
            if months_left <= 0:
                expiry_status = f"Expiring this month ({parsed_exp.strftime('%b %Y')})"
            else:
                expiry_status = f"VALID (Expires in {months_left} months · {parsed_exp.strftime('%b %Y')})"

    return {
        "batch_number": batch_no,
        "expiry_date": exp_str,
        "mfg_date": mfg_str,
        "is_expired": is_expired,
        "expiry_status": expiry_status,
    }


def medverify_text_pipeline(image_path: str) -> dict:
    """
    Full image -> verification result pipeline (QR first, OCR fallback).
    This does NOT run the CNN models — see cnn_inference.py for that,
    combine both in main.py for the full result.

    Never raises: any decode/OCR failure is reported back as a normal
    ERROR/NOT_FOUND result rather than propagating an exception to the API layer.
    """
    logger.info("Scanning: %s", os.path.basename(image_path))

    _, pil_img = load_image_any_format(image_path)
    if pil_img is None:
        return {
            "status": "INVALID_INPUT",
            "reason": "Could not read this file as an image (it may be corrupted, unsupported, or not an image at all)",
            "confidence": None,
        }

    # Never blindly trust QR/barcode payload data — it is only used to look up
    # a name in our own database (verify_medicine), never executed or rendered.
    qr_data = _decode_qr(pil_img)
    if qr_data:
        logger.info("QR/Barcode found")
        result = verify_medicine(qr_data)
        result["method"] = "QR/Barcode"
        qr_batch = extract_batch_and_expiry(qr_data)
        result.update(qr_batch)
        result["optical_text_extracted"] = qr_data
        return result

    logger.info("No QR — running OCR...")
    raw_text, all_ocr_text = extract_text_ocr_robust(pil_img)
    match, score = smart_medicine_match(raw_text)
    if not match and all_ocr_text:
        match, score = smart_medicine_match(all_ocr_text)

    if not match:
        # Nothing in the small curated genuine list — also check the much
        # larger general database before giving up. Done as a fallback
        # rather than during every escalation attempt in
        # extract_text_ocr_robust(): scanning ~250k names is cheap (~50ms)
        # but there's no reason to pay it more than once per image. A match
        # here still correctly resolves to UNVERIFIED (not GENUINE) via
        # verify_medicine(), since it's only confirming presence in the
        # broader catalog, not independently-verified authenticity.
        broad_match, broad_score = smart_medicine_match(all_ocr_text, name_list=db.details_names_list)
        if not broad_match and raw_text:
            broad_match, broad_score = smart_medicine_match(raw_text, name_list=db.details_names_list)
        if broad_match:
            logger.info("Match found in broad database (score: %d)", broad_score)
            match, score = broad_match, broad_score

    # Scan everything tried (not just the winning variant) for a banned
    # company name — a preprocessing pass that didn't win on medicine-name
    # score might still have picked up the manufacturer line clearly.
    banned_hit = find_banned_company_in_text(all_ocr_text)
    batch_info = extract_batch_and_expiry(all_ocr_text or raw_text)

    if match:
        logger.info("Best OCR match found (score: %d)", score)
        result = verify_medicine(match, company_name=banned_hit)
        result["method"] = "OCR"
        result["ocr_match_score"] = score
        result.update(batch_info)
        result["optical_text_extracted"] = raw_text.strip() or all_ocr_text.strip()
        if batch_info.get("is_expired"):
            result["expiry_warning"] = f"CRITICAL ALERT: Packaging indicates this medicine has EXPIRED ({batch_info['expiry_date']}). Do not administer or consume."
        return result

    if banned_hit:
        # No confident medicine-name match, but the package text itself
        # names a banned manufacturer — that alone is worth flagging rather
        # than falling through to a generic NOT_FOUND. Pass the raw OCR text
        # as the medicine_name field so verify_medicine's empty-input check
        # doesn't short-circuit before it reaches the banned-company check.
        logger.info("Banned company name found in OCR text with no medicine match")
        result = verify_medicine(raw_text.strip() or "(unreadable)", company_name=banned_hit)
        result["method"] = "OCR"
        result.update(batch_info)
        result["optical_text_extracted"] = raw_text.strip() or all_ocr_text.strip()
        return result

    if not QR_AVAILABLE and not OCR_AVAILABLE:
        reason = (
            "QR/Barcode and OCR scanning are both unavailable on this server. "
            "Please use 'Database Lookup' instead."
        )
    elif not raw_text.strip():
        reason = "No readable text or QR/barcode found in this image"
    else:
        reason = "Could not extract a readable medicine name from the image"

    res = {
        "status": "NOT_FOUND",
        "reason": reason,
        "confidence": "LOW",
        "method": "OCR",
        "optical_text_extracted": raw_text.strip() or all_ocr_text.strip(),
    }
    res.update(batch_info)
    return res
