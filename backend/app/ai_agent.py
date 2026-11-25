"""
MedVerify AI agent (multi-language medicine Q&A).

Answers free-text questions about a medicine ("what is this for", "side
effects?", "kya ye bacchon ke liye safe hai?") in whatever language the user
asks in. Grounded on purpose: the model is only given the medicine's own
database record (Composition / Uses / Side_effects / Manufacturer from
Medicine_Details.csv, plus the GENUINE/UNVERIFIED/NOT_FOUND verification
status) and is explicitly told not to invent facts beyond that record. This
keeps it from confidently hallucinating dosages or interactions that aren't
actually in the dataset.

Uses Groq's OpenAI-compatible chat completions API (https://groq.com) —
fast inference, generous free tier. Requires GROQ_API_KEY to be set; if it
isn't, /ask reports the feature as unavailable instead of crashing the app,
same pattern as the optional CNN models and rate limiting elsewhere in this
project.
"""
import logging
from typing import Optional

import requests

from app import config

logger = logging.getLogger("medverify.ai_agent")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

AI_AVAILABLE = bool(config.GROQ_API_KEY)
if not AI_AVAILABLE:
    logger.warning(
        "GROQ_API_KEY not set — the /ask AI agent endpoint is DISABLED. "
        "Set MEDVERIFY_GROQ_API_KEY in backend/.env to enable it (free key: https://console.groq.com/keys)."
    )

SYSTEM_PROMPT = """You are the MedVerify assistant. You answer questions about ONE specific \
medicine for a general member of the public in India.

Rules you must follow:
1. Reply in the language the user's question is written in (or the language \
explicitly requested), whatever it is — Hindi, Marathi, Tamil, Hinglish, English, etc.
2. Base your answer ONLY on the "Known record" data given below. Do not invent \
dosages, interactions, brand comparisons, or facts not present in that record.
3. If the record doesn't contain the answer to the user's question, say so plainly \
in their language instead of guessing.
4. Never present yourself as a doctor. For anything about whether to take a \
medicine, dosage, or a medical decision, clearly recommend consulting a doctor \
or pharmacist.
5. Keep answers short and easy to read for a non-technical person — a few \
sentences or a short bullet list, not an essay.
6. If the verification status is COUNTERFEIT or NOT_FOUND, make sure the user \
understands that clearly before anything else.
"""


def _build_record_context(verification_result: dict) -> str:
    """Turns a /verify/text-style result dict into a compact grounding block."""
    lines = [f"Verification status: {verification_result.get('status', 'UNKNOWN')}"]
    reason = verification_result.get("reason")
    if reason:
        lines.append(f"Reason: {reason}")

    matched = verification_result.get("matched_name") or verification_result.get("medicine")
    if matched:
        lines.append(f"Matched medicine name: {matched}")

    details = verification_result.get("details") or {}
    for key, label in (
        ("composition", "Composition"),
        ("uses", "Uses"),
        ("side_effects", "Side effects"),
        ("manufacturer", "Manufacturer"),
    ):
        val = details.get(key)
        if val:
            lines.append(f"{label}: {val}")

    if len(lines) == 1:
        lines.append("(No further details available in the database for this medicine.)")

    return "\n".join(lines)


def ask_about_medicine(
    verification_result: dict,
    question: str,
    language_hint: Optional[str] = None,
) -> dict:
    """
    Calls Groq with the medicine's known record as grounding context and the
    user's free-text question. Returns {"answer": str} or raises RuntimeError
    on a failed/misconfigured call (the endpoint layer turns that into a
    clean HTTP error rather than a 500 stack trace).
    """
    if not AI_AVAILABLE:
        raise RuntimeError("AI agent is not configured (missing GROQ_API_KEY).")

    record_context = _build_record_context(verification_result)

    user_content = f"Known record for this medicine:\n{record_context}\n\nUser's question:\n{question.strip()}"
    if language_hint:
        user_content += f"\n\n(Answer specifically in: {language_hint})"

    payload = {
        "model": config.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        return {"answer": answer}
    except requests.exceptions.Timeout as e:
        logger.error("Groq API timed out: %s", e)
        raise RuntimeError("The AI agent took too long to respond. Please try again.") from e
    except requests.exceptions.RequestException as e:
        logger.error("Groq API call failed: %s", e)
        raise RuntimeError("Could not reach the AI agent right now. Please try again later.") from e
    except (KeyError, IndexError, ValueError) as e:
        logger.error("Unexpected Groq API response shape: %s", e)
        raise RuntimeError("The AI agent returned an unexpected response.") from e
