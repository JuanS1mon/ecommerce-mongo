"""
Módulo de autenticación con Google OAuth2
Maneja el flujo de autenticación OAuth2 con Google para usuarios de ecommerce
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from authlib.integrations.starlette_client import OAuth
except Exception:
    OAuth = None
try:
    from fastapi import HTTPException, status
except Exception:
    # Fallback ligero para pruebas sin FastAPI instalado
    class HTTPException(Exception):
        def __init__(self, status_code=None, detail=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class status:
        HTTP_400_BAD_REQUEST = 400
        HTTP_500_INTERNAL_SERVER_ERROR = 500
        HTTP_409_CONFLICT = 409

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET
)
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from security.ecommerce_auth import hash_password, create_access_token

# Configure logger
logger = logging.getLogger(__name__)

# Configurar OAuth con Authlib
oauth = OAuth() if OAuth else None

# Configurar Google OAuth2
if OAuth and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and oauth:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account',  # Permite al usuario elegir cuenta
        }
    )
    logger.info("✅ Google OAuth2 configurado correctamente")
else:
    logger.warning("Google OAuth2 no configurado - faltan GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET")


def get_oauth_client():
    """Obtiene el cliente OAuth configurado"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth2 no está configurado en el servidor"
        )
    if not oauth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authlib no está instalado en el servidor"
        )
    return oauth.google


def validate_google_user_info(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y extrae información relevante del usuario de Google
    
    Args:
        user_info: Información del usuario devuelta por Google
        
    Returns:
        Dict con información validada del usuario
        
    Raises:
        HTTPException si la información es inválida
    """
    try:
        # Extraer información requerida
        google_id = user_info.get("sub")
        email = user_info.get("email")
        email_verified = user_info.get("email_verified", False)
        
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Información de Google incompleta"
            )
        
        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email de Google no está verificado"
            )
        
        # Extraer información opcional
        nombre = user_info.get("given_name", "")
        apellido = user_info.get("family_name", "")
        profile_picture = user_info.get("picture", "")
        
        return {
            "google_id": google_id,
            "email": email,
            "nombre": nombre,
            "apellido": apellido,
            "profile_picture": profile_picture,
            "email_verified": email_verified
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando información de Google: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error procesando información de Google"
        )


async def find_user_by_google_id(google_id: str) -> Optional[EcomerceUsuarios]:
    """Busca un usuario por su Google ID usando Beanie (async)."""
    try:
        user = await EcomerceUsuarios.find_one(EcomerceUsuarios.google_id == google_id)
        return user
    except Exception as e:
        logger.error(f"Error buscando usuario por Google ID: {str(e)}")
        return None


async def find_user_by_email(email: str) -> Optional[EcomerceUsuarios]:
    """Busca un usuario por su email usando Beanie (async)."""
    try:
        user = await EcomerceUsuarios.find_one(EcomerceUsuarios.email == email)
        return user
    except Exception as e:
        logger.error(f"Error buscando usuario por email: {str(e)}")
        return None


async def create_or_update_google_user(
    google_user_info: Dict[str, Any]
) -> EcomerceUsuarios:
    """
    Crea un nuevo usuario o actualiza uno existente con información de Google
    
    Args:
        db: Sesión de base de datos
        google_user_info: Información del usuario de Google (ya validada)
        
    Returns:
        Usuario creado o actualizado
        
    Raises:
        HTTPException si hay un error
    """
    try:
        google_id = google_user_info["google_id"]
        email = google_user_info["email"]

        # Buscar por Google ID primero
        user = await find_user_by_google_id(google_id)

        if user:
            # Usuario existente con Google - actualizar información
            logger.info(f"Actualizando usuario existente de Google: {email}")
            user.nombre = google_user_info.get("nombre", user.nombre)
            # Guardar nombre completo también en google_name
            user.google_name = google_user_info.get("nombre", user.google_name)
            user.google_picture = google_user_info.get("profile_picture", user.google_picture)
            user.activo = True
            user.email_verified = True
            await user.save()
            return user

        # Buscar por email (usuario local que quiere vincular con Google)
        user = await find_user_by_email(email)

        if user:
            # Usuario local existente - vincular con Google si no estaba vinculado
            if not user.google_id:
                logger.info(f"Vinculando usuario local existente con Google: {email}")
                user.google_id = google_id
                user.google_email = email
                user.google_name = google_user_info.get("nombre", user.google_name)
                user.google_picture = google_user_info.get("profile_picture", user.google_picture)
                user.activo = True
                user.email_verified = True
                await user.save()
                return user
            else:
                # Usuario ya vinculado con otra cuenta Google
                if user.google_id != google_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Este email ya está vinculado con otra cuenta de Google"
                    )
                return user

        # Usuario nuevo - crear con Google
        logger.info(f"Creando nuevo usuario desde Google: {email}")
        new_user = EcomerceUsuarios(
            nombre=google_user_info.get("nombre", ""),
            email=email,
            google_id=google_id,
            google_email=email,
            google_name=google_user_info.get("nombre", ""),
            google_picture=google_user_info.get("profile_picture", ""),
            activo=True,
            email_verified=True,
            contraseña_hash=None
        )

        await new_user.insert()

        logger.info(f"✅ Usuario de Google creado exitosamente: {email}")
        return new_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando/actualizando usuario de Google: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando usuario de Google"
        )


def log_google_auth_event(event_type: str, details: Dict[str, Any], level: str = "INFO"):
    """
    Registra eventos de autenticación con Google en los logs
    
    Args:
        event_type: Tipo de evento (ej: "GOOGLE_LOGIN_SUCCESS")
        details: Detalles del evento
        level: Nivel de log (INFO, WARNING, ERROR)
    """
    log_message = f"Google Auth Event: {event_type} - {details}"
    
    if level == "ERROR":
        logger.error(log_message)
    elif level == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)
