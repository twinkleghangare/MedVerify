# **MedVerify**

AI-assisted medicine verification using database matching, QR/barcode scanning, and OCR.

> **Note:** MedVerify is an academic prototype, not a certified medicine-authentication system. Results depend on available datasets and must not replace professional verification.

## **Features**

- Verify medicine names and manufacturers against local datasets.
- Scan medicine packages using QR/barcode decoding and OCR.
- Use fuzzy matching to identify possible database matches.
- Optional CNN-based image analysis.
- Groq-powered result explanations and medicine Q&A.
- FastAPI backend with HTML, CSS, and JavaScript frontend.
- Optional Android app using Capacitor.

## **Tech Stack**

Python, FastAPI, Pandas, OpenCV, Pillow, Tesseract OCR, pyzbar, TensorFlow/Keras, Groq API, HTML, CSS, JavaScript, Capacitor.

## **Project Structure**

```
medverify/
├── backend/
│   ├── app/
│   ├── data/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── index.html
├── mobile-app/
├── docker-compose.yml
└── README.md
```

## **Setup**

1. Install Python and system dependencies: Tesseract OCR and ZBar.
2. Add the required datasets to `backend/data/`:
   - `Real_Medicines_dataset.xlsx`
   - `Banned_Pharma_Companies.xlsx`
   - `Medicine_Details.csv`
3. (Optional) Copy `backend/.env.example` to `backend/.env` and configure environment variables.
4. Start the backend.

**Windows**

```
start_backend.bat
```

**macOS/Linux**

```
chmod +x start_backend.sh
./start_backend.sh
```

Open `frontend/index.html` in your browser.

Backend health check: `http://localhost:8000/health`

## **API Endpoints**

| Method | Endpoint        | Description                             |
| ------ | --------------- | --------------------------------------- |
| GET    | `/health`       | API and dependency status               |
| POST   | `/verify/text`  | Verify medicine details                 |
| POST   | `/verify/image` | Scan and verify a package image         |
| POST   | `/chat`         | Ask questions about a verified medicine |

## **Testing**

```
cd backend
pip install -r requirements-dev.txt
pytest
```

The project notes report **34 tests passed** in the recorded environment. CNN inference with trained models was not validated in that test run.

## **Deployment**

- **Render:** Deploy the backend using the repository's Render configuration, if present.
- **GitHub Pages:** Host the frontend and configure `API_BASE` to point to the deployed backend.
- **Docker:** Run `docker compose up --build` if the Compose configuration is available and validated.

## **Limitations**

- Results depend on the coverage and quality of local medicine datasets.
- `NOT_FOUND` does not mean a medicine is counterfeit.
- `GENUINE` indicates a curated-dataset match, not proof of package authenticity.
- OCR may be less accurate on reflective or curved packaging.
- CNN checks are optional; the synthetic classifier is experimental.
- Groq features require a valid API key.
- Authentication and authorization are not currently implemented.
