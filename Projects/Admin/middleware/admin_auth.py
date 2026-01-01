"""
Middleware de autenticación para el panel de administración
Valida que el usuario sea admin usando MongoDB con Beanie
"""
import logging
from typing import Optional, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.responses import RedirectResponse

from security.jwt_auth import get_current_admin_user, get_optional_admin_user
# TEMP COMENTADO para migración MongoDB: from db.schemas.config.Usuarios import UserDB
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios

logger = logging.getLogger(__name__)


async def require_admin(
    current_user: AdminUsuarios = Depends(get_current_admin_user)
) -> AdminUsuarios:
    """
    Middleware que valida que el usuario autenticado sea administrador
    
    Args:
        current_user: Usuario admin obtenido del token JWT
        
    Returns:
        AdminUsuarios: Modelo del usuario admin
        
    Raises:
        HTTPException: Si el usuario no es admin o no existe
    """
    # Ya viene validado desde get_current_admin_user
    logger.info(f"Acceso admin autorizado: {current_user.usuario}")
    return current_user


async def get_optional_admin(
    current_user: Optional[AdminUsuarios] = Depends(get_optional_admin_user)
) -> Optional[AdminUsuarios]:
    """
    Versión opcional del require_admin que no lanza excepción si no es admin
    Útil para endpoints que quieren mostrar contenido diferente según el rol
    
    Args:
        current_user: Usuario admin (opcional)
        
    Returns:
        Optional[AdminUsuarios]: Usuario si es admin, None en caso contrario
    """
    return current_user


async def require_admin_or_redirect(
    request: Request,
    current_user: Optional[AdminUsuarios] = Depends(get_optional_admin_user)
) -> AdminUsuarios:
    """
    Middleware que valida admin o redirige al login
    Útil para páginas HTML que necesitan autenticación
    
    Args:
        request: Request object
        current_user: Usuario admin (opcional)
        
    Returns:
        AdminUsuarios: Usuario admin autenticado
        
    Raises:
        HTTPException: Con redirección si no está autenticado
    """
    if not current_user:
        # No autenticado, redirigir al login
        login_url = f"/admin/login?next={request.url.path}"
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": login_url}
        )
    
    return current_user

