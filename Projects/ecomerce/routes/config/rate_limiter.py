"""
Limitador de peticiones simple en memoria para endpoints críticos.
No requiere librerías externas. Funciona por IP y ventana temporal.
No es adecuado para despliegues con múltiples procesos/nodos (usar Redis para producción).
"""
from fastapi import Request, HTTPException, status
from fastapi import Depends
from time import time
from threading import Lock
from typing import Callable

_lock = Lock()
# Estructura: {key: (window_start_ts, count)}
_rate_store = {}


def rate_limit_dependency(limit: int = 10, window_seconds: int = 60) -> Callable:
    """
    Retorna una dependencia que valida el rate limit por IP.
    Uso en endpoint: _rl = Depends(rate_limit_dependency(10,60))
    """
    def _dependency(request: Request):
        try:
            ip = request.client.host or "anonymous"
        except Exception:
            ip = "anonymous"
        key = f"rl:{ip}"
        now = time()
        with _lock:
            window_start, count = _rate_store.get(key, (now, 0))
            if now - window_start > window_seconds:
                window_start = now
                count = 1
            else:
                count += 1
            _rate_store[key] = (window_start, count)
            if count > limit:
                ttl = int(window_seconds - (now - window_start))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {ttl} seconds."
                )
        return True

    return _dependency
