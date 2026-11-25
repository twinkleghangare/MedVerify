# MedVerify — Complete Project (Backend + Frontend)

AI-assisted medicine authentication: database + fuzzy-match verification,
QR/Barcode + OCR scanning, and two optional CNN checks (anomaly detector +
demo classifier), served by a FastAPI backend with a plain HTML/JS frontend.

This README documents the project **after a production-hardening pass**
(input validation, upload security, error handling, rate limiting, and an
automated test suite were added — see "What changed" below).

## Project structure

```
medverify_project/
├── backend/
│   ├── app/
│   │   ├── config.py          # all paths + security/env settings in one place
│   │   ├── database.py        # loads genuine/banned/details databases
│   │   ├── matching.py        # fuzzy match + verify_medicine() logic
│   │   ├── ocr_pipeline.py    # QR/Barcode + OCR pipeline
│   │   ├── cnn_inference.py   # loads + runs the two optional CNN models
│   │   ├── main.py            # FastAPI app + endpoints
│   │   └── models/weights/    # <- put your trained .keras files here (optional)
│   ├── data/                  # <- put your .xlsx / .csv database files here
│   ├── tests/                 # automated pytest suite (unit + API + security)
│   ├── requirements.txt
│   ├── requirements-dev.txt   # requirements.txt + pytest/httpx
│   ├── .env.example           # copy to .env and adjust
│   └── Dockerfile
├── frontend/
│   └── index.html             # single-file frontend, no build step needed
├── docker-compose.yml
├── start_backend.bat          # Windows: double-click to set up + run backend
├── start_backend.sh           # Mac/Linux: run to set up + run backend
└── README.md
```

## Quick start (Windows)

1. **Add your data files** into `backend/data/`:
   - `Real_Medicines_dataset.xlsx`
   - `Banned_Pharma_Companies.xlsx`
   - `Medicine_Details.csv`

2. **(Optional) Add trained CNN models** into `backend/app/models/weights/`:
   - `medverify_autoencoder_final.keras`
   - `anomaly_threshold.txt`
   - `medverify_classifier_final.keras`

   If you skip this — or skip installing TensorFlow entirely — the app still
   works: name/database verification and image OCR/QR scanning work fully;
   the two CNN checks just report `"available": false` with a reason,
   instead of the two-model checks being present at all.

3. **(Optional) Configure environment variables**: copy `backend/.env.example`
   to `backend/.env` and adjust (CORS origin, upload size limit, rate limits).

4. **Double-click `start_backend.bat`**. First run installs everything
   (takes a few minutes — TensorFlow is large); later runs start instantly.
   Keep that window open while you use MedVerify.

5. **Open `frontend/index.html`** in your browser (double-click it).
   You should see a green "Connected to MedVerify API" status at the top.

6. Use the **Verify by name** tab for text lookups, or **Scan package**
   to upload a photo.

## Quick start (Mac/Linux)

```bash
chmod +x start_backend.sh
./start_backend.sh
```

Then open `frontend/index.html` in your browser.

## System dependencies (needed once, for OCR/QR scanning)

The Python packages are installed automatically by the start script, but two
system-level tools are also required for image scanning to work:

- **Windows**: install Tesseract OCR from the
  [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) and
  make sure it's added to your PATH during setup.
- **macOS**: `brew install tesseract zbar`
- **Linux**: `sudo apt-get install -y tesseract-ocr libzbar0`

Without this, name-based verification (`Verify by name` tab) still works
fine — only the image-scanning OCR step needs it. QR/barcode decoding needs
`libzbar0` specifically; OCR needs the `tesseract-ocr` binary.

## Environment variables

See `backend/.env.example` for the full list. The important ones:

| Variable                     | Default   | Purpose                                             |
|-------------------------------|-----------|------------------------------------------------------|
| `MEDVERIFY_CORS_ORIGINS`      | `*`       | Comma-separated allowed frontend origins             |
| `MEDVERIFY_MAX_UPLOAD_MB`     | `8`       | Max accepted image upload size                       |
| `MEDVERIFY_RATE_LIMIT_TEXT`   | `30/minute` | Rate limit for `/verify/text`                       |
| `MEDVERIFY_RATE_LIMIT_IMAGE`  | `10/minute` | Rate limit for `/verify/image`                      |
| `MEDVERIFY_ENV`                | `development` | Set to `production` when deployed                |

`.env` is loaded automatically (via `python-dotenv`) if present in `backend/`.
Never commit a real `.env` — only `.env.example` is tracked.

## Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

This runs the full automated suite: unit tests for the fuzzy-matching logic,
API/integration tests against the real FastAPI app (via `TestClient`, no
network needed), and a set of security regression tests (path traversal,
disallowed file types, oversized uploads, malformed input). All tests run
against the real `backend/data/*` files, not mocks.

**Last run in this environment: 34 passed, 0 failed** (TensorFlow was not
installed in that environment, so CNN-dependent behavior was exercised via
its "model not loaded" path — see Known limitations).

## API overview

| Method | Path            | Purpose                                            |
|--------|-----------------|-----------------------------------------------------|
| GET    | `/health`       | Liveness + dependency status (DB loaded? models loaded? QR/OCR available?) |
| POST   | `/verify/text`  | Verify by medicine name (+ optional company name)   |
| POST   | `/verify/image` | Full pipeline: QR/OCR + database lookup + CNN checks |

`POST /verify/text` body: `{"medicine_name": "...", "company_name": "..."}` —
`medicine_name` is required (1–200 chars); `company_name` is optional.

`POST /verify/image` is a multipart upload (`file` field). Accepted types:
JPEG, PNG, WEBP, BMP; max size configurable via `MEDVERIFY_MAX_UPLOAD_MB`
(default 8 MB).

Result statuses: `GENUINE`, `COUNTERFEIT` (banned company match — a
firm-level database fact, not an image-based guess), `UNVERIFIED` (present
in the general details DB but not the curated genuine list), `NOT_FOUND`,
`INVALID_INPUT`, `ERROR`.

## Security considerations (what this pass changed)

An audit of the original project found and fixed the following:

- **Path traversal / arbitrary file write** in image upload handling — the
  original code built the saved filename directly from the client-supplied
  `file.filename` (e.g. `../../../../etc/evil.jpg` would escape the intended
  upload folder). Fixed: the server now generates its own filename and only
  ever trusts an allow-listed file **extension** from the original name.
- **App crashed on startup if TensorFlow wasn't installed**, even though a
  comment claimed otherwise. Fixed: model loading is now fully guarded and
  degrades to "not available" instead of taking the whole API down.
- **No upload validation** — missing file-size limit, extension allow-list,
  and content-type check. Fixed: max size (413 on exceed), extension
  allow-list (400), content-type check (400), and the file is actually
  decoded as an image before use (rejects corrupted/non-image files instead
  of crashing the pipeline).
- **No length limits on text input** (`medicine_name`/`company_name`),
  allowing arbitrarily large strings into the fuzzy-matching routine. Fixed
  via Pydantic field limits (422 on violation).
- **Reflected XSS in the frontend**: scan results (including raw text pulled
  from a scanned QR code, and any user-entered `medicine_name`/`company_name`
  echoed back in `reason` fields) were inserted into the page via
  `innerHTML` without escaping — a malicious QR code or a crafted company
  name could run arbitrary JavaScript in the viewer's browser. Confirmed
  exploitable, then fixed by HTML-escaping every backend-sourced value before
  it's rendered. A restrictive `Content-Security-Policy` meta tag was also
  added as a secondary layer.
- **OCR name-matching false positives**: `smart_medicine_match()` scored
  candidate medicine names by checking `word in ocr_text` as a plain
  substring — very short words (e.g. "a", "to") match almost any text,
  which could let an unrelated database entry outscore the medicine
  actually printed on the package. Confirmed with a real test case, fixed
  with word-boundary matching plus an exact-phrase-match priority tier.
- **OCR path never checked the manufacturer**: the image-scanning pipeline
  matched the medicine name from OCR text but never checked whether the
  *manufacturer* printed on the package matched a banned company — so a
  photo with a banned manufacturer's name right on it could still return
  GENUINE. Fixed: OCR text is now also scanned against the banned-companies
  list.
- **EXIF orientation was ignored**: phone cameras store rotation as EXIF
  metadata rather than physically rotating pixel data; browsers apply it
  automatically but PIL/OpenCV do not. A photo that looked upright to the
  user could load sideways or upside-down here, producing garbage OCR
  output with no visible error. Confirmed with a real phone photo, fixed by
  applying `ImageOps.exif_transpose()` on load.
- **OCR gave up entirely on reflective/glossy packaging**: a single plain
  OCR pass produced pure garbage on a real glare-heavy blister-foil photo.
  Fixed with staged multi-attempt preprocessing (see "OCR robustness"
  section below) — confirmed the same photo now yields real, readable
  product text instead of noise.
- **Single generic word could trigger a confident-looking false match**:
  word-overlap matching didn't distinguish identifying words ("Nimesulide")
  from generic label vocabulary that appears on nearly every medicine
  ("tablet", "mg", "ltd"), so one shared generic word could match an
  unrelated database entry. Confirmed with a real test case (a genuine
  medicine not in the database was OCR'd, matched via the sole word
  "tablet", and returned as a *different*, wrong GENUINE result). Fixed by
  excluding generic label vocabulary from scoring and requiring at least
  two distinctive word matches before accepting a fuzzy match.
- **Dosage-number coincidence caused cross-medicine false matches**: see
  "Database coverage" above — `fuzzy_find`'s character-level similarity
  ratio could be pushed over the acceptance cutoff purely by two unrelated
  medicine names sharing dosage digits (confirmed: "Augmentin 625" matched
  "Aten 25"). Fixed by requiring letters-only similarity to also clear the
  cutoff.
- **Unhandled exceptions could leak stack traces** to API callers. Fixed
  with global exception handlers that log the real error server-side and
  return a generic, safe message to the client.
- **`NaN` values from pandas** (empty spreadsheet cells) could leak into
  JSON responses as the invalid token `NaN`. Fixed with a sanitizer that
  converts them to `null`.
- **No rate limiting** on the public endpoints. Added via `slowapi` (free,
  open-source, in-memory — no external service).
- Decompression-bomb-sized images are now rejected before full decode
  (`Image.MAX_IMAGE_PIXELS` guard).

CORS is configurable via `MEDVERIFY_CORS_ORIGINS` (defaults to `*` for local
dev — safe here because the API uses no cookies/credentials, but you should
scope it to your real frontend origin once deployed). There is currently
**no authentication/authorization** — the API is fully public. That was true
of the original project and hasn't been changed, since adding a full auth
system was out of scope for this pass; see Known limitations.

## OCR robustness (production-hardening pass)

Real phone photos of medicine packaging — reflective blister foil, glare,
curved surfaces, small embossed text — routinely defeat a single plain OCR
pass. Rather than paper over this with a demo trick, the pipeline now does
what production OCR systems actually do:

- **EXIF orientation correction** on every image load (phones store rotation
  as metadata, not by physically rotating pixels — browsers apply it,
  `PIL`/`OpenCV` don't unless told to).
- **Staged multi-attempt OCR**: a cheap single pass runs first and is used
  immediately if it produces a confident match — clean, well-lit photos
  (a flat printed box, a screen, a scan) stay fast (~0.5–1s). Only when that
  fails does it escalate through progressively heavier preprocessing
  (grayscale → CLAHE adaptive contrast → denoise+CLAHE+sharpen), stopping as
  soon as one attempt is confident. Hard photos take longer (~5s in
  testing) but get a real second chance instead of an instant failure.
- **False-positive-resistant matching**: word-overlap matching ignores
  generic pharma/label vocabulary ("tablet", "mg", "ltd", etc. — present on
  nearly every medicine's packaging and thus not identifying) and requires
  at least two distinctive word matches before accepting a fuzzy match at
  all. Verified against a real test case where a single generic word
  match previously produced a confident-looking but wrong result.

**What this does and doesn't fix**: it measurably improves how much real
text gets extracted from a hard photo (confirmed: a real blister-foil photo
that previously produced pure garbage now correctly surfaces the actual
product name in the extracted text). It does **not** turn Tesseract into a
specialized packaging-OCR model — on the hardest photos it may still not
extract a clean match, and it will correctly report `NOT_FOUND` rather than
guess. That's the intended behavior: an honest "couldn't confidently read
this" beats a confident wrong answer. For production deployments handling
this class of image at scale, the industry-standard answer is to rely on
QR/DataMatrix codes as the primary channel (this project already does)
and treat OCR as a fallback, precisely because OCR on reflective packaging
remains an open problem even for commercial systems.

## Database coverage (major expansion)

The original demo dataset (159 curated "genuine" entries, ~11,800 general
records) covers only a small fraction of real medicines on the Indian
market. This pass integrated a real, legitimately-licensed public dataset —
**"India Medicines and Drug Info Dataset"** (Kaggle, scraped from Tata 1mg,
2025, CC BY-NC-SA 4.0) — into the general details database:

- **General details database: ~11,800 → 252,680 records** (deduplicated,
  existing curated entries preserved and never overwritten)
- Manufacturer names were extracted from the source data's messy scraped
  text via a best-effort regex (~85% success rate on a sample) — left
  blank rather than guessed where extraction wasn't confident
- The small **curated "genuine" list is unchanged in size** (160 entries)
  — this pass did not fabricate additional "verified genuine" entries,
  since that status is meant to represent independently-curated trust, not
  just presence in a scraped catalog. A medicine now found only in the
  larger general database correctly returns `UNVERIFIED` (present in a
  real product catalog, not independently verified), not `GENUINE`.
- **Real bug found and fixed by this expansion**: naive character-level
  fuzzy matching (`difflib.SequenceMatcher`) let dosage-number coincidences
  produce false matches between *completely unrelated* medicines — e.g.
  "Augmentin 625" (Amoxicillin) fuzzy-matched to "Aten 25" (Atenolol, an
  unrelated heart medication) purely because both strings happen to share
  several digits, scoring right at the similarity cutoff. Confirmed with
  real medicine names, fixed by requiring the letters-only (digit-stripped)
  similarity to *also* clear the cutoff before accepting a fuzzy match —
  this filters the false positive while preserving genuine typo tolerance
  (e.g. "Okcet" still correctly matches "Okacet").
- Load time for the larger CSV: ~1 second on startup — no meaningful
  runtime cost on ordinary consumer hardware.

To add more real medicines to the small curated **genuine** list (which is
what unlocks the `GENUINE` status rather than `UNVERIFIED`), add rows
directly to `backend/data/Real_Medicines_dataset.xlsx` with data you can
personally verify (e.g. from a photographed package, an official
manufacturer listing, etc.) — this project deliberately does not
auto-promote catalog entries to "verified genuine" status.

## Production incident: image-upload 502s on Render (fixed)

Real phone photos (several MB, 3000px+ per side) uploaded via the deployed
Render backend intermittently caused `502 Bad Gateway` and knocked the
whole backend offline for a bit. **Diagnosed with real Render logs** (not
guessed) — two separate confirmed causes, both fixed:

**1. The event loop was fully blocked during image processing.**
`/verify/image` was declared `async def` but called synchronous, CPU-bound
work directly — Tesseract OCR, OpenCV preprocessing, pandas/fuzzy-match
lookups. Render logs showed this precisely: a 76-second gap where **zero**
requests were served, not even `/health`, immediately after
`"No QR — running OCR..."` logged — then the process restarting from
scratch. The single worker's event loop was completely occupied by one
image scan, meaning the whole backend looked dead to Render's platform
(and to every other user) for as long as that scan took. Fixed: the
blocking calls now run via FastAPI's `run_in_threadpool`, keeping the
event loop free to keep serving other requests (confirmed: `/health`
responds in ~15ms even while a slow image scan is in progress on the same
server — verified with a real concurrent test).

**2. Wasted memory from a duplicate full-resolution image load** — see
below. Real phone photos are often 3000-4000px+ per side; both issues
compounded on a resource-constrained deployment.

- **A dead, wasteful full-resolution image load**: `load_image_any_format()`
  loaded the image via `cv2.imread()` at full original resolution *and*
  loaded it again via PIL — but the `cv2` copy (`img_cv`) was never actually
  used by any caller. Confirmed via a full-codebase check, then removed.
- **No downscaling before OCR processing**: the multi-variant OCR pass
  (grayscale + CLAHE + denoise + sharpen) held several full-resolution
  copies of the image in memory at once. Fixed: images are now downscaled
  to at most 1600px on the longest side (`MEDVERIFY_MAX_IMAGE_DIMENSION`,
  configurable) before any processing.

Measured in this sandbox after the memory fix: processing the real photo
that triggered the original crash added only ~22MB over the ~177MB
baseline (which is itself mostly the 252k-row database loaded in memory).

## Optional AI explanation (Groq)

`GET/POST` requests to `/verify/text` and `/verify/image` accept an optional
`?explain=true` query parameter. When set, the response gets an extra
`ai_explanation` field: a short, plain-language explanation of the
verification result, generated by Groq's free API (fast open-source models
like Llama — get a free key at https://console.groq.com/keys, no credit
card needed).

**Real production issue found and fixed**: the default model
(`llama-3.1-8b-instant`) was deprecated by Groq (confirmed via a real
error in Render's logs: `model_not_found`). Updated the default to
`openai/gpt-oss-20b`, Groq's own recommended replacement. If this happens
again in the future (Groq periodically deprecates models), set
`GROQ_MODEL` to a currently-supported model id — see
https://console.groq.com/docs/models for the live list.

**What it is and isn't:**
- It only *explains* a result the real database/OCR/QR logic already
  produced — it never decides or overrides GENUINE/COUNTERFEIT/UNVERIFIED/
  NOT_FOUND itself. Letting an LLM make that call would reintroduce exactly
  the kind of unverifiable, hallucination-prone judgment this project has
  been hardened against.
- It's opt-in and off by default (`explain=false`) so the core verification
  response stays fast and never depends on a third-party API being up.
- It degrades gracefully like the CNN checks: no API key, the `groq`
  package missing, a network error, or a timeout all just report
  `{"available": false, "reason": "..."}` — never a crash, never a blocked
  response.

**Setup:** set `GROQ_API_KEY` in `.env` (see `.env.example`) or as an
environment variable on your deployment platform. Nothing else changes —
leave it unset and this feature simply stays unavailable.

**Not independently tested against the live Groq API in this environment**
(the sandbox this project was developed in has no network access to
api.groq.com) — the graceful-degradation path (no key configured) was
tested and works; the actual live-call path should be verified once a
real key is added.

## Android app

`mobile-app/` wraps the exact same frontend (`www/index.html` is kept in
sync with `frontend/index.html` and `docs/index.html`) in a native Android
shell using [Capacitor](https://capacitorjs.com/), so it can be installed
and run like a normal app — own icon, splash screen, no browser address
bar, and a settings option (footer "Change" button) to point it at a
different backend without rebuilding.

See **[BUILD_APK_STEPS.md](BUILD_APK_STEPS.md)** for exact steps to build
the actual `.apk` file — this requires Android Studio (which wasn't
available in the environment that assembled this project, so the APK
itself isn't included here, only the ready-to-build project).

## Chat about a medicine (Groq)

After any verification (text or image), the frontend shows an "Ask about
this medicine" chat box backed by `POST /chat`. Users can ask free-form
questions — "what is this for", "what are the side effects" — and get a
conversational answer.

**Grounding, not deciding:** every answer is generated with the actual
verification result (status, composition, uses, side effects from
MedVerify's own database) given to the model as context it must not
contradict. The system prompt explicitly forbids the model from issuing
its own genuine/counterfeit verdict or specific dosing/prescribing advice
— those stay the job of the real verification logic and a real doctor/
pharmacist, respectively. Same setup, same graceful degradation, and same
untested-live-call caveat as the explanation feature above.

## Notes on the two CNN models

- **Anomaly detector (autoencoder)**: trained only on real genuine package
  photos. Flags packaging that looks statistically unlike anything it's
  seen — a defensible signal, but not a guarantee.
- **Synthetic classifier**: trained on real genuine images plus
  artificially corrupted copies standing in for "counterfeit" (blur, noise,
  color-shift, warp) — there's no real counterfeit-photo dataset behind it.
  Treat its output as a demo/portfolio signal, **not** a reliable real-world
  counterfeit detector, until retrained on actual counterfeit packaging
  photos. The API and frontend both label this clearly rather than
  presenting it as a definitive counterfeit determination.

## Deployment

### Free public deployment (Render + GitHub Pages)

This is the recommended path if you want a real public URL for free, no
paid services involved:

**1. Backend on Render.com (free tier)**

- Push this repo to a GitHub repository (public or private).
- On [render.com](https://render.com): **New → Blueprint**, pick your repo.
  Render reads `render.yaml` at the repo root and provisions the service
  automatically (it uses `backend/Dockerfile.render` — a lean image
  **without TensorFlow**, since no trained model files ship with this
  project anyway; see that file's comments for why).
- Wait for the build to finish, then note your backend's URL, e.g.
  `https://medverify-backend.onrender.com`.
- Check `https://<your-backend>.onrender.com/health` returns
  `{"status": "ok", ...}`.

**2. Frontend on GitHub Pages (free)**

- In `frontend/index.html`, change the `API_BASE` constant near the top of
  the `<script>` section to your Render backend URL from step 1 (no
  trailing slash).
- Commit and push that change.
- In your GitHub repo: **Settings → Pages → Source**, point it at the
  branch/folder containing `frontend/index.html` (or move that file to a
  `docs/` folder or a separate repo if you want a clean Pages root).
- Your frontend will be live at `https://<username>.github.io/<repo>/`.

**Free-tier trade-offs to know about:**
- Render's free web service **spins down after ~15 minutes of no
  traffic** — the next request cold-starts it back up, which can take
  30–60 seconds. Fine for a demo/portfolio project; not fine for something
  people need to respond instantly at all times.
- 750 free instance-hours/month on Render, shared across your free
  services on that account.
- The anomaly/classifier CNN checks are unavailable in this deployment
  (no TensorFlow, no trained model files) — they already report
  `"available": false` gracefully rather than erroring; core database +
  OCR/QR verification is fully unaffected.

### Local Docker Compose (self-hosted, all features)

`docker-compose.yml` and `backend/Dockerfile` (the full image, including
TensorFlow) are provided for local self-hosting with every feature enabled.
**These were written and reviewed but not build-tested in this
environment**, because no Docker daemon was available here — see Known
limitations. Review them before relying on them.

```bash
docker compose up --build
# backend:  http://localhost:8000
# frontend: http://localhost:8080
```

## Known limitations (honest assessment)

- **No authentication/authorization** on any endpoint — anyone who can
  reach the API can call it. Fine for a local/demo deployment; add auth
  (e.g. API keys or a proper auth provider) before exposing this publicly
  with real usage.
- **The synthetic classifier is not a real counterfeit detector** — see
  above. It was never claimed to be reliable, and this pass didn't change
  that (no real counterfeit-photo dataset was available to retrain it, and
  fabricating one wasn't an option).
- **The genuine-medicines dataset is a static local file**, not an
  authoritative government source. `NOT_FOUND` means "not in this dataset",
  not "confirmed counterfeit" — the API text already says so. Confirmed in
  testing: the curated genuine list has only 159 entries and the broader
  details database ~11,800 — real-world India alone has many thousands of
  branded medicines, so `NOT_FOUND` on a real, legitimate medicine is
  expected and common with this demo dataset. Expanding coverage requires
  either manually curating more verified entries from a trustworthy source
  or integrating a real licensed/official database — this project
  deliberately does not fabricate large amounts of "official-looking" data
  to fill this gap, since presenting invented data as authoritative would
  be worse than an honest coverage gap.
- **OCR struggles on reflective/glossy blister-foil photos** — confirmed in
  testing with a real medicine strip photo (glare + curved metallic surface
  + small embossed text defeated Tesseract even after contrast/sharpness
  preprocessing). For reliable OCR results, photograph the flat outer
  carton/box under even lighting rather than the blister foil, or use the
  "Verify by name" tab directly.
- **Docker config is untested** in this environment (no Docker daemon
  available) — reviewed for correctness but not built/run.
- **No HTTPS/TLS termination** is configured — that's expected to be
  handled by whatever you put in front of this (a reverse proxy, a
  platform's built-in TLS, etc.) in a real deployment.
- **CNN checks require TensorFlow**, which is a heavy dependency (~500MB+).
  If you don't need the anomaly/classifier checks, you can omit it — the
  rest of the app (database + OCR/QR verification) works without it, which
  this pass specifically made true (previously the app wouldn't even start).
- Automated tests were run **without** TensorFlow installed in this sandbox,
  so the CNN-loading and CNN-inference code paths themselves were exercised
  only via their "not available" branch, not with a real model loaded. The
  logic was read carefully and is defensively wrapped, but a real run with
  actual `.keras` model files would be worth doing before relying on those
  two checks in production.
