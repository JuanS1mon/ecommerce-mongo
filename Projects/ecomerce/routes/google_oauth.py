"""
Router de autenticación con Google OAuth2
Maneja las rutas de login con Google y callback
"""
import logging
from typing import Optional
from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.config import Config
from authlib.integrations.starlette_client import OAuthError

from security.google_auth import (
    get_oauth_client,
    validate_google_user_info,
    create_or_update_google_user,
    log_google_auth_event
)
from security.ecommerce_auth import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from config import GOOGLE_CLIENT_ID, FRONTEND_URL, BACKEND_URL

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth/google",
    tags=["google-oauth"],
)


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


@router.get("/login")
async def google_login(request: Request):
    """
    Inicia el flujo de autenticación con Google OAuth2
    Redirige al usuario a la página de login de Google
    """
    try:
        # Verificar configuración
        if not GOOGLE_CLIENT_ID:
            log_google_auth_event(
                "GOOGLE_LOGIN_CONFIG_ERROR",
                {"error": "Google OAuth2 no configurado"},
                "ERROR"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Autenticación con Google no está disponible"
            )

        client_info = get_client_info(request)
        log_google_auth_event(
            "GOOGLE_LOGIN_INITIATED",
            {**client_info},
            "INFO"
        )

        # Obtener cliente OAuth
        google = get_oauth_client()
        
        # Generar URL de autorización de Google
        redirect_uri = request.url_for('google_callback')
        
        logger.info(f"Redirigiendo a Google OAuth con redirect_uri: {redirect_uri}")
        
        return await google.authorize_redirect(request, redirect_uri)

    except HTTPException:
        raise
    except OAuthError as e:
        logger.error(f"Error OAuth iniciando login con Google: {str(e)}")
        log_google_auth_event(
            "GOOGLE_LOGIN_OAUTH_ERROR",
            {"error": str(e)},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error iniciando autenticación con Google"
        )
    except Exception as e:
        logger.error(f"Error inesperado en login con Google: {str(e)}")
        log_google_auth_event(
            "GOOGLE_LOGIN_ERROR",
            {"error": str(e)},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error iniciando login con Google"
        )


@router.get("/callback")
async def google_callback(
    request: Request,
):
    """
    Callback de Google OAuth2
    Google redirige aquí después de que el usuario autoriza la aplicación
    """
    client_info = get_client_info(request)
    
    try:
        # Obtener cliente OAuth
        google = get_oauth_client()
        
        # Obtener token de acceso de Google
        try:
            token = await google.authorize_access_token(request)
        except OAuthError as e:
            logger.error(f"Error OAuth obteniendo token: {str(e)}")
            log_google_auth_event(
                "GOOGLE_CALLBACK_TOKEN_ERROR",
                {"error": str(e), **client_info},
                "ERROR"
            )
            # Redirigir a página de login con error
            return RedirectResponse(
                url=f"/ecomerce/login?error=Error de autenticación con Google",
                status_code=status.HTTP_303_SEE_OTHER
            )
        
        # Obtener información del usuario desde Google
        user_info = token.get('userinfo')
        if not user_info:
            # Si no viene en el token, hacer petición explícita
            user_info = await google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = user_info.json() if hasattr(user_info, 'json') else user_info
        
        logger.info(f"Información recibida de Google: {user_info.get('email', 'no-email')}")
        
        # Validar información del usuario
        validated_user_info = validate_google_user_info(user_info)
        
        log_google_auth_event(
            "GOOGLE_CALLBACK_USER_INFO_RECEIVED",
            {"email": validated_user_info["email"], **client_info},
            "INFO"
        )
        
        # Crear o actualizar usuario en la base de datos (async Beanie)
        user = await create_or_update_google_user(validated_user_info)
        
        # Crear token JWT para la aplicación
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "type": "ecommerce", "provider": "google"},
            expires_delta=access_token_expires
        )
        
        is_new_user = False
        try:
            is_new_user = (datetime.utcnow() - user.created_at).total_seconds() < 60
        except Exception:
            pass

        log_google_auth_event(
            "GOOGLE_LOGIN_SUCCESS",
            {
                "email": user.email,
                "user_id": getattr(user, 'id', None),
                "is_new_user": is_new_user,
                **client_info
            },
            "INFO"
        )
        
        # Redirigir al frontend con el token
        response = RedirectResponse(
            url=f"/ecomerce/productos/tienda?google_login=success",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
        # Establecer cookie con el token
        response.set_cookie(
            key="ecommerce_token",
            value=access_token,
            httponly=False,  # Accesible desde JavaScript para compartir entre pestañas
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=False,  # Cambiar a True en producción con HTTPS
            samesite="lax"
        )
        
        return response

    except HTTPException as e:
        # Redirigir a login con mensaje de error
        return RedirectResponse(
            url=f"/ecomerce/login?error={e.detail}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        logger.error(f"Error inesperado en callback de Google: {str(e)}")
        log_google_auth_event(
            "GOOGLE_CALLBACK_ERROR",
            {"error": str(e), **client_info},
            "ERROR"
        )
        return RedirectResponse(
            url="/ecomerce/login?error=Error procesando autenticación con Google",
            status_code=status.HTTP_303_SEE_OTHER
        )


@router.get("/status")
async def google_auth_status():
    """
    Verifica si Google OAuth2 está configurado y disponible
    """
    is_configured = bool(GOOGLE_CLIENT_ID)
    
    return JSONResponse(
        content={
            "google_oauth_enabled": is_configured,
            "message": "Google OAuth2 configurado" if is_configured else "Google OAuth2 no configurado"
        }
    )
