#!/usr/bin/env python3
import sys
import subprocess
import time
from pathlib import Path

log_req = Path('/home/site/wwwroot/install_requirements.log')
log_uv = Path('/home/site/wwwroot/install_uvicorn_runtime.log')

def run(cmd, logpath, retries=1, sleep=5):
    for i in range(1, retries+1):
        with open(logpath, 'a') as f:
            f.write(f"\n--- RUN (attempt {i}) $ {' '.join(cmd)} ---\n")
            f.flush()
            try:
                subprocess.check_call(cmd, stdout=f, stderr=f)
                f.write('\n--- SUCCESS ---\n')
                return True
            except subprocess.CalledProcessError as e:
                f.write(f'--- FAIL: {e} ---\n')
                if i < retries:
                    time.sleep(sleep)
    return False

# Ensure pip exists
try:
    subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    # fallback: try bootstrap get-pip.py (best-effort)
    try:
        subprocess.check_call([sys.executable, "-c", "import ensurepip; ensurepip.bootstrap()"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

# Install requirements synchronously (if present)
reqs = Path('/home/site/wwwroot/requirements.txt')
if reqs.exists():
    run([sys.executable, "-m", "pip", "install", "-r", str(reqs)], str(log_req), retries=3, sleep=5)

# Ensure uvicorn present
try:
    import uvicorn  # type: ignore
    print('[ensure_uvicorn] uvicorn already installed')
except Exception:
    print('[ensure_uvicorn] uvicorn missing — instalando uvicorn==0.30.0...')
    run([sys.executable, "-m", "pip", "install", "uvicorn==0.30.0"], str(log_uv), retries=3, sleep=5)
    print('[ensure_uvicorn] uvicorn install attempt finished')

# Report installed packages (short)
try:
    out = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    print('[ensure_uvicorn] pip freeze (head):')
    for l in out.decode().splitlines()[:20]:
        print('  ' + l)
except Exception:
    pass

