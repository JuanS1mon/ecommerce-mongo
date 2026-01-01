"""
Router de autenticación para el panel de administración
Maneja login, logout y verificación de credenciales admin
Migrado a MongoDB con Beanie
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from datetime import timedelta
import logging

from security.jwt_auth import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from security.security import verificar_clave
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.utils.template_helpers import render_admin_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Auth"])


@router.get("/login", response_class=HTMLResponse, name="admin_login_page")
async def admin_login_page(request: Request, next: str = None):
    """
    Página de login del panel de administración
    
    Args:
        request: Request object
        next: URL a la que redirigir después del login exitoso
    """
    return render_admin_template("login.html", request, next=next or "/admin/dashboard")


@router.post("/api/login", name="admin_login_api")
async def admin_login_api(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/admin/dashboard")
):
    """
    API de login para administradores
    Verifica credenciales usando MongoDB con Beanie
    
    Args:
        username: Nombre de usuario
        password: Contraseña
        next: URL de redirección después del login
        
    Returns:
        JSONResponse con token y datos del usuario
    """
    try:
        # Obtener información del cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Buscar usuario en MongoDB
        usuario = await AdminUsuarios.find_one(AdminUsuarios.usuario == username)
        
        if not usuario:
            logger.warning(f"❌ Intento de login admin fallido - Usuario no existe: {username} desde {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Verificar si está activo
        if not usuario.activo:
            logger.warning(f"❌ Intento de login admin fallido - Usuario inactivo: {username} desde {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        # Verificar contraseña
        if not verificar_clave(password, usuario.clave_hash):
            logger.warning(f"❌ Intento de login admin fallido - Contraseña incorrecta: {username} desde {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Crear token JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": usuario.usuario, "user_id": str(usuario.id)},
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Login admin exitoso: {username} desde {client_ip}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Login exitoso",
                "access_token": access_token,
                "token_type": "bearer",
                "redirect_url": next,
                "user": {
                    "id": str(usuario.id),
                    "username": usuario.usuario,
                    "nombre": usuario.nombre,
                    "email": usuario.mail
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en login admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("/logout", name="admin_logout")
async def admin_logout(request: Request):
    """
    Logout del panel de administración
    El cliente debe eliminar el token
    """
    logger.info("Admin logout")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Logout exitoso",
            "redirect_url": "/admin/login"
        }
    )
