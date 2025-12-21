#!/bin/bash
echo "🔧 Iniciando instalación de dependencias..."
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencias instaladas"
echo "🚀 Iniciando aplicación..."
gunicorn -k uvicorn.workers.UvicornWorker main:app --bind=0.0.0.0:8000 --timeout=120 --log-level=info
