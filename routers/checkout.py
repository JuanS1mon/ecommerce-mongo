# Shim para compatibilidad con tests antiguos que importan `routers/checkout.py`
# Reexporta funciones desde la implementación actual en Projects.ecomerce.routes.checkout

try:
    from Projects.ecomerce.routes.checkout import process_checkout
except Exception:
    # Fallback minimal implementation (evita fallos en imports de tests aislados)
    async def process_checkout(data: dict, credentials=None):
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"success": False, "message": "checkout module not available"})

from fastapi.responses import JSONResponse

__all__ = ["process_checkout", "JSONResponse"]
