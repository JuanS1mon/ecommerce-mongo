"""
Router de autenticación para usuarios de ecommerce
Maneja registro, login y verificación de usuarios de EcomerceUsuarios
"""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from security.ecommerce_auth import (
    authenticate_ecommerce_user,
    create_access_token,
    get_current_ecommerce_user,
    register_ecommerce_user,
    log_ecommerce_auth_event,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Configure logger
logger = logging.getLogger(__name__)

# Pydantic models
class EcommerceLoginRequest(BaseModel):
    email: str
    password: str

class EcommerceRegisterRequest(BaseModel):
    nombre: str
    apellido: str
    email: str
    contraseña: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None

class EcommerceUserResponse(BaseModel):
    id: str
    nombre: str
    apellido: Optional[str] = None
    email: str
    telefono: Optional[str]
    direccion: Optional[str]
    ciudad: Optional[str]
    provincia: Optional[str]
    pais: Optional[str]
    activo: bool
    authenticated: bool

def get_client_info(request: Request = None) -> dict:
    """Extrae información del cliente para logging"""
    if not request:
        return {}

    client_ip = "unknown"
    user_agent = "unknown"

    try:
        if hasattr(request, 'client') and request.client:
            client_ip = request.client.host
        elif hasattr(request, 'headers'):
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(",")[0].strip()
            else:
                x_real_ip = request.headers.get("X-Real-IP")
                if x_real_ip:
                    client_ip = x_real_ip

        if hasattr(request, 'headers'):
            user_agent = request.headers.get("User-Agent", "unknown")
    except Exception:
        pass

    return {
        "client_ip": client_ip,
        "user_agent": user_agent
    }

router = APIRouter(
    prefix="/ecomerce/auth",
    tags=["ecommerce-auth"],
)

@router.post("/register")
async def register_ecommerce_user_endpoint(
    user_data: EcommerceRegisterRequest,
    request: Request
):
    """
    Registra un nuevo usuario de ecommerce
    """
    client_info = get_client_info(request)

    try:
        # Registrar usuario
        user_dict = user_data.model_dump()
        registered_user = await register_ecommerce_user(user_dict)

        if not registered_user:
            # Verificar si el email ya existe (usando Beanie)
            from Projects.ecomerce.models.usuarios import EcomerceUsuarios
            existing_user = await EcomerceUsuarios.find_one(EcomerceUsuarios.email == user_data.email)
            if existing_user:
                error_detail = "Ya existe una cuenta registrada con ese email. Por favor, inicia sesión o recupera tu contraseña."
            else:
                error_detail = "Error al registrar usuario. Verifica los datos e intenta nuevamente."
            log_ecommerce_auth_event(
                "REGISTER_FAILED",
                {"email": user_data.email, "reason": error_detail, **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )

        log_ecommerce_auth_event(
            "REGISTER_SUCCESS",
            {"email": user_data.email, "user_id": registered_user["id"], **client_info},
            "INFO"
        )

        return JSONResponse(
            content={
                "message": "Usuario registrado exitosamente",
                "user": registered_user
            },
            status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        raise
    except Exception as e:
        log_ecommerce_auth_event(
            "REGISTER_ERROR",
            {"email": user_data.email, "error": str(e), **client_info},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/login")
async def login_ecommerce_user_endpoint(
    request: Request
):
    """
    Login para usuarios de ecommerce
    """
    # Determinar si se envió JSON o Form data
    user_email = None
    user_password = None

    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        # JSON request
        try:
            json_data = await request.json()
            user_email = json_data.get("email")
            user_password = json_data.get("password")
            logger.error(f"🚨 ECOMMERCE LOGIN ENDPOINT CALLED with email={user_email} (JSON)")
        except:
            raise HTTPException(status_code=400, detail="JSON inválido")
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        # Form data request
        try:
            form_data = await request.form()
            user_email = form_data.get("email")
            user_password = form_data.get("password")
            logger.error(f"ECOMMERCE LOGIN ENDPOINT CALLED with email={user_email} (Form)")
        except:
            raise HTTPException(status_code=400, detail="Datos del formulario inválidos")
    else:
        raise HTTPException(status_code=400, detail="Tipo de contenido no soportado")

    client_info = get_client_info(request)

    try:
        # Detectar si es petición API
        is_api_request = False
        if request:
            accept_header = request.headers.get("Accept", "")
            is_api_request = "application/json" in accept_header

        # Validar entrada
        if not user_email or not user_password:
            log_ecommerce_auth_event(
                "LOGIN_FAILED",
                {"reason": "empty_credentials", **client_info},
                "WARNING"
            )
            if is_api_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email y contraseña son requeridos"
                )
            else:
                return RedirectResponse(
                    url="/ecomerce/login?error=Credenciales requeridas",
                    status_code=status.HTTP_303_SEE_OTHER
                )

        # Autenticar usuario
        user = await authenticate_ecommerce_user(user_email, user_password)

        if not user:
            log_ecommerce_auth_event(
                "LOGIN_FAILED",
                {"email": user_email, "reason": "invalid_credentials", **client_info},
                "WARNING"
            )
            if is_api_request:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            else:
                return RedirectResponse(
                    url="/ecomerce/login?error=Credenciales incorrectas",
                    status_code=status.HTTP_303_SEE_OTHER
                )

        # Crear token JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"], "type": "ecommerce"},
            expires_delta=access_token_expires
        )

        log_ecommerce_auth_event(
            "LOGIN_SUCCESS",
            {"email": user["email"], "user_id": user["id"], **client_info},
            "INFO"
        )

        if is_api_request:
            return JSONResponse(
                content={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "user": user
                },
                status_code=status.HTTP_200_OK
            )
        else:
            # Para web: redirigir a los productos públicos con el token
            response = RedirectResponse(
                url=f"/ecomerce/productos/tienda?token={access_token}",
                status_code=status.HTTP_303_SEE_OTHER
            )
            response.set_cookie(
                key="ecommerce_token",
                value=access_token,
                httponly=False,  # Mantener accesible para compartir entre pestañas
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                secure=False,  # Cambiar a True en producción con HTTPS
                samesite="lax"
            )
            return response

    except HTTPException:
        raise
    except Exception as e:
        log_ecommerce_auth_event(
            "LOGIN_ERROR",
            {"email": user_email, "error": str(e), **client_info},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/logout")
async def logout_ecommerce_user_endpoint(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Logout para usuarios de ecommerce
    """
    client_info = get_client_info(request)

    try:
        # Obtener usuario actual si hay token válido
        user = None
        if credentials and credentials.credentials:
            user = await get_current_ecommerce_user(credentials.credentials)

        if user:
            log_ecommerce_auth_event(
                "LOGOUT_SUCCESS",
                {"email": user["email"], "user_id": user["id"], **client_info},
                "INFO"
            )

        # Detectar tipo de petición
        is_api_request = False
        if request:
            accept_header = request.headers.get("Accept", "")
            is_api_request = "application/json" in accept_header

        if is_api_request:
            return JSONResponse(
                content={
                    "message": "Sesión cerrada exitosamente",
                    "success": True
                },
                status_code=status.HTTP_200_OK
            )
        else:
            response = RedirectResponse(
                url="/ecomerce/productos/tienda",
                status_code=status.HTTP_303_SEE_OTHER
            )
            response.delete_cookie(key="ecommerce_token")
            return response

    except Exception as e:
        logger.error(f"Error en logout ecommerce: {str(e)}")
        response = RedirectResponse(
            url="/ecomerce/productos/tienda",
            status_code=status.HTTP_303_SEE_OTHER
        )
        response.delete_cookie(key="ecommerce_token")
        return response

@router.get("/me")
async def get_current_ecommerce_user_info_endpoint(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Obtiene información del usuario ecommerce autenticado
    """
    try:
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación requerido"
            )

        user = await get_current_ecommerce_user(credentials.credentials)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )

        return EcommerceUserResponse(**user)

    except HTTPException:
        raise
    except BaseException as e:
        logger.error(f"Error obteniendo usuario ecommerce actual: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo información del usuario"
        )

@router.get("/verify")
async def verify_ecommerce_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Verifica si el token de ecommerce es válido
    """
    try:
        if not credentials or not credentials.credentials:
            return {"valid": False, "message": "Token requerido"}

        user = await get_current_ecommerce_user(credentials.credentials)

        if not user:
            return {"valid": False, "message": "Token inválido"}

        return {
            "valid": True,
            "message": "Token válido",
            "user": user
        }

    except Exception as e:
        logger.error(f"Error verificando token ecommerce: {str(e)}")
        return {"valid": False, "message": "Error verificando token"}

@router.get("/status")
async def get_ecommerce_auth_status(
    request: Request
):
    """
    Verifica el estado de autenticación usando la cookie HttpOnly
    """
    try:
        # Obtener token de la cookie HttpOnly
        token = request.cookies.get("ecommerce_token")

        if not token:
            return {"authenticated": False, "message": "No autenticado"}

        # Validar token
        user = await get_current_ecommerce_user(token)

        if not user:
            return {"authenticated": False, "message": "Token inválido"}

        return {
            "authenticated": True,
            "message": "Autenticado",
            "user": user
        }

    except Exception as e:
        logger.error(f"Error verificando estado de autenticación: {str(e)}")
        return {"authenticated": False, "message": "Error verificando autenticación"}
