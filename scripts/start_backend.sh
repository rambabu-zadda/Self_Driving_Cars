#!/usr/bin/env bash
cd backend
python -m venv .venv || true
source .venv/bin/activate
pip install -r requirements-docker.txt
uvicorn app:app --host 0.0.0.0 --port 8000
