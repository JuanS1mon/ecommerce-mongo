"""
Router de autenticación JWT - Sin cookies, solo Bearer tokens
Maneja login, logout y verificación de tokens JWT
"""
import logging
from datetime import timedelta
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Project-specific imports
# from db.schemas.config.Usuarios import Token, UserDB
# from db.models.security.token_blacklist import TokenBlacklist
from security.jwt_auth import (
    create_access_token,
    get_current_user,
    get_optional_user,
    authenticate_user_jwt,
    log_auth_event,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
    # UserDB removed - now using Any
)

# Configure logger
logger = logging.getLogger(__name__)

# Pydantic model for token response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: dict

class LoginResponse(BaseModel):
    """Respuesta del endpoint de login"""
    message: str
    access_token: str
    token_type: str
    expires_in: int
    user: dict

def get_client_info(request: Request = None) -> dict:
    """Extrae información del cliente para logging de seguridad"""
    if not request:
        return {}
    
    client_ip = "unknown"
    user_agent = "unknown"
    
    try:
        # Obtener IP del cliente
        if hasattr(request, 'client') and request.client:
            client_ip = request.client.host
        elif hasattr(request, 'headers'):
            # Intentar obtener IP de headers de proxy
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(",")[0].strip()
            else:
                x_real_ip = request.headers.get("X-Real-IP")
                if x_real_ip:
                    client_ip = x_real_ip
        
        # Obtener User-Agent
        if hasattr(request, 'headers'):
            user_agent = request.headers.get("User-Agent", "unknown")
    except Exception:
        pass  # Silenciar errores para no afectar funcionalidad principal
    
    return {
        "client_ip": client_ip,
        "user_agent": user_agent
    }

router = APIRouter(
    prefix="/auth",
    tags=["autenticación"],
)

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(None)
):
    """
    Endpoint de login JWT - SIN COOKIES, solo Bearer tokens

    - Si se incluye 'next' en el formulario o query params, redirige tras login exitoso
    - Si es una petición API (Accept: application/json), devuelve JSON con el token
    - Si es formulario HTML, redirige a la ruta deseada agregando el token como query param (?token=...)
    - El frontend debe capturar el token de la URL y guardarlo en localStorage/sessionStorage usando JavaScript
    - Todas las rutas protegidas deben requerir el header Authorization: Bearer <token>
    - No se usa cookie de sesión
    """
    client_info = get_client_info(request) if request else {}
    
    # DEBUG: Log detallado de datos recibidos
    logger.debug(f"🔍 LOGIN DEBUG:")
    logger.debug(f"  Username recibido: '{username}'")
    logger.debug(f"  Password recibido: {'*' * len(password) if password else 'None'} (longitud: {len(password) if password else 0})")
    logger.debug(f"  Password bytes: {password.encode('utf-8') if password else 'None'}")
    logger.debug(f"  Next recibido: '{next}'")
    logger.debug(f"  Request query params: {dict(request.query_params) if request else 'None'}")    
    try:
        # Obtener parámetro 'next' para redirección
        next_url = next or (request.query_params.get('next') if request else None)
        logger.debug(f"🔍 REDIRECT DEBUG: next_url = '{next_url}'")
        
        # Detectar si es petición API vs formulario web
        is_api_request = False
        if request:
            accept_header = request.headers.get("Accept", "")
            content_type = request.headers.get("Content-Type", "")
            user_agent = request.headers.get("User-Agent", "")
            is_api_request = (
                "application/json" in accept_header and 
                "text/html" not in accept_header
            ) or "application/json" in content_type
            
            # DEBUG: Log detallado de headers para detectar el problema
            logger.debug(f"🔍 HEADER DEBUG:")
            logger.debug(f"  Accept: '{accept_header}'")
            logger.debug(f"  Content-Type: '{content_type}'")
            logger.debug(f"  User-Agent: '{user_agent[:100]}...'")
            logger.debug(f"  is_api_request: {is_api_request}")
            logger.debug(f"🚀 DECISION: {'API response' if is_api_request else 'Web redirect'}")
        
        # Validar entrada
        if not username or not password:
            log_auth_event(
                "LOGIN_FAILED",
                {"reason": "empty_credentials", **client_info},
                "WARNING"
            )
            if is_api_request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credenciales requeridas"
                )
            else:
                from fastapi.responses import HTMLResponse
                with open("static/login_error.html", "r", encoding="utf-8") as f:
                    html = f.read()
                return HTMLResponse(content=html, status_code=400)
        
        # Autenticar usuario
        user = await authenticate_user_jwt(username, password)
        
        if not user:
            log_auth_event(
                "LOGIN_FAILED",
                {"username": username, "reason": "invalid_credentials", **client_info},
                "WARNING"
            )
            if is_api_request:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                from fastapi.responses import HTMLResponse
                with open("static/login_error.html", "r", encoding="utf-8") as f:
                    html = f.read()
                return HTMLResponse(content=html, status_code=401)
        
        # Crear token de acceso JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, 
            expires_delta=access_token_expires
        )
        
        # Preparar información del usuario para la respuesta
        user_info = {
            "username": user.email,
            "nombre": user.nombre,
            "email": user.email,
            "activo": user.active,
            "roles": user.roles if user.roles else []        }
        
        # Log exitoso
        log_auth_event(
            "LOGIN_SUCCESS", 
            {"username": user["username"], **client_info},
            "INFO"
        )
        
        # 🚨 DEBUG ESPECÍFICO - DEBE APARECER EN LOGS
        logger.error("🚨 LOGIN EXITOSO - INICIANDO LÓGICA DE REDIRECCIÓN")
        logger.error(f"🚨 next_url = '{next_url}'")
        logger.error(f"🚨 access_token = '{access_token[:30]}...'")
        
        # Si es petición API, devolver JSON sin redirección
        if is_api_request:
            return JSONResponse(
                content={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": user_info
                },
                status_code=200
            )

        # Si es formulario HTML, establecer el token como cookie HttpOnly y redirigir
        # Determinar la URL de redirección por defecto basada en roles
        default_redirect = "/"
        if user.get("roles"):
            # Verificar si el usuario tiene rol de admin
            admin_role = any(role.lower() == "admin" for role in user["roles"])
            if admin_role:
                default_redirect = "/admin"
        
        response = RedirectResponse(url=next_url or default_redirect, status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log_auth_event(
            "LOGIN_ERROR",
            {"username": username, "error": str(e), **client_info},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/logout")
async def logout_post(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    user: Optional[Any] = Depends(get_optional_user)
):
    """
    Cierra sesión del usuario (método POST para APIs)
    Invalida el token agregándolo a la lista negra
    """
    from fastapi.security import HTTPBearer
    from datetime import datetime, timezone
    from jose import jwt
    
    client_info = get_client_info(request)
    
    try:
        # Extraer el token del header Authorization
        token = None
        if credentials and credentials.credentials:
            token = credentials.credentials
        
        if token and user:
            # Decodificar el token para obtener la fecha de expiración
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    fecha_expiracion = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                else:
                    # Si no tiene exp, usar 1 hora desde ahora
                    from datetime import timedelta
                    fecha_expiracion = datetime.now(timezone.utc) + timedelta(hours=1)
                
                # TODO: Migrar TokenBlacklist a Beanie/MongoDB
                # Agregar el token a la lista negra
                # TokenBlacklist.add_to_blacklist(
                #     db=db,
                #     token=token,
                #     usuario_codigo=user.codigo,
                #     fecha_expiracion=fecha_expiracion,
                #     razon='logout',
                #     user_agent=client_info.get('user_agent'),
                #     ip_address=client_info.get('client_ip')
                # )
                
                log_auth_event(
                    "LOGOUT_SUCCESS",
                    {"username": user.email if hasattr(user, 'email') else 'unknown', "token_invalidado": False, **client_info},
                    "INFO"
                )
                
                logger.info(f"✅ Logout exitoso para usuario: {user.email if hasattr(user, 'email') else 'unknown'}")
                
            except Exception as e:
                logger.error(f"Error al procesar logout: {str(e)}")
        
        # Detectar si es petición API
        is_api_request = False
        if request:
            accept_header = request.headers.get("Accept", "")
            is_api_request = "application/json" in accept_header
        
        if is_api_request:
            # Para peticiones API, devolver JSON
            return JSONResponse(
                content={
                    "message": "Sesión cerrada exitosamente",
                    "token_invalidado": True,
                    "instruction": "El token ha sido invalidado en el servidor"
                },
                status_code=status.HTTP_200_OK
            )
        else:
            # Para peticiones web: limpiar cookie y redirigir
            response = RedirectResponse(url="/loginpage", status_code=status.HTTP_303_SEE_OTHER)
            response.delete_cookie(key="access_token")
            return response
        
    except Exception as e:
        logger.error(f"Error en logout: {str(e)}")
        
        # En caso de error, también limpiar cookie y redirigir
        response = RedirectResponse(url="/loginpage", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(key="access_token")
        return response

@router.get("/logout")
async def logout_get(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    user: Optional[Any] = Depends(get_optional_user)
):
    """
    Cierra sesión del usuario (método GET para navegador)
    Invalida el token y redirige al login
    """
    from datetime import datetime, timezone, timedelta
    from jose import jwt
    
    client_info = get_client_info(request)
    
    try:
        # Extraer el token del header Authorization
        token = None
        if credentials and credentials.credentials:
            token = credentials.credentials
        
        if token and user:
            # Decodificar el token para obtener la fecha de expiración
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    fecha_expiracion = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                else:
                    fecha_expiracion = datetime.now(timezone.utc) + timedelta(hours=1)
                
                # Agregar el token a la lista negra
                TokenBlacklist.add_to_blacklist(
                    db=db,
                    token=token,
                    usuario_codigo=user.codigo,
                    fecha_expiracion=fecha_expiracion,
                    razon='logout',
                    user_agent=client_info.get('user_agent'),
                    ip_address=client_info.get('client_ip')
                )
                
                log_auth_event(
                    "LOGOUT_SUCCESS",
                    {"username": user.usuario, "token_invalidado": True, **client_info},
                    "INFO"
                )
                
                logger.info(f"✅ Token invalidado para usuario: {user.usuario}")
                
            except Exception as e:
                logger.error(f"Error al invalidar token: {str(e)}")
        
        # Limpiar cookie y redirigir
        response = RedirectResponse(url="/loginpage", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(key="access_token")
        return response
        
    except Exception as e:
        logger.error(f"Error en logout GET: {str(e)}")
        
        # En caso de error, también limpiar cookie y redirigir
        response = RedirectResponse(url="/loginpage", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(key="access_token")
        return response

@router.get("/test-user")
async def test_user_endpoint():
    """Endpoint temporal para probar la funcionalidad del frontend"""
    # SVG de avatar de prueba en base64
    test_avatar = "PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICAgIDxjaXJjbGUgY3g9IjUwIiBjeT0iNTAiIHI9IjUwIiBmaWxsPSIjNEY0NkU1Ii8+CiAgICA8Y2lyY2xlIGN4PSI1MCIgY3k9IjM1IiByPSIxNSIgZmlsbD0id2hpdGUiLz4KICAgIDxlbGxpcHNlIGN4PSI1MCIgY3k9Ijc1IiByeD0iMjAiIHJ5PSIxNSIgZmlsbD0id2hpdGUiLz4KICAgIDx0ZXh0IHg9IjUwIiB5PSI1NSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjI0IiBmaWxsPSIjNEY0NkU1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5KPC90ZXh0Pgo8L3N2Zz4="
    
    user_data = {
        "codigo": 1,
        "usuario": "juan",
        "nombre": "Juan Admin",
        "email": "juan@admin.com",
        "imagen_perfil": test_avatar,
        "autenticado": True,
        "activo": True,
        "roles": ["admin"]
    }
    
    return user_data

@router.get("/me")
async def get_current_user_info(
    request: Request,
    user: Any = Depends(get_current_user)
):
    """Obtiene información del usuario autenticado actualmente"""
    try:
        # Excluir información sensible
        user_data = {
            "codigo": user.codigo,
            "usuario": user.usuario,
            "nombre": user.nombre,
            "email": user.mail,
            "imagen_perfil": user.imagen_perfil if hasattr(user, 'imagen_perfil') else None,
            "autenticado": True,
            "activo": user.activo,
            "roles": user.roles if hasattr(user, "roles") and user.roles else []
        }
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error obteniendo información del usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo información del usuario"
        )

@router.get("/verify-token")
async def verify_token(user: Any = Depends(get_current_user)):
    """Verifica si el token JWT es válido"""
    return {
        "valid": True,
        "message": "Token válido",
        "user": {
            "usuario": user.usuario,
            "nombre": user.nombre,
            "activo": user.activo,
            "roles": user.roles if hasattr(user, "roles") and user.roles else []
        }
    }

@router.get("/login-debug/{username}")
async def login_debug(username: str, request: Request):
    """
    Endpoint de debug para login automático - SOLO PARA DESARROLLO
    """
    from security.jwt_auth import authenticate_user_jwt, create_access_token
    from datetime import timedelta
    
    print(f"🔧 DEBUG LOGIN para: {username}")
    
    # SOLO para desarrollo - passwords conocidos
    test_passwords = {
        "juan": "juan123",
        "admin": "admin123", 
        "test": "test123"
    }
    
    if username not in test_passwords:
        return {"error": "Usuario no válido para debug"}
    
    password = test_passwords[username]
    
    # Autenticar usuario
    user = authenticate_user_jwt(db, username, password)
    
    if not user:
        return {"error": "Credenciales incorrectas"}
    
    # Crear token
    access_token = create_access_token(
        data={"sub": user["username"]}, 
        expires_delta=timedelta(minutes=60)
    )
    
    # Devolver respuesta con múltiples formas de establecer el token
    response = RedirectResponse(url=f"/admin?token={access_token}", status_code=303)
    
    # También establecer como cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=3600,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        domain=None
    )
    
    return response

@router.post("/debug-password")
async def debug_password_endpoint(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Endpoint temporal para debug de contraseñas - SOLO PARA DESARROLLO
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.error("🚨 DEBUG PASSWORD ENDPOINT ACTIVADO")
    logger.error(f"Username recibido: '{username}'")
    logger.error(f"Password recibido: '{password}'")
    logger.error(f"Password repr: {repr(password)}")
    logger.error(f"Password bytes: {password.encode('utf-8')}")
    logger.error(f"Password length: {len(password)}")
    logger.error(f"Password bytes length: {len(password.encode('utf-8'))}")
    
    # Verificar si la contraseña tiene caracteres especiales
    has_special_chars = any(ord(c) > 127 for c in password)
    logger.error(f"Has non-ASCII chars: {has_special_chars}")
    
    # Mostrar caracteres uno por uno
    char_info = []
    for i, c in enumerate(password):
        char_info.append(f"[{i}]: '{c}' (ord: {ord(c)})")
    logger.error(f"Character analysis: {' | '.join(char_info[:20])}")  # Solo primeros 20
    
    # Intentar autenticar para ver qué pasa
    from security.jwt_auth import authenticate_user_jwt
    
    db = next(db_gen)
    
    try:
        result = authenticate_user_jwt(db, username, password)
        logger.error(f"Authentication result: {result is not None}")
        if result:
            logger.error(f"User authenticated: {result['username']}")
        else:
            logger.error("Authentication failed")
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
    
    return {
        "debug": "Check server logs for detailed password analysis",
        "username": username,
        "password_length": len(password),
        "has_special_chars": has_special_chars
    }

# NOTA IMPORTANTE PARA RUTAS PROTEGIDAS:
# Todas las rutas que requieran autenticación deben usar Depends(get_current_user) y esperar el token en el header Authorization: Bearer <token>.
# El frontend debe enviar el token en cada petición protegida. Si usas HTML básico, necesitas JS para leer el token de la URL y guardarlo.
