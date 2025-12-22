"""
Middleware de Autenticación para Rutas Protegidas
================================================

Este middleware maneja la autenticación puramente desde el backend:
1. Verifica tokens JWT antes de servir páginas HTML
2. Redirige automáticamente a login si no hay autenticación válida
3. Inyecta datos del usuario directamente en las plantillas
4. Sistema reutilizable para cualquier ruta que requiera autenticación

Uso:
    from Services.security.auth_middleware import require_auth_for_template
    
    @router.get("/admin")
    async def admin_page(request: Request, user_data: dict = Depends(require_auth_for_template)):
        return templates.TemplateResponse("admin.html", {
            "request": request,
            **user_data  # Incluye user, user_count, activities, etc.
        })
"""

import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer

from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from security.jwt_auth import verify_token, JWTAuthError

# Configurar logger
logger = logging.getLogger("auth_middleware")

# Configuración
LOGIN_PAGE_URL = "/loginpage"
security = HTTPBearer(auto_error=False)

class AuthenticationError(Exception):
    """Excepción para errores de autenticación en middleware"""
    pass

def extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extrae el token JWT de la petición.
    PRIORIDAD: Query params > Authorization header > cookies
    
    Args:
        request: Request de FastAPI
        
    Returns:
        Token JWT si se encuentra, None si no
    """
    logger.debug(f"Extracting token from request to: {request.url.path}")
    
    # 1. PRIORIDAD ALTA: Intentar desde query params (para navegadores que no manejan cookies)
    token = request.query_params.get("token")
    if token:
        logger.debug("Token encontrado en query params")
        return token
    
    # 2. Intentar desde Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        logger.debug("Token encontrado en Authorization header")
        return token
    
    # 3. Intentar desde cookies (primero ecommerce_token, luego access_token)
    token = request.cookies.get("ecommerce_token")
    if token:
        logger.debug("Token encontrado en cookie ecommerce_token")
        return token
    
    token = request.cookies.get("access_token")
    if token:
        logger.debug("Token encontrado en cookie access_token")
        return token

    logger.debug("No se encontró token en la petición")
    return None

async def get_user_from_token(token: str) -> EcomerceUsuarios:
    """
    Obtiene el usuario desde un token JWT validado usando MongoDB
    
    Args:
        token: Token JWT
        
    Returns:
        Usuario autenticado
        
    Raises:
        AuthenticationError: Si el token es inválido o el usuario no existe
    """
    try:
        logger.debug(f"Verificando token para autenticacion...")
        
        # Verificar token
        token_data = verify_token(token)
        logger.debug(f"Token valido para usuario: {token_data.username}")
        
        # Buscar usuario en MongoDB
        user = await EcomerceUsuarios.find_one(EcomerceUsuarios.email == token_data.username)
        
        if not user:
            raise AuthenticationError(f"Usuario no encontrado: {token_data.username}")
        
        if not user.activo:
            raise AuthenticationError(f"Usuario inactivo: {token_data.username}")
            
        logger.debug(f"Usuario encontrado: {user.email}")
        
        # Roles ya están en el modelo como lista
        logger.debug(f"Roles: {user.roles}")
        
        return user
        
    except Exception as e:
        logger.error(f"Error obteniendo usuario desde token: {str(e)}")
        raise AuthenticationError(f"Error de autenticacion: {str(e)}")
        
        logger.info(f"✅ Usuario autenticado exitosamente: {user.usuario} con roles {user.roles}")
        return user
        
    except JWTAuthError as e:
        raise AuthenticationError(f"Token inválido: {str(e)}")
    except Exception as e:
        logger.error(f"Error obteniendo usuario desde token: {str(e)}")
        raise AuthenticationError(f"Error de autenticación: {str(e)}")

async def get_dashboard_data(user: EcomerceUsuarios) -> Dict[str, Any]:
    """
    Obtiene datos para el dashboard del usuario autenticado usando MongoDB
    
    Args:
        user: Usuario autenticado
        
    Returns:
        Diccionario con datos del dashboard
    """
    try:
        logger.debug(f"Obteniendo datos del dashboard para: {user.email}")
        logger.debug(f"Roles del usuario: {user.roles}")
        
        # Contar usuarios totales en MongoDB
        user_count = await EcomerceUsuarios.count()
        
        # Obtener actividades recientes (últimos 5 usuarios registrados)
        recent_users = await EcomerceUsuarios.find().sort([("created_at", -1)]).limit(5).to_list()
        
        # Formatear actividades
        activities = []
        for recent_user in recent_users:
            activities.append({
                "usuario": {"nombre": recent_user.nombre},
                "action": "se registro en el sistema",
                "timestamp": "hace 2 horas"  # Podrías usar created_at real
            })
        
        # Calcular is_admin
        is_admin = "admin" in user.roles
        logger.debug(f"Calculando is_admin: 'admin' in {user.roles} = {is_admin}")
        
        dashboard_data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "nombre": user.nombre,
                "roles": user.roles,
                "active": user.active
            },
            "user_count": user_count,
            "activity_count": len(activities),
            "activities": activities,
            "is_admin": is_admin,
            "is_authenticated": True
        }
        
        logger.debug(f"Dashboard data generado - is_admin: {dashboard_data['is_admin']}")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error obteniendo datos del dashboard: {str(e)}")
        # Devolver datos mínimos en caso de error
        is_admin_fallback = "admin" in user.roles
        logger.debug(f"Fallback - is_admin: {is_admin_fallback}")
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "nombre": user.nombre,
                "roles": user.roles,
                "active": user.active
            },
            "user_count": 0,
            "activity_count": 0,
            "activities": [],
            "is_admin": is_admin_fallback,
            "is_authenticated": True
        }

async def require_auth_for_template(
    request: Request
) -> Dict[str, Any]:
    """
    Dependency que requiere autenticación para servir plantillas HTML.
    
    Si no hay autenticación válida, redirige automáticamente a la página de login.
    Si hay autenticación válida, devuelve datos completos del usuario y dashboard.
    
    Args:
        request: Request de FastAPI
        db: Sesión de base de datos
        
    Returns:
        Diccionario con datos del usuario y dashboard para la plantilla
        
    Raises:
        HTTPException: Redirige a login si no hay autenticación válida
    """
    logger.info(f"Verificando autenticación para: {request.url.path}")
    
    # Extraer token de la petición
    token = extract_token_from_request(request)
    
    if not token:
        logger.warning("No se encontró token en la petición")
        return_url = str(request.url)
        login_url = f"{LOGIN_PAGE_URL}?next={return_url}"
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": login_url}
        )
    
    try:
        # Verificar token y obtener usuario
        user = await get_user_from_token(token)
        
        # Obtener datos del dashboard
        dashboard_data = await get_dashboard_data(user)
        
        logger.info(f"Autenticacion exitosa para usuario: {user.email}")
        return dashboard_data
        
    except AuthenticationError as e:
        logger.warning(f"Error de autenticación: {str(e)}")
        return_url = str(request.url)
        login_url = f"{LOGIN_PAGE_URL}?next={return_url}"
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": login_url}
        )
    except Exception as e:
        logger.error(f"Error inesperado procesando usuario: {str(e)}")
        return_url = str(request.url)
        login_url = f"{LOGIN_PAGE_URL}?next={return_url}"
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": login_url}
        )

async def require_admin_for_template(
    request: Request
) -> Dict[str, Any]:
    """
    Dependency que requiere rol de administrador para servir plantillas HTML.
    
    Combina require_auth_for_template con verificación de rol admin.
    
    Args:
        request: Request de FastAPI
        db: Sesión de base de datos
        
    Returns:
        Diccionario con datos del usuario admin y dashboard
        
    Raises:
        HTTPException: Redirige a login o muestra error 403 si no es admin
    """
    logger.debug(f"🚪 require_admin_for_template iniciado para: {request.url.path}")
    
    # Primero verificar autenticación
    user_data = await require_auth_for_template(request)
    
    logger.debug(f"👤 Usuario autenticado: {user_data['user']['usuario']}")
    logger.debug(f"🎭 Roles del usuario: {user_data['user'].get('roles', [])}")
    logger.debug(f"🔐 is_admin en user_data: {user_data.get('is_admin', False)}")
    
    # Verificar rol de admin
    if not user_data.get("is_admin", False):
        logger.warning(f"❌ Usuario {user_data['user']['usuario']} intentó acceder a área de admin sin permisos")
        logger.warning(f"   Roles actuales: {user_data['user'].get('roles', [])}")
        logger.warning(f"   is_admin: {user_data.get('is_admin', False)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso de administrador requerido"
        )
    
    logger.info(f"✅ Acceso de admin autorizado para: {user_data['user']['usuario']}")
    return user_data

# Función de utilidad para verificar roles específicos
def require_role_for_template(required_role: str):
    """
    Factory function para crear dependencies que requieren roles específicos
    
    Args:
        required_role: Rol requerido (ej: "admin", "user", "moderator")
        
    Returns:
        Dependency function
    """
    async def check_role(
        request: Request
    ) -> Dict[str, Any]:
        # Verificar autenticación
        user_data = await require_auth_for_template(request)
        
        # Verificar rol específico
        user_roles = user_data['user'].get('roles', [])
        if required_role.lower() not in user_roles:
            logger.warning(
                f"Usuario {user_data['user']['usuario']} intentó acceder sin rol {required_role}. "
                f"Roles actuales: {user_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{required_role}' requerido"
            )
        
        return user_data
    
    return check_role

# Para compatibilidad con el sistema anterior, mantener estas funciones simples

async def get_authenticated_user(request: Request) -> EcomerceUsuarios:
    """
    Función simple que devuelve el usuario autenticado (sin datos de dashboard).
    Útil para APIs que solo necesitan el usuario.
    """
    logger.debug(f"get_authenticated_user called for path: {request.url.path}")
    token = extract_token_from_request(request)
    logger.debug(f"Token extracted: {'YES' if token else 'NO'}")

    if not token:
        logger.warning("No token found in request")
        raise HTTPException(status_code=401, detail="Token requerido")

    try:
        user = await get_user_from_token(token)
        logger.debug(f"User authenticated: {getattr(user, 'usuario', getattr(user, 'email', 'unknown'))}")
        return user
    except AuthenticationError as e:
        logger.error(f"Error authenticating user: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")


async def require_auth_for_template(request: Request) -> Dict[str, Any]:
    """
    Dependency que requiere autenticación para servir plantillas HTML.
    Si no hay autenticación válida, devuelve una Redirección a la página de login.
    """
    token = extract_token_from_request(request)
    if not token:
        return RedirectResponse(LOGIN_PAGE_URL)

    try:
        user = await get_user_from_token(token)
    except AuthenticationError:
        return RedirectResponse(LOGIN_PAGE_URL)

    dashboard = await get_dashboard_data(user)
    return dashboard


def require_role_api(roles: list):
    """
    Dependency factory para endpoints de API que requieren roles específicos.
    Compatible con autenticación por cookies, headers y query params.
    """
    async def check_role(request: Request):
        # Obtener usuario autenticado usando el sistema de cookies/headers/query
        user = await get_authenticated_user(request)

        # Verificar roles del usuario
        user_roles = []
        if hasattr(user, 'roles') and user.roles:
            if isinstance(user.roles, list):
                for role in user.roles:
                    if isinstance(role, str):
                        user_roles.append(role.lower())
                    elif hasattr(role, 'nombre'):
                        user_roles.append(role.nombre.lower())
                    else:
                        user_roles.append(str(role).lower())
            else:
                user_roles = [str(user.roles).lower()]

        has_required_role = any(role.lower() in user_roles for role in roles)
        if not has_required_role:
            logger.warning(
                f"Usuario {getattr(user,'usuario',getattr(user,'email','unknown'))} intentó acceder sin roles {roles}. Roles actuales: {user_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de estos roles: {roles}"
            )

        return user

    return check_role
