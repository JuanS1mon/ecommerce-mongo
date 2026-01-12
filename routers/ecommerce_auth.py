# routers/ecommerce_auth.py
"""
Router de autenticación para usuarios de ecommerce/servicios
Maneja login, registro y verificación de usuarios
"""
import logging
from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from security.ecommerce_auth import (
    authenticate_ecommerce_user,
    register_ecommerce_user,
    get_current_ecommerce_user,
    create_access_token,
    change_ecommerce_user_password,
    log_ecommerce_auth_event
)

# Configurar logger
logger = logging.getLogger(__name__)

# Crear router
router = APIRouter()

# Modelos Pydantic para las requests
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/auth/register")
async def register_user(request: RegisterRequest):
    """
    Registra un nuevo usuario de ecommerce/servicios
    """
    try:
        # Convertir request a dict
        user_data = request.dict()

        # Registrar usuario
        result = await register_ecommerce_user(user_data)

        if not result:
            log_ecommerce_auth_event("REGISTER_FAILED", {"email": request.email}, "WARNING")
            raise HTTPException(
                status_code=400,
                detail="Error al registrar usuario. Verifique los datos e intente nuevamente."
            )

        log_ecommerce_auth_event("REGISTER_SUCCESS", {"email": request.email}, "INFO")

        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": "Usuario registrado exitosamente",
                "user": result
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en registro de usuario: {str(e)}")
        log_ecommerce_auth_event("REGISTER_ERROR", {"email": request.email, "error": str(e)}, "ERROR")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/auth/login")
async def login_user(request: LoginRequest):
    """
    Autentica un usuario de ecommerce/servicios
    """
    try:
        logger.info(f"🔐 Login attempt for email: {request.email}")
        logger.info(f"📝 Password length: {len(request.password) if request.password else 0}")

        # Autenticar usuario
        user = await authenticate_ecommerce_user(request.email, request.password)

        if not user:
            logger.warning(f"❌ Authentication failed for email: {request.email}")
            log_ecommerce_auth_event("LOGIN_FAILED", {"email": request.email}, "WARNING")
            raise HTTPException(
                status_code=401,
                detail="Email o contraseña incorrectos"
            )

        # Crear token de acceso
        access_token_expires = timedelta(minutes=60 * 24)  # 24 horas
        access_token = create_access_token(
            data={
                "sub": user["email"],
                "type": "ecommerce",
                "user_id": user["id"]
            },
            expires_delta=access_token_expires
        )

        log_ecommerce_auth_event("LOGIN_SUCCESS", {"email": request.email}, "INFO")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login de usuario: {str(e)}")
        log_ecommerce_auth_event("LOGIN_ERROR", {"email": request.email, "error": str(e)}, "ERROR")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/auth/test")
async def test_endpoint(data: dict):
    """
    Endpoint de prueba para verificar que el servidor recibe JSON correctamente
    """
    logger.info(f"📨 Test endpoint received: {data}")
    return {"received": data, "status": "ok"}

@router.get("/auth/verify")
async def verify_token(request: Request):
    """
    Verifica si un token JWT es válido
    """
    try:
        # Obtener token del header Authorization
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Token de autorización faltante o inválido"
            )

        token = authorization.split(" ")[1]

        # Verificar token
        user = await get_current_ecommerce_user(token)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado"
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "user": user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verificando token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/auth/me")
async def get_current_user(request: Request):
    """
    Obtiene información del usuario actual
    """
    try:
        # Obtener token del header Authorization
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Token de autorización faltante o inválido"
            )

        token = authorization.split(" ")[1]

        # Obtener usuario
        user = await get_current_ecommerce_user(token)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado"
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "user": user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_ecommerce_user)):
    """
    Cambia la contraseña del usuario actual
    """
    try:
        # Verificar que la contraseña actual sea correcta
        if not await authenticate_ecommerce_user(current_user["email"], request.current_password):
            raise HTTPException(
                status_code=400,
                detail="La contraseña actual es incorrecta"
            )

        # Cambiar la contraseña
        success = await change_ecommerce_user_password(current_user["id"], request.new_password)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Error al cambiar la contraseña"
            )

        log_ecommerce_auth_event("PASSWORD_CHANGED", {"user_id": current_user["id"]}, "INFO")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Contraseña cambiada exitosamente"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {str(e)}")
        log_ecommerce_auth_event("PASSWORD_CHANGE_ERROR", {"user_id": current_user.get("id"), "error": str(e)}, "ERROR")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )