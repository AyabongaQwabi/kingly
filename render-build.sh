#!/usr/bin/env bash
set -euo pipefail

echo "Building frontend…"
cd frontend
npm ci
npm run build

echo "Installing backend deps…"
cd ../backend
pip install -r requirements.txt

echo "Build complete."

