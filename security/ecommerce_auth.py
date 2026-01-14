"""
Sistema de autenticación para usuarios de ecommerce/servicios
Maneja login, registro y verificación de usuarios
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
import re

from config import SECRET_KEY, ALGORITHM
from models.models_beanie import Usuario
from db.database import init_beanie_db

# Configurar logger
logger = logging.getLogger(__name__)

# Configuración de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bandera para controlar inicialización de Beanie
beanie_initialized = False

async def ensure_beanie_initialized():
    """Asegura que Beanie esté inicializado antes de usar los modelos"""
    global beanie_initialized
    if not beanie_initialized:
        try:
            await init_beanie_db()
            beanie_initialized = True
            logger.info("Beanie inicializado en ecommerce_auth")
        except Exception as e:
            logger.error(f"Error inicializando Beanie: {e}")
            raise

# Configuración de tokens
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas para usuarios ecommerce

def hash_password(password: str) -> str:
    """Encripta una contraseña usando bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT de acceso"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_ecommerce_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Autentica un usuario de ecommerce

    Args:
        email: Email del usuario
        password: Contraseña en texto plano

    Returns:
        Diccionario con información del usuario o None si falla la autenticación
    """
    try:
        logger.info(f"🔍 Authenticating user: {email}")
        # Asegurar que Beanie esté inicializado
        await ensure_beanie_initialized()
        
        # Buscar usuario por email usando Beanie
        user = await Usuario.find_one(
            Usuario.email == email,
            Usuario.is_active == True
        )

        if not user:
            logger.warning(f"❌ Usuario no encontrado o inactivo: {email}")
            return None

        logger.info(f"✅ Usuario encontrado: {user.username}, hashed_password exists: {bool(user.hashed_password)}")

        # Verificar contraseña
        try:
            password_valid = verify_password(password, user.hashed_password)
            logger.info(f"🔐 Password verification result: {password_valid}")
        except Exception as pwd_error:
            logger.error(f"❌ Error verificando contraseña para {email}: {str(pwd_error)}")
            return None

        if not password_valid:
            logger.warning(f"❌ Contraseña incorrecta para usuario: {email}")
            return None

        # Retornar información del usuario
        user_data = {
            "id": str(user.id),  # MongoDB ObjectId
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "authenticated": True
        }

        logger.info(f"Usuario autenticado exitosamente: {email}")
        return user_data

    except Exception as e:
        logger.error(f"Error autenticando usuario ecommerce {email}: {str(e)}")
        logger.error(f"Type of error: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def get_current_ecommerce_user(token: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene el usuario ecommerce actual desde un token JWT

    Args:
        token: Token JWT

    Returns:
        Diccionario con información del usuario o None si el token es inválido
    """
    try:
        # Decodificar token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None

        # Verificar que sea un token de ecommerce
        token_type = payload.get("type")
        if token_type != "ecommerce":
            logger.warning(f"Token no es de tipo ecommerce: {token_type}")
            return None

        # Asegurar que Beanie esté inicializado
        await ensure_beanie_initialized()

        # Obtener usuario usando Beanie
        user = await Usuario.find_one(
            Usuario.email == email,
            Usuario.is_active == True
        )

        if not user:
            return None

        return {
            "id": str(user.id),  # MongoDB ObjectId
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "authenticated": True
        }

    except JWTError as e:
        logger.warning(f"Error decodificando token ecommerce: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error obteniendo usuario ecommerce actual: {str(e)}")
        return None

async def register_ecommerce_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Registra un nuevo usuario de ecommerce

    Args:
        user_data: Datos del usuario a registrar

    Returns:
        Diccionario con información del usuario registrado o None si falla
    """
    try:
        # Asegurar que Beanie esté inicializado
        await ensure_beanie_initialized()
        
        # Validar datos requeridos
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                logger.error(f"Campo requerido faltante: {field}")
                return None

        # Validar formato de email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, user_data['email']):
            logger.error(f"Formato de email inválido: {user_data['email']}")
            return None

        # Verificar que el email no esté registrado
        existing_user = await Usuario.find_one(Usuario.email == user_data['email'])
        if existing_user:
            logger.warning(f"Email ya registrado: {user_data['email']}")
            return None

        # Validar longitud de contraseña
        if len(user_data['password']) < 6:
            logger.error("Contraseña demasiado corta (mínimo 6 caracteres)")
            return None

        # Hash de la contraseña
        password_hash = hash_password(user_data['password'])

        # Crear usuario usando Beanie
        new_user = Usuario(
            username=user_data['username'],
            email=user_data['email'],
            hashed_password=password_hash,
            role="user",  # Rol por defecto
            is_active=True
        )

        await new_user.insert()

        user_info = {
            "id": str(new_user.id),  # MongoDB ObjectId
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "is_active": new_user.is_active,
            "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
        }

        logger.info(f"Usuario registrado exitosamente: {user_data['email']}")
        return user_info

    except Exception as e:
        logger.error(f"Error registrando usuario: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def log_ecommerce_auth_event(event_type: str, details: Dict[str, Any], level: str = "INFO"):
    """
    Registra eventos de autenticación de ecommerce

    Args:
        event_type: Tipo de evento (LOGIN_SUCCESS, LOGIN_FAILED, etc.)
        details: Detalles del evento
        level: Nivel de logging
    """
    message = f"ECOMMERCE_AUTH_{event_type}: {details}"

    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)

async def change_ecommerce_user_password(user_id: str, new_password: str) -> bool:
    """
    Cambia la contraseña de un usuario de ecommerce

    Args:
        user_id: ID del usuario
        new_password: Nueva contraseña

    Returns:
        bool: True si se cambió exitosamente, False en caso contrario
    """
    try:
        await ensure_beanie_initialized()

        # Validar la nueva contraseña
        if len(new_password) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")

        # Buscar el usuario
        user = await Usuario.get(user_id)
        if not user:
            logger.error(f"Usuario no encontrado para cambio de contraseña: {user_id}")
            return False

        # Hash de la nueva contraseña
        hashed_password = hash_password(new_password)

        # Actualizar la contraseña
        user.password_hash = hashed_password
        user.updated_at = datetime.utcnow()

        await user.save()

        logger.info(f"Contraseña cambiada exitosamente para usuario: {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error cambiando contraseña para usuario {user_id}: {str(e)}")
        return False
