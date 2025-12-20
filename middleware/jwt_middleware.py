# ============================================================================
# JWTMiddleware - Middleware de autenticación JWT para FastAPI
# ============================================================================
# Este archivo implementa un middleware que protege rutas de la aplicación (tanto API como HTML) exigiendo un token JWT válido.
#
# Características principales:
# - Intercepta todas las peticiones entrantes y verifica si la ruta requiere autenticación.
# - Extrae el token JWT desde el header Authorization, query param (?token=...) o cookie (access_token).
# - Si la ruta es protegida y el token es válido, permite el acceso y adjunta los datos del usuario autenticado al request.
# - Si la ruta es protegida y el token es inválido o falta, responde con 401 (API) o redirige a /login (HTML).
# - Permite definir fácilmente qué rutas son públicas y cuáles protegidas.
# - Facilita la integración de seguridad robusta y centralizada, desacoplando la lógica de autenticación de los endpoints individuales.
#
# Uso recomendado:
# - Añadir este middleware en main.py para proteger todas las rutas sensibles de la app.
# - Mantener la lista de rutas protegidas y públicas en este archivo para un control centralizado.
# - Usar las funciones utilitarias para consultar el usuario autenticado desde los endpoints si es necesario.
# ============================================================================

import logging
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from security.jwt_auth import verify_token, JWTAuthError

logger = logging.getLogger("jwt_middleware")

class JWTMiddleware(BaseHTTPMiddleware):
    """
    Middleware de autenticación JWT para FastAPI.
    - Protege rutas API y HTML.
    - Extrae el token JWT desde header, query param o cookie.
    - Si la ruta es protegida y el token es válido, permite el acceso.
    - Si la ruta es protegida y el token es inválido o falta, responde con 401 (API) o redirige a /login (HTML).
    """
    def __init__(self, app, protected_paths: list = None):
        """
        Inicializa el middleware.
        - app: instancia de la aplicación FastAPI.
        - protected_paths: lista de prefijos de rutas que requieren autenticación.
        """
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/admin",              # Panel admin HTML
            "/analisis/admin",     # Página de análisis admin
            "/generar",            # Generador de código
            "/usuarios_admin",     # Gestión usuarios HTML
            "/admin/data",         # API de datos admin protegida
            "/analisis/admin/data",  # API de datos análisis admin protegida
            "/analisis/nuevo/data",  # API de datos nuevo análisis protegida
            "/api/admin", 
            "/api/users",
            "/api/protected"
        ]
        self.public_paths = [
            "/", "/auth", "/auth/login", "/auth/logout", "/auth/me", "/auth/verify-token", "/auth/test-user", "/login", "/logout", "/docs", "/redoc", "/openapi.json", "/static", "/favicon.ico", "/loginpage",
            "/ecomerce", "/ecommerce"  # Agregar rutas de ecommerce como públicas
        ]

    def is_protected_path(self, path: str) -> bool:
        """
        Determina si una ruta requiere autenticación.
        Devuelve True si la ruta está en la lista de protegidas y no es pública.
        """
        for public_path in self.public_paths:
            if public_path == "/" and path == "/":
                return False
            elif public_path != "/" and path.startswith(public_path):
                return False
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extrae el token JWT de la petición, buscando en:
        1. Header Authorization
        2. Query param (?token=...)
        3. Cookie (access_token)
        Devuelve el token si lo encuentra, o None si no está presente.
        """
        # 1. Authorization header
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
        # 2. Query param
        token = request.query_params.get("token")
        if token:
            return token
        # 3. Cookie
        token = request.cookies.get("access_token")
        if token:
            return token
        return None

    def is_html_request(self, request: Request) -> bool:
        """
        Detecta si la petición espera una respuesta HTML (usado para decidir si redirigir a login).
        """
        accept = request.headers.get("accept", "")
        return "text/html" in accept.lower()

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesa cada petición entrante:
        - Si la ruta es protegida, exige un JWT válido.
        - Si el token es válido, adjunta los datos del usuario al request.
        - Si el token es inválido o falta, responde con 401 (API) o redirige a login (HTML).
        - Si la ruta es pública, deja pasar la petición normalmente.
        """
        path = request.url.path
        method = request.method
        logger.debug(f"Procesando {method} {path}")
        if self.is_protected_path(path):
            logger.debug(f"Ruta protegida detectada: {path}")
            token = self.extract_token_from_request(request)
            if not token:
                logger.warning(f"Acceso denegado a {path}: No se proporcionó token")
                if self.is_html_request(request):
                    # Redirigir a login si es HTML
                    return RedirectResponse(url=f"/loginpage?next={path}", status_code=302)
                else:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Token de acceso requerido",
                            "path": path,
                            "instruction": "Incluya el token JWT en el header Authorization: Bearer <token> o como ?token=..."
                        },
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            try:
                token_data = verify_token(token)
                logger.debug(f"Token verificado exitosamente para usuario: {getattr(token_data, 'username', None)}")
                request.state.token_data = token_data
                request.state.authenticated = True
            except JWTAuthError as e:
                logger.warning(f"Token inválido para {path}: {e.detail}")
                if self.is_html_request(request):
                    return RedirectResponse(url=f"/login?next={path}", status_code=302)
                else:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={
                            "detail": e.detail,
                            "path": path
                        },
                        headers=e.headers
                    )
            except Exception as e:
                logger.error(f"Error inesperado verificando token: {str(e)}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "detail": "Error interno verificando autenticación",
                        "path": path
                    }
                )
        else:
            logger.debug(f"Ruta pública: {path}")
            request.state.authenticated = False
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Error procesando petición: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Error interno del servidor"}
            )

# Funciones de utilidad para otros módulos

def get_middleware_auth_info(request: Request) -> dict:
    """
    Devuelve información de autenticación extraída por el middleware para la petición actual.
    Útil para endpoints que quieran saber si el usuario está autenticado y su username.
    """
    if not getattr(request.state, 'authenticated', False):
        return {}
    token_data = getattr(request.state, 'token_data', None)
    if not token_data:
        return {}
    return {
        "authenticated": True,
        "username": getattr(token_data, 'username', None)
    }

def is_request_authenticated(request: Request) -> bool:
    """
    Devuelve True si la petición actual fue autenticada por el middleware.
    """
    return getattr(request.state, 'authenticated', False)
