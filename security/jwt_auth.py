"""
Sistema de autenticación JWT puro - Sin cookies
Maneja tokens JWT exclusivamente a través del header Authorization
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from config import SECRET_KEY, ALGORITHM
# Lazy import to avoid circular imports
# from Projects.ecomerce.models.usuarios import EcomerceUsuarios
# TODO: Migrate TokenBlacklist to Beanie
# from db.models.security.token_blacklist import TokenBlacklist
# from db.schemas.config.Usuarios import UserDB, TokenData
# from security.security import verificar_clave

# Local definitions for TokenData
class TokenData:
    def __init__(self, username: str):
        self.username = username

# Lazy import to avoid circular imports
# UserDB = EcomerceUsuarios

# Local password verification function
from passlib.context import CryptContext

def verificar_clave(password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra su hash"""
    if not password or not hashed_password:
        return False
    try:
        return pwd_context.verify(password, hashed_password)
    except Exception:
        return False# Configurar logger
logger = logging.getLogger("jwt_auth")

# Configurar HTTPBearer para extraer token del header Authorization
security = HTTPBearer(auto_error=False)

# Configuración de token
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas para admin

class JWTAuthError(HTTPException):
    """Excepción personalizada para errores de JWT"""
    def __init__(self, detail: str = "No se pudo validar las credenciales"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT de acceso
    
    Args:
        data: Datos a incluir en el token (generalmente {'sub': username})
        expires_delta: Tiempo de expiración personalizado
    
    Returns:
        Token JWT como string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Token JWT creado exitosamente para: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creando token JWT: {str(e)}")
        raise JWTAuthError("Error interno creando token de acceso")

def verify_token(token: str) -> TokenData:
    """
    Verifica y decodifica un token JWT
    
    Args:
        token: Token JWT a verificar
    
    Returns:
        TokenData con información del token
    
    Raises:
        JWTAuthError: Si el token es inválido
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            logger.warning("Token JWT sin 'sub' claim")
            raise JWTAuthError("Token inválido")
        
        logger.debug(f"Token verificado exitosamente para usuario: {username}")
        return TokenData(username=username)
    
    except JWTError as e:
        logger.warning(f"Error decodificando token JWT: {str(e)}")
        raise JWTAuthError("Token inválido o expirado")
    except Exception as e:
        logger.error(f"Error inesperado verificando token: {str(e)}")
        raise JWTAuthError("Error verificando token")

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> Any:
    """
    Obtiene el usuario actual desde el token JWT en el header Authorization
    
    Args:
        credentials: Credenciales del header Authorization
    
    Returns:
        Usuario autenticado
    
    Raises:
        JWTAuthError: Si no hay token o es inválido
    """
    token = None
    # Prefer token from Authorization header
    if credentials and getattr(credentials, 'credentials', None):
        token = credentials.credentials
    else:
        # Fallback: permitir token desde la cookie 'ecommerce_token' (para sesiones web)
        try:
            token = request.cookies.get('ecommerce_token') if request and hasattr(request, 'cookies') else None
            if token:
                logger.debug('Token obtenido desde cookie ecommerce_token')
        except Exception:
            token = None

    if not token:
        logger.warning("No se proporcionó token de autorización ni cookie ecommerce_token")
        raise JWTAuthError("Token de acceso requerido")
    
    # VERIFICAR SI EL TOKEN ESTÁ EN LA LISTA NEGRA
    # Note: TokenBlacklist might need to be migrated to Beanie too, but for now keeping it
    # if TokenBlacklist.is_token_blacklisted(db, token):
    #     logger.warning(f"Token en lista negra intentó ser usado")
    #     raise JWTAuthError("Token inválido - sesión cerrada")
    
    # Verificar token
    token_data = verify_token(token)
    
    # Buscar usuario en base de datos usando Beanie
    from Projects.ecomerce.models.usuarios import EcomerceUsuarios  # Lazy import
    user = await EcomerceUsuarios.find_one(EcomerceUsuarios.email == token_data.username)
    
    if not user:
        logger.warning(f"Usuario no encontrado en BD: {token_data.username}")
        raise JWTAuthError("Usuario no encontrado")
    
    if not user.activo:
        logger.warning(f"Usuario inactivo intentó acceder: {token_data.username}")
        raise JWTAuthError("Usuario inactivo")
    
    # Los roles ya están en el documento del usuario
    user.roles = [user.rol] if user.rol else []
    
    logger.debug(f"Usuario autenticado: {user.email} con roles: {user.roles}")
    return user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> Optional[Any]:
    """
    Obtiene el usuario actual si está autenticado, sino devuelve None
    Útil para rutas que funcionan con o sin autenticación
    """
    try:
        # Pasar request para que get_current_user pueda usar cookie como fallback
        if not credentials and request and request.cookies.get('ecommerce_token'):
            # Llamar a get_current_user con request (sin credenciales de header)
            return await get_current_user(None, request)
        if not credentials:
            return None
        return await get_current_user(credentials, request)
    except Exception:
        return None


async def get_current_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> Any:
    """
    Obtiene el usuario admin actual desde el token JWT
    Busca en la colección admin_usuarios
    
    Args:
        credentials: Credenciales del header Authorization (Bearer token)
        request: Request de FastAPI para obtener cookies
        
    Returns:
        AdminUsuarios: Usuario administrador autenticado
        
    Raises:
        JWTAuthError: Si el token es inválido o el usuario no existe
    """
    # Obtener token desde header o cookie admin_token
    token = None
    if credentials:
        token = credentials.credentials
        logger.debug('Token obtenido desde header Authorization')
    else:
        try:
            if request and request.cookies.get('admin_token'):
                token = request.cookies.get('admin_token')
                logger.debug('Token obtenido desde cookie admin_token')
            elif request and request.cookies.get('ecommerce_token'):
                # Fallback a ecommerce_token para compatibilidad
                token = request.cookies.get('ecommerce_token')
                logger.debug('Token obtenido desde cookie ecommerce_token')
        except Exception:
            token = None

    if not token:
        logger.warning("No se proporcionó token de admin")
        raise JWTAuthError("Token de acceso requerido")
    
    # Verificar token
    token_data = verify_token(token)
    
    # Buscar usuario en colección de admins usando Beanie
    from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios  # Lazy import
    user = await AdminUsuarios.find_one(AdminUsuarios.usuario == token_data.username)
    
    if not user:
        logger.warning(f"Admin no encontrado en BD: {token_data.username}")
        raise JWTAuthError("Usuario administrador no encontrado")
    
    if not user.activo:
        logger.warning(f"Admin inactivo intentó acceder: {token_data.username}")
        raise JWTAuthError("Usuario administrador inactivo")
    
    logger.debug(f"Admin autenticado: {user.usuario}")
    return user


async def get_optional_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> Optional[Any]:
    """
    Obtiene el usuario admin actual si está autenticado, sino devuelve None
    Útil para rutas admin que funcionan con o sin autenticación
    """
    try:
        return await get_current_admin_user(credentials, request)
    except Exception:
        return None

def require_role(required_role: str):
    """
    Decorator/dependency para requerir un rol específico
    
    Args:
        required_role: Nombre del rol requerido (ej: "admin", "user")
    
    Returns:
        Función dependency que verifica el rol
    """
    def check_role(current_user: Any = Depends(get_current_user)) -> Any:
        if not current_user.roles or required_role.lower() not in current_user.roles:
            logger.warning(
                f"Usuario {current_user.email} intentó acceder sin rol {required_role}. "
                f"Roles actuales: {current_user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{required_role}' requerido"
            )
        
        logger.debug(f"Acceso autorizado para {current_user.usuario} con rol {required_role}")
        return current_user
    
    return check_role

def require_admin(current_user: Any = Depends(get_current_user)) -> Any:
    """
    Dependency específico para requerir rol de administrador
    """
    if not current_user.roles or "admin" not in current_user.roles:
        logger.warning(
            f"Usuario {current_user.email} intentó acceder al panel de admin. "
            f"Roles actuales: {current_user.roles}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso de administrador requerido"
        )
    
    logger.debug(f"Acceso de admin autorizado para {current_user.email}")
    return current_user

async def authenticate_user_jwt(username: str, password: str) -> Optional[dict]:
    """
    Autentica un usuario por username y password
    
    Args:
        db: Sesión de base de datos (deprecated, will be removed)
        username: Nombre de usuario (email)
        password: Contraseña en texto plano
    
    Returns:
        Diccionario con información del usuario si es válido, None si no
    """
    try:
        # DEBUG: Log detallado de credenciales recibidas
        logger.debug(f"🔐 AUTHENTICATE_USER_JWT DEBUG:")
        logger.debug(f"  Username recibido: '{username}'")
        logger.debug(f"  Password recibido: {'*' * len(password) if password else 'None'} (longitud: {len(password) if password else 0})")
        logger.debug(f"  Password bytes: {password.encode('utf-8') if password else 'None'}")
        logger.debug(f"  Password repr: {repr(password) if password else 'None'}")
        
        # Buscar usuario usando Beanie
        from Projects.ecomerce.models.usuarios import EcomerceUsuarios  # Lazy import
        user = await EcomerceUsuarios.find_one(EcomerceUsuarios.email == username)
        
        if not user:
            logger.warning(f"❌ Intento de login con usuario inexistente: {username}")
            return None
            
        logger.debug(f"✅ Usuario encontrado en BD: {user.email}")
        logger.debug(f"  Usuario activo: {user.activo}")
        logger.debug(f"  Hash en BD: {user.contraseña_hash[:20]}... (longitud: {len(user.contraseña_hash) if user.contraseña_hash else 0})")

        if not user.activo:
            logger.warning(f"❌ Intento de login con usuario inactivo: {username}")
            return None
        
        # Verificar contraseña
        logger.debug(f"🔑 Verificando contraseña...")
        password_valid = verificar_clave(password, user.contraseña_hash)
        logger.debug(f"🔑 Resultado verificación: {password_valid}")
        
        if not password_valid:
            logger.warning(f"❌ Contraseña incorrecta para usuario: {username}")
            return None
            
        logger.info(f"✅ Autenticación exitosa para usuario: {username}")

        # Los roles ya están en el documento del usuario
        roles = user.roles or []
        
        user_data = {
            "codigo": str(user.id),  # MongoDB ObjectId
            "username": user.email,  # Usar email como username
            "nombre": user.nombre,
            "email": user.email,
            "activo": user.activo,
            "roles": roles
        }
        
        logger.info(f"Autenticación exitosa para usuario: {username}")
        return user_data
    
    except Exception as e:
        logger.error(f"Error en autenticación: {str(e)}")
        return None

# Utilidad para logs de seguridad
def log_auth_event(event_type: str, details: dict, level: str = "INFO"):
    """
    Registra eventos de autenticación y seguridad
    
    Args:
        event_type: Tipo de evento (LOGIN_SUCCESS, LOGIN_FAILED, etc.)
        details: Detalles del evento
        level: Nivel de log (INFO, WARNING, ERROR)
    """
    log_message = f"[{event_type}] {details}"
    
    if level.upper() == "ERROR":
        logger.error(log_message)
    elif level.upper() == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)
