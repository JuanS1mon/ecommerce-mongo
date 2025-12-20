from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
import logging
import os
import httpx

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("uvicorn.error")
    async def dispatch(self, request, call_next):
        import time
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        user_agent = headers.get("user-agent", "unknown")
        self.logger.info(f"🌐 {method} {url}")
        self.logger.info(f"   📍 IP: {client_ip}")
        self.logger.info(f"   🔍 User-Agent: {user_agent[:100]}...")
        self.logger.debug(f"📍 Encabezados: {headers}")
        self.logger.debug(f"📍 Cookies: {request.cookies}")
        auth_header = request.headers.get("Authorization")
        if auth_header:
            self.logger.debug(f"🔑 Encabezado Authorization detectado: {auth_header}")
        else:
            self.logger.debug("❌ Encabezado Authorization no presente")
        access_token_cookie = request.cookies.get("access_token")
        if access_token_cookie:
            self.logger.debug(f"🔑 Cookie access_token detectada: {access_token_cookie}")
        else:
            self.logger.debug("❌ Cookie access_token no presente")
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            self.logger.info(f"✅ {method} {url} -> {response.status_code}")
            self.logger.info(f"   ⏱️  Tiempo: {process_time:.3f}s")
            self.logger.info(f"   📤 Content-Type: {response.headers.get('content-type', 'unknown')}")
            response.headers["X-Process-Time"] = str(process_time)
        except Exception as e:
            process_time = time.time() - start_time
            self.logger.error(f"❌ {method} {url} -> ERROR")
            self.logger.error(f"   ⏱️  Tiempo: {process_time:.3f}s")
            self.logger.error(f"   💥 Error: {str(e)}")
            raise
        return response

class FrontendRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        from config import FRONTEND_URL
        frontend_prefix = "/frontend"
        if request.url.path.startswith(frontend_prefix):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{FRONTEND_URL}{request.url.path[len(frontend_prefix):]}")
                    if response.status_code == 200:
                        return RedirectResponse(url=f"{FRONTEND_URL}{request.url.path[len(frontend_prefix):]}")
            except httpx.RequestError:
                return JSONResponse(status_code=503, content={"detail": "El frontend está caído. Por favor, intenta más tarde."})
        return await call_next(request)

class CustomErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        excluded_paths = ["/docs", "/redoc", "/openapi.json"]
        # No interceptar errores en rutas de API
        if request.url.path.startswith("/auth/") or request.url.path.startswith("/ecomerce/") or request.url.path.startswith("/ecommerce/") or request.url.path.startswith("/api/"):
            return response
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return response
        static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
        if response.status_code == 404:
            return FileResponse(os.path.join(static_dir, '404.html'), status_code=404)
        elif response.status_code == 401:
            return FileResponse(os.path.join(static_dir, '401.html'), status_code=401)
        elif response.status_code == 403:
            return FileResponse(os.path.join(static_dir, '403.html'), status_code=403)
        elif response.status_code == 405:
            return FileResponse(os.path.join(static_dir, '405.html'), status_code=405)
        elif response.status_code == 500:
            return FileResponse(os.path.join(static_dir, '500.html'), status_code=500)
        elif response.status_code == 503:
            return FileResponse(os.path.join(static_dir, '503.html'), status_code=503)
        elif response.status_code == 505:
            return FileResponse(os.path.join(static_dir, '505.html'), status_code=505)
        return response

class UserTemplateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if isinstance(response, HTMLResponse) or getattr(response, "media_type", None) == "text/html":
            try:
                if hasattr(response, "context") and isinstance(response.context, dict):
                    if "user" not in response.context:
                        pass
            except Exception as e:
                logging.getLogger("main").error(f"Error al procesar middleware de templates: {e}")
        return response

class DebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger = logging.getLogger("main")
        logger.debug("🔍 Middleware procesando: %s %s", request.method, request.url)
        logger.debug("📍 Encabezados: %s", request.headers)
        logger.debug("📍 Cookies: %s", request.cookies)
        auth_header = request.headers.get("Authorization")
        if auth_header:
            logger.debug("🔑 Encabezado Authorization detectado: %s", auth_header)
        else:
            logger.debug("❌ Encabezado Authorization no presente")
        access_token_cookie = request.cookies.get("access_token")
        if access_token_cookie:
            logger.debug("🔑 Cookie access_token detectada: %s", access_token_cookie)
        else:
            logger.debug("❌ Cookie access_token no presente")
        response = await call_next(request)
        logger.debug("📤 Respuesta: %s %s", response.status_code, response.headers.get("Content-Type"))
        return response
