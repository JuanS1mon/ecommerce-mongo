"""
Sistema de autenticación para usuarios de ecommerce
Maneja login, registro y verificación de usuarios de EcomerceUsuarios
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
import re

from config import SECRET_KEY, ALGORITHM
from Projects.ecomerce.models.usuarios import EcomerceUsuarios

# Configurar logger
logger = logging.getLogger(__name__)

# Configuración de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
        # Buscar usuario por email usando Beanie
        user = await EcomerceUsuarios.find_one(
            EcomerceUsuarios.email == email,
            EcomerceUsuarios.activo == True
        )

        if not user:
            logger.warning(f"Usuario ecommerce no encontrado o inactivo: {email}")
            return None

        # Verificar contraseña
        try:
            password_valid = verify_password(password, user.contraseña_hash)
        except Exception as pwd_error:
            logger.error(f"Error verificando contraseña para {email}: {str(pwd_error)}")
            return None

        if not password_valid:
            logger.warning(f"Contraseña incorrecta para usuario ecommerce: {email}")
            return None

        # Retornar información del usuario
        user_data = {
            "id": str(user.id),  # MongoDB ObjectId
            "nombre": user.nombre,
            "apellido": getattr(user, 'apellido', None),  # Campo opcional
            "email": user.email,
            "telefono": user.telefono,
            "direccion": user.direccion,
            "ciudad": user.ciudad,
            "provincia": getattr(user, 'provincia', None),  # Campo opcional
            "pais": user.pais,
            "activo": user.activo,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "authenticated": True
        }

        logger.info(f"Usuario ecommerce autenticado exitosamente: {email}")
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

        # Obtener usuario usando Beanie
        user = await EcomerceUsuarios.find_one(
            EcomerceUsuarios.email == email,
            EcomerceUsuarios.activo == True
        )

        if not user:
            return None

        return {
            "id": str(user.id),  # MongoDB ObjectId
            "nombre": user.nombre,
            "apellido": getattr(user, 'apellido', None),  # Campo opcional
            "email": user.email,
            "telefono": user.telefono,
            "direccion": user.direccion,
            "ciudad": user.ciudad,
            "provincia": getattr(user, 'provincia', None),  # Campo opcional
            "pais": user.pais,
            "activo": user.activo,
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
        # Validar datos requeridos
        required_fields = ['nombre', 'apellido', 'email', 'contraseña']
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
        existing_user = await EcomerceUsuarios.find_one(EcomerceUsuarios.email == user_data['email'])
        if existing_user:
            logger.warning(f"Email ya registrado: {user_data['email']}")
            return None

        # Validar longitud de contraseña
        if len(user_data['contraseña']) < 6:
            logger.error("Contraseña demasiado corta (mínimo 6 caracteres)")
            return None

        # Hash de la contraseña
        password_hash = hash_password(user_data['contraseña'])

        # Crear usuario usando Beanie
        new_user = EcomerceUsuarios(
            nombre=user_data['nombre'],
            apellido=user_data['apellido'],
            email=user_data['email'],
            contraseña_hash=password_hash,
            telefono=user_data.get('telefono'),
            direccion=user_data.get('direccion'),
            ciudad=user_data.get('ciudad'),
            provincia=user_data.get('provincia'),
            pais=user_data.get('pais'),
            activo=True
        )

        await new_user.insert()

        # TODO: Crear carrito automáticamente para el nuevo usuario
        # This requires migrating the cart model to Beanie first
        # For now, we'll skip cart creation

        user_info = {
            "id": str(new_user.id),  # MongoDB ObjectId
            "nombre": new_user.nombre,
            "apellido": new_user.apellido,
            "email": new_user.email,
            "telefono": new_user.telefono,
            "direccion": new_user.direccion,
            "ciudad": new_user.ciudad,
            "provincia": new_user.provincia,
            "pais": new_user.pais,
            "activo": new_user.activo,
            "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
            "authenticated": False  # Aún no está autenticado
        }

        logger.info(f"Usuario ecommerce registrado exitosamente: {user_data['email']}")
        return user_info

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR EN REGISTRO: {str(e)}")
        print(f"TRACEBACK: {error_details}")
        logger.error(f"Error registrando usuario ecommerce: {str(e)}")
        logger.error(f"Traceback completo: {error_details}")
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
