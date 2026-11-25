#!/bin/bash
echo "============================================"
echo "  MedVerify Backend - Setup and Start"
echo "============================================"
echo ""

cd "$(dirname "$0")/backend"

if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/3] Virtual environment already exists, skipping."
fi

echo "[2/3] Installing dependencies (this can take a few minutes first time)..."
source venv/bin/activate
pip install -r requirements.txt

echo "[3/3] Starting server at http://localhost:8000 ..."
echo ""
echo "Leave this terminal open while using MedVerify."
echo "Press CTRL+C to stop the server."
echo ""
uvicorn app.main:app --reload --port 8000
