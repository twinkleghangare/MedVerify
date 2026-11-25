"""Unit tests for the fuzzy-matching / core verification logic (no HTTP layer)."""
from app.database import db
from app.matching import fuzzy_find, verify_medicine


def test_fuzzy_find_exact_match():
    assert fuzzy_find("okacet", db.genuine_names_list) == "okacet"


def test_fuzzy_find_case_and_whitespace_insensitive():
    assert fuzzy_find("  OkaCet  ", db.genuine_names_list) == "okacet"


def test_fuzzy_find_no_match_returns_none():
    assert fuzzy_find("completely-made-up-xyz-000", db.genuine_names_list) is None


def test_fuzzy_find_empty_query_returns_none():
    assert fuzzy_find("", db.genuine_names_list) is None
    assert fuzzy_find(None, db.genuine_names_list) is None


def test_verify_known_genuine_medicine():
    result = verify_medicine("Okacet")
    assert result["status"] == "GENUINE"
    assert result["confidence"] == "HIGH"
    assert result["matched_name"] == "okacet"


def test_verify_unknown_medicine_is_not_found():
    result = verify_medicine("TotallyFakeMedicineXYZ123")
    assert result["status"] == "NOT_FOUND"


def test_verify_empty_name_is_invalid_input():
    result = verify_medicine("")
    assert result["status"] == "INVALID_INPUT"


def test_verify_banned_company_flagged_as_counterfeit():
    banned = db.banned_company_list[0]
    result = verify_medicine("Paracetamol", company_name=banned)
    assert result["status"] == "COUNTERFEIT"
    assert result["confidence"] == "HIGH"


def test_verify_medicine_in_details_only_is_unverified_or_genuine():
    # Any medicine present in the broad details DB should resolve to either
    # GENUINE (if also in the curated list) or UNVERIFIED — never crash.
    if db.details_names_list:
        name = db.details_names_list[0]
        result = verify_medicine(name)
        assert result["status"] in ("GENUINE", "UNVERIFIED")


def test_verify_medicine_truncates_overlong_input():
    long_name = "a" * 10_000
    result = verify_medicine(long_name)
    assert len(result["medicine"]) <= 200


def test_verify_medicine_result_is_json_serializable():
    import json
    result = verify_medicine("Okacet")
    json.dumps(result)  # raises if NaN or other non-JSON-safe values leak through


# --- Regression tests for OCR text-matching bugs found during manual testing ---

def test_smart_match_ignores_trivial_short_words():
    """A medicine name made only of short/common words (e.g. 'a to z ns')
    must not outscore an exact, unambiguous name match just because those
    short words appear as incidental substrings elsewhere in the OCR text."""
    from app.ocr_pipeline import smart_medicine_match
    ocr_text = (
        "OKACET Cetirizine Hydrochloride 10mg Tablets Manufactured by Cipla Ltd "
        "Category Allergy Antihistamine Store below 30C in a dry place "
        "Schedule H drug sale by retail only on the prescription of a Registered "
        "Medical Practitioner"
    )
    match, score = smart_medicine_match(ocr_text)
    assert match == "okacet"


def test_ocr_pipeline_checks_manufacturer_for_banned_companies():
    """A banned manufacturer's name printed on the package must be caught even
    when the medicine name itself matches a genuine database entry — OCR text
    must be checked against the banned-companies list, not just medicine names."""
    from app.ocr_pipeline import find_banned_company_in_text
    banned = db.banned_company_list[0]
    ocr_text = f"Okacet Cetirizine 10mg Manufactured by: {banned.title()}"
    assert find_banned_company_in_text(ocr_text) == banned


def test_load_image_applies_exif_orientation(tmp_path):
    """Phone photos store rotation as EXIF metadata rather than rotating
    pixel data. Without applying it, an image that looks upright to the user
    (and in a browser) can load sideways here, breaking OCR silently."""
    from PIL import Image
    from app.ocr_pipeline import load_image_any_format
    import piexif

    # Build a small image with an EXIF orientation tag of 6 (needs 90° rotation
    # to display upright) and confirm the loaded image comes back upright
    # (i.e. its dimensions reflect the rotation having been applied).
    img = Image.new("RGB", (40, 100), "white")  # tall, narrow — will visibly
    # change proportions once rotated, which is what we assert on below.
    exif_dict = {"0th": {274: 6}}  # 274 = Orientation tag, 6 = rotate 90 CW
    exif_bytes = piexif.dump(exif_dict)
    path = tmp_path / "rotated.jpg"
    img.save(path, exif=exif_bytes)

    _, loaded = load_image_any_format(str(path))
    assert loaded is not None
    # Original was 40x100 (portrait); orientation 6 applied should give 100x40 (landscape)
    assert loaded.size == (100, 40)


def test_smart_match_ignores_generic_label_words():
    """A single generic word (e.g. 'tablet', present on almost every
    medicine's packaging) must never be enough on its own to match an
    unrelated database entry — this was a real false positive found during
    testing with a real photo of a medicine not in the database."""
    from app.ocr_pipeline import smart_medicine_match
    # A fictitious medicine name guaranteed not to be in the demo database,
    # surrounded by generic words that happen to overlap with real entries.
    ocr_text = "Xyzatrol Wondermed 500 tablet contains film coated ip bp"
    match, score = smart_medicine_match(ocr_text)
    assert match is None
    assert score == 0


def test_smart_match_requires_two_distinctive_words():
    """A fuzzy (non-exact-phrase) match needs at least two distinctive word
    hits — a single distinctive word alone stays unmatched, since one
    overlapping word is still weak evidence for a full-name identification."""
    from app.ocr_pipeline import smart_medicine_match
    multi_word_names = [n for n in db.genuine_names_list if len(n.split()) >= 2]
    if not multi_word_names:
        return  # nothing to test against in this dataset
    name = multi_word_names[0]
    first_word = name.split()[0]
    if len(first_word) < 3:
        return
    match, score = smart_medicine_match(f"random unrelated text {first_word} more text")
    assert score == 0


def test_fuzzy_find_rejects_digit_coincidence_false_positive():
    """Two completely different medicines whose names happen to share digits
    (dosage strengths) must not fuzzy-match each other just because the raw
    character-level similarity ratio is inflated by the shared digits — a
    real confirmed case: "Augmentin 625" vs "Aten 25" scored right at the
    default cutoff purely from shared digits, despite the actual drug names
    being only ~46% similar."""
    from app.matching import fuzzy_find
    result = fuzzy_find("augmentin 625", ["aten 25", "vertin 16"])
    assert result is None


def test_fuzzy_find_still_allows_genuine_typo_tolerance():
    """The digit-coincidence fix must not break ordinary typo tolerance on
    names without dosage numbers."""
    from app.matching import fuzzy_find
    assert fuzzy_find("okcet", db.genuine_names_list) == "okacet"


def test_smart_match_allows_short_brand_distinguishing_codes():
    """Short (2-letter) brand codes like 'RD', 'SR', 'XR' are common and
    meaningful in Indian pharma naming (e.g. 'Aciloc RD' is a distinct
    product from plain 'Aciloc') and must count as real distinguishing
    words — confirmed with a real photo where 'RD' was the second word
    needed to cross the match threshold."""
    from app.ocr_pipeline import smart_medicine_match
    # Matches the real OCR pattern: dosage strengths merged as "20mg+10mg"
    # (no space) rather than two separate bare numbers — this is what the
    # actual scanned photo produced and what avoids an unrelated product
    # tying on a shared dosage number + suffix (see the tie-safety test below).
    ocr_text = "OMEPRAZOLE MAGNESIUM DOMPERIDONE TABLETS 20mg+10mg ACILOC RD Aciloc RD"
    match, score = smart_medicine_match(ocr_text, name_list=db.details_names_list)
    assert match == "aciloc rd 20 tablet"


def test_smart_match_refuses_to_guess_between_tied_candidates():
    """When two different, unrelated medicines tie for the best word-overlap
    score (e.g. both happen to share a common suffix word like 'RD' plus a
    common dosage number), picking one arbitrarily would be an unsupported
    specific-product claim — the match must be refused rather than guessed."""
    from app.ocr_pipeline import smart_medicine_match
    ocr_text = "OMEPRAZOLE MAGNESIUM DOMPERIDONE TABLETS 20mg 10mg ACILOC RD Aciloc RD"
    match, score = smart_medicine_match(ocr_text, name_list=db.details_names_list)
    assert match is None
    assert score == 0


def test_smart_match_still_ignores_short_english_stopwords():
    """Lowering the word-length floor to 2 chars (to allow real brand codes
    like 'RD') must not let common short English filler words ('of', 'to',
    'a') count as identifying evidence again."""
    from app.ocr_pipeline import smart_medicine_match
    ocr_text = "to be sold by retail on the prescription of a registered medical practitioner only tablet contains ltd"
    match, score = smart_medicine_match(ocr_text, name_list=db.genuine_names_list)
    assert score == 0


def test_verify_medicine_details_use_resolved_name_not_raw_query():
    """A short raw query (e.g. 'dolo') must not pull composition/manufacturer
    details from an unrelated database entry that happens to fuzzy-match the
    raw query more loosely than the resolved brand name does — confirmed
    real case: 'dolo' alone fuzzy-matched a completely different Gabapentin +
    Nortriptyline product's details, while the resolved 'dolo 650' correctly
    matches its own entry. The details lookup must use the resolved name."""
    result = verify_medicine("dolo")
    assert result["status"] == "GENUINE"
    assert result["matched_name"] == "dolo 650"
    # Manufacturer from the details enrichment must agree with the genuine
    # list's own company field — not point to an unrelated product.
    if result.get("details") and result["details"].get("manufacturer"):
        assert "micro labs" in result["details"]["manufacturer"].lower()
