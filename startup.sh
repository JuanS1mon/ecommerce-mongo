#!/bin/bash
echo "🔧 Iniciando instalación de dependencias..."
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencias instaladas"
echo "🚀 Iniciando aplicación con Uvicorn..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120
