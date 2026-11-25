"""
Fuzzy-matching and the core text-based verification logic
(medicine name / company name -> GENUINE / UNVERIFIED / NOT_FOUND / COUNTERFEIT-signal).
"""
import math
import re
from difflib import SequenceMatcher, get_close_matches
from typing import Optional

from app import config
from app.database import db


def _clean(value):
    """pandas gives back NaN for empty spreadsheet cells; NaN is not valid JSON
    (json.dumps emits the literal token `NaN`, which most strict JSON parsers
    reject), so convert any float NaN to None before it goes in an API response."""
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _letters_only(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def _normalize_query(query: str) -> str:
    cleaned = re.sub(
        r"\b(tablets?|tabs?|capsules?|caps?|syrups?|suspensions?|injections?|drops?|gels?|creams?|ointments?|mg|gm|ml)\b",
        "",
        query.lower(),
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def fuzzy_find(query: str, name_list: list[str], cutoff: float = config.FUZZY_MATCH_CUTOFF) -> Optional[str]:
    """Exact match first, then normalized/substring match, then fuzzy (edit-distance) match."""
    if not query:
        return None
    raw_query = query.strip().lower()
    if not raw_query:
        return None

    # Try original query first, then normalized query (stripping form suffixes like 'tablet')
    query_variants = [raw_query]
    norm_query = _normalize_query(raw_query)
    if norm_query and norm_query != raw_query:
        query_variants.append(norm_query)

    for q in query_variants:
        if q in name_list:
            return q

        partial = [n for n in name_list if len(n) >= 4 and (q in n or n in q)]
        if partial:
            return partial[0]

        candidates = get_close_matches(q, name_list, n=5, cutoff=cutoff)
        query_letters = _letters_only(q)
        for candidate in candidates:
            candidate_letters = _letters_only(candidate)
            if not query_letters or not candidate_letters:
                continue
            if SequenceMatcher(None, query_letters, candidate_letters).ratio() >= cutoff:
                return candidate

    return None


def _check_expiry(date_str: Optional[str]):
    from app.ocr_pipeline import parse_date_string
    from datetime import datetime
    parsed = parse_date_string(date_str)
    if not parsed:
        return None, None
    now = datetime.now()
    if parsed < now:
        return True, f"EXPIRED ({parsed.strftime('%b %Y')})"
    months_left = (parsed.year - now.year) * 12 + (parsed.month - now.month)
    if months_left <= 0:
        return False, f"Expiring this month ({parsed.strftime('%b %Y')})"
    return False, f"VALID (Expires in {months_left} months · {parsed.strftime('%b %Y')})"


def _verify_medicine_core(medicine_name: str, company_name: Optional[str] = None) -> dict:
    """
    Core verification check against the three databases.

    Returns a dict with status one of:
      GENUINE     — matched a verified authentic-medicines record
      COUNTERFEIT — the *company* is on the government banned-companies list
                    (a firm-level fact, not an image-based guess)
      UNVERIFIED  — found in the general medicine-details database, but not
                    in the curated "verified genuine" list — could be a real
                    but unverified product, not evidence of counterfeiting
      NOT_FOUND   — no match anywhere; treat as a signal to investigate
                    further, not as proof of counterfeiting
    """
    medicine_name = (medicine_name or "").strip()[: config.MAX_TEXT_FIELD_LEN]
    company_name = (company_name or "").strip()[: config.MAX_TEXT_FIELD_LEN] or None

    result = {
        "medicine": medicine_name,
        "company": company_name or "Not provided",
        "status": None,
        "reason": None,
        "confidence": None,
        "details": None,
        "matched_name": None,
    }

    if not medicine_name:
        result.update(
            status="INVALID_INPUT",
            confidence=None,
            reason="No medicine name provided",
        )
        return result

    if not db.loaded:
        result.update(
            status="ERROR",
            confidence=None,
            reason="Verification database is not loaded on the server",
        )
        return result

    # 1. Banned company check
    if company_name:
        matched_banned = fuzzy_find(company_name, db.banned_company_list)
        if matched_banned:
            result.update(
                status="COUNTERFEIT",
                confidence="HIGH",
                reason=f'"{company_name}" matches a government-banned pharma company',
            )
            return result

    # 2. Genuine database check
    matched_genuine = fuzzy_find(medicine_name, db.genuine_names_list)
    if matched_genuine:
        genuine_row = db.get_genuine_row(matched_genuine)
        genuine_company = _clean(genuine_row.get("Name of Company")) if genuine_row is not None else None
        category = _clean(genuine_row.get("Category")) if genuine_row is not None else None

        # Check for manufacturer conflict if company was specified
        company_conflict = False
        if company_name and genuine_company:
            comp_match = fuzzy_find(company_name, [genuine_company.lower()])
            if not comp_match:
                company_conflict = True

        if company_conflict:
            result.update(
                status="UNVERIFIED",
                confidence="MEDIUM",
                reason=f'Formulation matches authentic "{matched_genuine}", but entered manufacturer "{company_name}" does not match registered manufacturer "{genuine_company}". Verify authenticity with official source.',
                matched_name=matched_genuine,
                company=genuine_company or company_name,
                category=category,
            )
        else:
            result.update(
                status="GENUINE",
                confidence="HIGH",
                reason="Verified in authenticated medicines database",
                matched_name=matched_genuine,
                company=genuine_company or company_name or "Not provided",
                category=category,
            )

        # Resolve details from details database
        detail_match = fuzzy_find(matched_genuine, db.details_names_list)
        if detail_match:
            detail_row = db.get_detail_row(detail_match)
            if detail_row is not None:
                raw_comp = _clean(detail_row.get("Composition"))
                raw_uses = _clean(detail_row.get("Uses"))
                raw_side = _clean(detail_row.get("Side_effects"))
                raw_mfr = _clean(detail_row.get("Manufacturer"))

                # Data cleaning for scraped glitches (e.g. "(650mg)ADD")
                if raw_comp and ("ADD" in raw_comp or raw_comp.startswith("(")):
                    clean_comp = re.sub(r"ADD\b", "", raw_comp).strip()
                    if category and category.lower() not in clean_comp.lower():
                        clean_comp = f"{category} {clean_comp}".strip()
                    raw_comp = clean_comp

                # Clinical fallback for famous categories if scraped uses are missing
                if not raw_uses and category and "paracetamol" in category.lower():
                    raw_uses = "Fever reduction, headache, body ache, and mild to moderate pain relief"
                if not raw_side and category and "paracetamol" in category.lower():
                    raw_side = "Nausea, allergic skin reaction (rare); safe when used at recommended therapeutic dosage"

                result["details"] = {
                    "composition": raw_comp,
                    "uses": raw_uses,
                    "side_effects": raw_side,
                    "manufacturer": raw_mfr or genuine_company,
                }
        elif category and "paracetamol" in category.lower():
            result["details"] = {
                "composition": "Paracetamol (650mg)",
                "uses": "Fever reduction, headache, body ache, and mild to moderate pain relief",
                "side_effects": "Nausea, allergic skin reaction (rare); safe when used at recommended therapeutic dosage",
                "manufacturer": genuine_company,
            }
        return result

    # 3. Present in general details DB but not the verified genuine list
    detail_match = fuzzy_find(medicine_name, db.details_names_list)
    if detail_match:
        detail_row = db.get_detail_row(detail_match)
        comp = None
        uses = None
        side_effects = None
        mfr = None
        if detail_row is not None:
            comp = _clean(detail_row.get("Composition"))
            uses = _clean(detail_row.get("Uses"))
            side_effects = _clean(detail_row.get("Side_effects"))
            mfr = _clean(detail_row.get("Manufacturer"))

        result.update(
            status="UNVERIFIED",
            confidence="MEDIUM",
            reason="Found in general pharmaceutical database, but not in curated authentic verification list",
            matched_name=detail_match,
            company=mfr or company_name or "Not provided",
            details={
                "composition": comp,
                "uses": uses,
                "side_effects": side_effects,
                "manufacturer": mfr,
            } if (comp or uses or mfr) else None,
        )
        return result

    # 4. Not found anywhere
    result.update(
        status="NOT_FOUND",
        confidence="LOW",
        reason="Medicine not found in any verified database — treat with caution and verify through an official source",
    )
    return result


def verify_medicine(
    medicine_name: str,
    company_name: Optional[str] = None,
    batch_number: Optional[str] = None,
    expiry_date: Optional[str] = None,
) -> dict:
    """Wrapper that verifies the medicine and enriches with batch & expiry information."""
    result = _verify_medicine_core(medicine_name, company_name=company_name)
    if batch_number:
        result["batch_number"] = batch_number.strip().upper()
    if expiry_date:
        result["expiry_date"] = expiry_date.strip()
        is_exp, exp_status = _check_expiry(expiry_date)
        result["is_expired"] = is_exp
        result["expiry_status"] = exp_status
        if is_exp:
            result["expiry_warning"] = (
                f"CRITICAL ALERT: Expiry date ({expiry_date}) indicates this medicine has EXPIRED. "
                "Do not administer or consume."
            )
    return result
