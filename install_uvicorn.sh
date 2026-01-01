#!/bin/bash
set -e
if ! python3 -m pip --version >/dev/null 2>&1; then
  echo "[install_uvicorn] pip not found, attempting get-pip.py bootstrap"
  curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py || { echo "curl failed"; exit 1; }
  python3 /tmp/get-pip.py --no-warn-script-location || { echo "get-pip.py failed"; exit 1; }
  rm -f /tmp/get-pip.py
fi
python3 -m pip install --upgrade pip setuptools wheel || true
python3 -m pip install uvicorn==0.30.0 --no-cache-dir
echo "[install_uvicorn] done"
