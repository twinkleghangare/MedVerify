"""
Optional AI-assisted explanation layer using Groq's free API (fast
open-source models like Llama).

IMPORTANT — what this does and does NOT do:
  - It ONLY explains, in plain language, a verification result that
    verify_medicine() / medverify_text_pipeline() already produced from the
    real database/OCR/QR logic.
  - It NEVER makes or overrides a GENUINE / COUNTERFEIT / UNVERIFIED /
    NOT_FOUND decision itself. Letting an LLM decide medicine authenticity
    would mean trusting a model that can hallucinate — the whole point of
    this project's hardening work has been to keep that decision
    evidence-based. This module is read-only with respect to the result.
  - It degrades gracefully exactly like the CNN checks in cnn_inference.py:
    no API key, package missing, network error, or timeout all just mean
    "not available" — never a crash, never a blocked/slowed-down core
    verification response.
"""
import logging

from app import config

logger = logging.getLogger("medverify.groq")

try:
    from groq import Groq
    GROQ_SDK_AVAILABLE = True
except ImportError as e:
    logger.warning("groq package not installed — AI explanation disabled: %s", e)
    Groq = None
    GROQ_SDK_AVAILABLE = False

_client = None
_client_init_failed = False


def _get_client():
    global _client, _client_init_failed
    if not GROQ_SDK_AVAILABLE or not config.GROQ_API_KEY or _client_init_failed:
        return None
    if _client is None:
        try:
            _client = Groq(api_key=config.GROQ_API_KEY)
        except Exception as e:
            logger.error("Failed to initialize Groq client: %s", e)
            _client_init_failed = True
            return None
    return _client


def is_available() -> bool:
    """Used by /health — reports whether the feature is configured at all,
    not whether a live call would currently succeed (that's only known by
    actually trying, which explain_result() does per-request)."""
    return GROQ_SDK_AVAILABLE and bool(config.GROQ_API_KEY)


def explain_result(result: dict) -> dict:
    """
    Turns a verification result dict (from verify_medicine() or
    medverify_text_pipeline()) into a short, plain-language explanation.

    Returns either:
      {"available": True, "explanation": "..."}
      {"available": False, "reason": "..."}

    Never raises — any failure (not configured, network error, timeout,
    unexpected API response) is caught and reported as "not available".
    Callers should treat this as decorative/optional and never require it
    for a valid response.
    """
    client = _get_client()
    if client is None:
        if not GROQ_SDK_AVAILABLE:
            return {"available": False, "reason": "groq package not installed on the server"}
        if not config.GROQ_API_KEY:
            return {"available": False, "reason": "AI explanation not configured (no Groq API key set)"}
        return {"available": False, "reason": "AI explanation client failed to initialize"}

    status = result.get("status", "UNKNOWN")
    medicine = result.get("medicine") or "the scanned item"
    reason = result.get("reason", "")

    # The prompt hands the model the decision that was ALREADY made and asks
    # it only to explain that — it's explicitly told not to introduce a new
    # verdict of its own, which is the guardrail that keeps this feature
    # from ever becoming the thing that decides authenticity.
    prompt = (
        f"A medicine verification system checked \"{medicine}\" and returned the "
        f"status \"{status}\" with this technical reason: \"{reason}\".\n\n"
        f"In 2-3 short, plain-language sentences, explain what this status means "
        f"for someone at a pharmacy counter and what they should do next. "
        f"Do not invent facts that aren't given above. Do not state a different "
        f"or new safety verdict of your own — only explain the status already given."
    )

    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
            timeout=config.GROQ_TIMEOUT_SECONDS,
        )
        text = (completion.choices[0].message.content or "").strip()
        if not text:
            return {"available": False, "reason": "AI explanation returned an empty response"}
        return {"available": True, "explanation": text}
    except Exception as e:
        logger.warning("Groq explanation request failed: %s", e)
        return {"available": False, "reason": "AI explanation request failed or timed out"}


# --------------------------------------------------------------------------
# Chat about a medicine — free-form Q&A grounded in the verification result
# --------------------------------------------------------------------------
MAX_CHAT_HISTORY_TURNS = 6  # cap on prior turns kept, to bound tokens/cost
MAX_QUESTION_LEN = 500


def chat_about_medicine(context: dict, question: str, history: list) -> dict:
    """
    Free-form conversational Q&A about a specific medicine, grounded in the
    real verification result already produced by the database/OCR logic
    (never re-decided by the model — see the system prompt below).

    context: the verification result dict (status, medicine, matched_name,
             category, details: {composition, uses, side_effects, manufacturer}, ...)
    question: the user's free-text question
    history: list of {"role": "user"|"assistant", "content": str} from
             earlier turns in this conversation (only the last
             MAX_CHAT_HISTORY_TURNS are used)

    Returns {"available": True, "answer": "..."} or
            {"available": False, "reason": "..."}. Never raises.
    """
    client = _get_client()
    if client is None:
        if not GROQ_SDK_AVAILABLE:
            return {"available": False, "reason": "groq package not installed on the server"}
        if not config.GROQ_API_KEY:
            return {"available": False, "reason": "AI chat not configured (no Groq API key set)"}
        return {"available": False, "reason": "AI chat client failed to initialize"}

    question = (question or "").strip()[:MAX_QUESTION_LEN]
    if not question:
        return {"available": False, "reason": "No question provided"}

    medicine = context.get("medicine") or context.get("matched_name") or "this medicine"
    status = context.get("status", "UNKNOWN")
    details = context.get("details") or {}

    # Ground the model in exactly what our own verification pipeline found —
    # it must answer FROM this, not invent independent claims, and it must
    # never issue its own genuine/counterfeit verdict (that's the one thing
    # this whole project keeps strictly evidence-based, not LLM-decided).
    system_prompt = (
        "You are a helpful assistant answering questions about a specific medicine "
        "for a MedVerify user (could be a patient or a pharmacist). Here is what "
        "MedVerify's own database/OCR verification already found about it — treat "
        "this as ground truth and do not contradict it:\n"
        f"- Name: {medicine}\n"
        f"- Verification status: {status}\n"
        f"- Category: {context.get('category') or 'unknown'}\n"
        f"- Manufacturer: {context.get('company') or 'unknown'}\n"
        f"- Composition: {details.get('composition') or 'unknown'}\n"
        f"- Uses: {details.get('uses') or 'unknown'}\n"
        f"- Side effects: {details.get('side_effects') or 'unknown'}\n\n"
        "Answer the user's questions about this medicine — what it's for, how it "
        "generally works, common side effects, general precautions, and similar "
        "informational questions — using the details above plus your general "
        "medical knowledge where the details above don't cover it (make clear "
        "when you're doing so). Keep answers short and conversational (2-5 "
        "sentences unless more detail is clearly needed).\n\n"
        "Hard rules:\n"
        "1. Never state a new or different genuine/counterfeit/authenticity "
        "verdict — the verification status above is already decided by "
        "MedVerify's own database and OCR checks, not by you.\n"
        "2. Never give specific dosing instructions, prescribing advice, or "
        "tell the user to start/stop/change a medication — always point to a "
        "doctor or pharmacist for that.\n"
        "3. If asked something unrelated to this medicine, gently redirect to "
        "medicine-related questions."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for turn in (history or [])[-MAX_CHAT_HISTORY_TURNS:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:MAX_QUESTION_LEN]})
    messages.append({"role": "user", "content": question})

    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.4,
            timeout=config.GROQ_TIMEOUT_SECONDS,
        )
        text = (completion.choices[0].message.content or "").strip()
        if not text:
            return {"available": False, "reason": "AI chat returned an empty response"}
        return {"available": True, "answer": text}
    except Exception as e:
        logger.warning("Groq chat request failed: %s", e)
        return {"available": False, "reason": "AI chat request failed or timed out"}
