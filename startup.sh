#!/bin/bash
set -e

LOG() { echo "[startup] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

LOG "🔧 Iniciando instalación de dependencias (requirements.txt)..."
# Asegurar que trabajamos desde el directorio de la app (donde está main.py)
cd /home/site/wwwroot || true
LOG "Working directory: $(pwd)"
# Detectar el python que estará disponible en runtime y usarlo para pip
PYTHON=$(command -v python || command -v python3 || echo python)
LOG "Usando ejecutable Python: $($PYTHON -c 'import sys; print(sys.executable)')"
# Upgade pip con el mismo intérprete
$PYTHON -m pip install --upgrade pip || true
if [ -f requirements.txt ]; then
  LOG "Instalando dependencias (sincrónico, puede tardar): $PYTHON -m pip install -r requirements.txt"
  # Intentar instalar hasta 3 veces y volcar salida a install_requirements.log
  if [ -f /home/site/wwwroot/install_requirements.log ]; then
    rm -f /home/site/wwwroot/install_requirements.log || true
  fi
  for i in 1 2 3; do
    LOG "Instalación intento $i..."
    $PYTHON -m pip install -r requirements.txt >> /home/site/wwwroot/install_requirements.log 2>&1 && break || LOG "Intento $i falló; ver /home/site/wwwroot/install_requirements.log"
    sleep 5
  done
  LOG "install_requirements.log (últimas 200 líneas):"; tail -n 200 /home/site/wwwroot/install_requirements.log || true
else
  LOG "⚠️ requirements.txt no encontrado; continuando"
fi

# Asegurar que ejecutamos desde el directorio del sitio
LOG "🗂️ Cambiando CWD a /home/site/wwwroot"
cd /home/site/wwwroot || LOG "⚠️ No se pudo cambiar a /home/site/wwwroot; continuando en CWD actual"
LOG "PWD: $(pwd)"

# Asegurar PYTHONPATH para que las importaciones desde /home/site/wwwroot funcionen
export PYTHONPATH=/home/site/wwwroot:${PYTHONPATH:-}
LOG "PYTHONPATH: $PYTHONPATH"

# Verificar e instalar uvicorn en tiempo de ejecución si hace falta (registro en install_uvicorn_runtime.log)
LOG "🔧 Comprobando uvicorn en runtime"
if $PYTHON -c 'import uvicorn' >/dev/null 2>&1; then
  LOG "uvicorn presente en runtime"
else
  LOG "uvicorn ausente: intentando instalar uvicorn[standard]==0.30.0 en runtime (puede tardar)"
  $PYTHON -m pip install --no-cache-dir "uvicorn[standard]==0.30.0" >> /home/site/wwwroot/install_uvicorn_runtime.log 2>&1 || LOG "⚠️ Falló la instalación runtime de uvicorn; revisar install_uvicorn_runtime.log"
  LOG "install_uvicorn_runtime.log (últimas 50 líneas):"; tail -n 50 /home/site/wwwroot/install_uvicorn_runtime.log || true
fi

# Preflight: comprobar que podemos importar `main` desde /home/site/wwwroot y recopilar diagnósticos completos
LOG "🔎 Preflight import: comprobando que 'main' es importable y generando diagnóstico en /home/site/wwwroot/import_check.log"
# Esperar hasta que el preflight encuentre IMPORT_OK o agotar timeout
start_time=$(date +%s)
timeout=180  # segundos
while true; do
  echo "--- ls -la /home/site/wwwroot ---"; ls -la /home/site/wwwroot 2>&1
  echo "--- Ejecutando diagnóstico Python ($PYTHON) ---"
  $PYTHON - <<'PY' > /home/site/wwwroot/import_check.log 2>&1
import sys, os, pkgutil, traceback
# Asegurar que el site root está al inicio del path
sys.path.insert(0, '/home/site/wwwroot')
print('sys.executable=%s' % sys.executable)
print('cwd=%s' % os.getcwd())
print('__file__=%s' % __file__)
print('sys.path=%s' % sys.path)
try:
    print('ls=%s' % os.listdir('/home/site/wwwroot')[:200])
except Exception as e:
    print('ls error:', e)
print('modules=%s' % sorted([m.name for m in pkgutil.iter_modules(path=['/home/site/wwwroot'])])[:500])
try:
    import main
    print('IMPORT_OK')
except Exception:
    traceback.print_exc()
    raise SystemExit(1)
PY
  if [ $? -eq 0 ]; then
    break
  fi
  now=$(date +%s)
  elapsed=$((now - start_time))
  if [ $elapsed -ge $timeout ]; then
    LOG "ERROR: Preflight no pudo importar 'main' después de ${timeout}s; revisar /home/site/wwwroot/import_check.log"
    tail -n 200 /home/site/wwwroot/import_check.log || true
    break
  fi
  LOG "Preflight: import falló, reintentando en 5s (elapsed ${elapsed}s)..."
  sleep 5
done
LOG "Preflight: content of import_check.log:"; tail -n 200 /home/site/wwwroot/import_check.log || true

# Arranque: preferimos arrancar con python3 -m uvicorn (usa el interprete donde instalamos uvicorn)
LOG "🚀 Intentando arrancar aplicación con python3 -m uvicorn (entrypoint: main:app)"
if python3 -c 'import uvicorn' >/dev/null 2>&1; then
  exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120
else
  LOG "uvicorn no disponible en python3, intentando gunicorn (uvicorn worker) si está disponible"
  if command -v gunicorn >/dev/null 2>&1; then
    exec gunicorn -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app
  else
    LOG "ERROR: No se encontró gunicorn ni uvicorn. Aborting"
    exit 1
  fi
fi
