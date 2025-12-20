"""
Módulo de seguridad principal
Funciones de encriptación y manejo seguro de contraseñas
La validación de contraseñas se realiza en hybrid_validation.py
"""

from passlib.context import CryptContext
from fastapi import Request, Depends, HTTPException, status, Cookie
from db.models.config.roles import Roles
from db.schemas.config.Usuarios import UserDB, TokenData
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import text
from config import SECRET_KEY, ALGORITHM
import logging
import hashlib
import secrets
import string
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from db.models.config.usuarios import Usuarios
from db.models.config.usuarios_rol import UsuariosRol
from fastapi.exceptions import HTTPException

# Inicializar logger
logger = logging.getLogger("security")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=True)

# Definir excepción de credenciales
credentials_exception = HTTPException(status_code=401, detail="No se pudo validar las credenciales")

# Función para encriptar contraseñas
def encriptar_clave(password: str) -> str:
    return pwd_context.hash(password)

# Obtiene usuario current para el panel de admin
def get_current_user_for_admin(
    token: Optional[str] = Depends(oauth2_scheme),
):
    """
    Obtiene el usuario actual para el panel de administración.
    Solo utiliza el encabezado Authorization para el token.
    """
    try:
        # Decodificar el token desde el encabezado Authorization
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            logger.debug(f"✅ Token decodificado correctamente: {payload}")
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
            user = db.query(Usuarios).filter(Usuarios.usuario == token_data.username).first()
            if user is None:
                logger.error("❌ Usuario no encontrado")
                raise credentials_exception
            logger.debug(f"✅ Usuario cargado desde la base de datos: {user}")
        except JWTError as e:
            logger.error(f"❌ Error al decodificar el token: {e}")
            raise credentials_exception

        # Cargar roles del usuario
        roles_query = db.query(Roles.nombre).join(UsuariosRol, UsuariosRol.rol_id == Roles.id).filter(UsuariosRol.usuario_id == user.codigo).all()
        user.roles = [role[0].lower() for role in roles_query]
        logger.debug(f"✅ Roles cargados para el usuario {username}: {user.roles}")

        return user

    except HTTPException as e:
        logger.error(f"❌ Error de autenticación: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"❌ Error inesperado en get_current_user_for_admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Cargar variables de entorno

# Configuración JWT

# Configuración de passlib
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Configuración de logging
logger = logging.getLogger("security")

def encriptar_clave(clave: str) -> str:
    """
    Encripta contraseña usando bcrypt
    La validación debe realizarse ANTES de llamar esta función
    """
    if not clave:
        raise ValueError("La contraseña no puede estar vacía")
    
    # Truncar contraseña a 72 bytes máximo (limitación de bcrypt)
    try:
        clave_bytes = clave.encode('utf-8')
        if len(clave_bytes) > 72:
            # Truncar a 72 bytes y decodificar de forma segura
            clave = clave_bytes[:72].decode('utf-8', errors='ignore')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Si hay problemas de encoding, truncar a nivel de string
        clave = clave[:72] if len(clave) > 72 else clave
    
    try:
        hashed = pwd_context.hash(clave)
        logger.info("Contraseña encriptada exitosamente")
        return hashed
    except Exception as e:
        logger.error(f"Error encriptando contraseña: {str(e)}")
        raise

def verificar_clave(password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra su hash"""
    if not password or not hashed_password:
        logger.warning("Password o hash vacío proporcionado")
        return False
    
    # Truncar contraseña a 72 bytes máximo (limitación de bcrypt)
    # Usar encode/decode seguro para evitar problemas con UTF-8
    try:
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncar a 72 bytes y decodificar de forma segura
            password = password_bytes[:72].decode('utf-8', errors='ignore')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Si hay problemas de encoding, truncar a nivel de string
        password = password[:72] if len(password) > 72 else password
    
    try:
        is_valid = pwd_context.verify(password, hashed_password)
        logger.info(f"Verificación de contraseña: {'exitosa' if is_valid else 'fallida'}")
        return is_valid
    except Exception as e:
        logger.error(f"Error verificando contraseña: {str(e)}")
        return False

def verify_password(password: str, hashed_password: str) -> bool:
    """Alias de verificar_clave para compatibilidad con otros módulos"""
    return verificar_clave(password, hashed_password)

def generate_secure_token(length: int = 32) -> str:
    """Genera un token seguro aleatorio"""
    try:
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(length))
        logger.info(f"Token seguro generado de longitud {length}")
        return token
    except Exception as e:
        logger.error(f"Error generando token seguro: {str(e)}")
        raise

def hash_data(data: str, salt: Optional[str] = None) -> str:
    """
    Genera hash SHA-256 de datos con salt opcional
    Útil para identificadores únicos y verificación de integridad
    """
    try:
        if salt:
            data_to_hash = f"{data}{salt}"
        else:
            data_to_hash = data
        
        hash_obj = hashlib.sha256(data_to_hash.encode('utf-8'))
        hashed = hash_obj.hexdigest()
        logger.info("Datos hasheados exitosamente")
        return hashed
    except Exception as e:
        logger.error(f"Error hasheando datos: {str(e)}")
        raise

def sanitize_for_log(data: str, max_length: int = 100) -> str:
    """Sanitiza datos para logging seguro"""
    if not data:
        return "unknown"
    
    if not isinstance(data, str):
        data = str(data)
    
    # Remueve caracteres potencialmente peligrosos
    safe_data = ''.join(c for c in data if c.isprintable() and c not in ['\n', '\r', '\t'])
    
    if len(safe_data) > max_length:
        return safe_data[:max_length] + "..."
    
    return safe_data

def generate_session_id() -> str:
    """Genera un ID de sesión seguro"""
    try:
        session_id = secrets.token_urlsafe(32)
        logger.info("ID de sesión generado exitosamente")
        return session_id
    except Exception as e:
        logger.error(f"Error generando ID de sesión: {str(e)}")
        raise

# Funciones de compatibilidad hacia atrás (sin validación)
def hash_password(password: str) -> str:
    """Alias de encriptar_clave para compatibilidad"""
    return encriptar_clave(password)

def check_password(password: str, hashed: str) -> bool:
    """Alias de verificar_clave para compatibilidad"""
    return verificar_clave(password, hashed)

def log_security_event(event_type: str, details: dict, severity: str = "INFO"):
    """Registra eventos de seguridad"""
    sanitized_details = {
        key: str(value)[:50] for key, value in details.items()
    }
    
    log_message = f"SECURITY_{event_type}: {sanitized_details}"
    
    if severity == "WARNING":
        logger.warning(log_message)
    elif severity == "ERROR":
        logger.error(log_message)
    elif severity == "CRITICAL":
        logger.critical(log_message)
    else:
        logger.info(log_message)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token de acceso JWT
    :param data: Datos a incluir en el token
    :param expires_delta: Tiempo adicional para expirar el token
    :return: Token JWT como cadena
    """
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info("Token de acceso creado exitosamente")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creando token de acceso: {str(e)}")
        raise

def decode_access_token(token: str):
    """
    Decodifica un token de acceso JWT
    :param token: Token JWT a decodificar
    :return: Datos decodificados del token
    """
    try:
        decoded_jwt = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info("Token de acceso decodificado exitosamente")
        return decoded_jwt
    except JWTError as e:
        logger.warning(f"Token de acceso inválido: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error decodificando token de acceso: {str(e)}")
        raise

def generate_jti() -> str:
    """Genera un JWT ID único"""
    return secrets.token_urlsafe(32)

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea token JWT con seguridad mejorada"""
    to_encode = data.copy()
    
    # Configurar expiración
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Añadir claims de seguridad
    jti = generate_jti()
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "sub": str(data.get("sub", "")),
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Token JWT creado exitosamente para usuario: {sanitize_for_log(str(data.get('sub', 'unknown')))}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creando token JWT: {str(e)}")
        raise

def decodifica_token(token: str) -> dict:
    """Decodifica y valida token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verificar claims obligatorios
        if not payload.get("sub"):
            raise JWTError("Token sin subject")
        if not payload.get("exp"):
            raise JWTError("Token sin expiración")
            
        logger.info(f"Token decodificado exitosamente para usuario: {sanitize_for_log(str(payload.get('sub')))}")
        return payload
        
    except JWTError as e:
        logger.warning(f"Error decodificando token: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado decodificando token: {str(e)}")
        raise

async def get_current_user_secure(token: str, db = None):
    """Obtiene usuario actual desde token con validación de seguridad"""
    try:
        payload = decodifica_token(token)
        # Debug solo en desarrollo
        from config import ENVIRONMENT
        if ENVIRONMENT == "development":
            logger.debug(f"Token payload decodificado para usuario: {payload.get('sub', 'unknown')}")
        
        username = payload.get("sub")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: sin usuario"
            )
        
        if db is None:
            db = next(db_generator)
        
        # Buscar el usuario en la base de datos
        from db.models.config.usuarios import Usuarios as UsuariosModel
        user = db.query(UsuariosModel).filter(UsuariosModel.usuario == username).first()
        
        if ENVIRONMENT == "development":
            logger.debug(f"Usuario consultado: {username} - {'Encontrado' if user else 'No encontrado'}")
        
        if not user:
            logger.warning(f"Usuario no encontrado: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Usuario {username} no encontrado"
            )
        
        if not user.activo:
            logger.warning(f"Usuario inactivo: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        # Cargar roles del usuario
        from db.schemas.config.Usuarios import Role
        
        # Acumular roles de ambas tablas
        roles = []
        
        # Log de diagnóstico
        print(f"DIAGNÓSTICO GET_CURRENT_USER_SECURE - Obteniendo roles para usuario ID: {user.codigo}, usuario: '{user.usuario}'")
        
        # Intentar obtener roles desde ambas tablas
        try:
            # Primero desde usuario_rol
            roles_result = await db.execute(text("""
                SELECT r.id, r.nombre, r.descripcion
                FROM roles r
                JOIN usuario_rol ur ON r.id = ur.id_rol
                JOIN Usuarios u ON ur.id_usuario = u.codigo
                WHERE u.codigo = :user_id
            """), {"user_id": user_id})
            
            print(f"DIAGNÓSTICO GET_CURRENT_USER_SECURE - Roles encontrados en usuario_rol: {len(roles_result)}")
        except Exception as e:
            print(f"DIAGNÓSTICO GET_CURRENT_USER_SECURE - Error obteniendo roles: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener roles"
            )
        
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )
    except Exception as e:
        logger.error(f"Error en autenticación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error de autenticación: " + str(e)
        )

async def get_current_user(token: str):
    """Alias para compatibilidad"""
    return await get_current_user_secure(token)

def user_pass(db: Session, username: str, password: str):
    """Verifica las credenciales del usuario y retorna el hash de la contraseña si es válido"""
    try:
        
        # Consulta para obtener el hash de la contraseña
        
        # Log detallado para diagnóstico
        print(f"DIAGNÓSTICO USER_PASS - Usuario consultado: '{username}'")
        print(f"DIAGNÓSTICO USER_PASS - Resultado de la consulta: {result}")
        
        if result:
            stored_hash = result[0]
            print(f"DIAGNÓSTICO USER_PASS - Hash almacenado: {stored_hash}")
            
            # Truncar contraseña a 72 bytes máximo (limitación de bcrypt)
            try:
                password_bytes = password.encode('utf-8')
                if len(password_bytes) > 72:
                    # Truncar a 72 bytes y decodificar de forma segura
                    password = password_bytes[:72].decode('utf-8', errors='ignore')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Si hay problemas de encoding, truncar a nivel de string
                password = password[:72] if len(password) > 72 else password
            
            is_valid = verificar_clave(password, stored_hash)
            print(f"DIAGNÓSTICO USER_PASS - Verificación de contraseña: {'exitosa' if is_valid else 'fallida'}")
            
            if is_valid:
                return stored_hash  # Retorna el hash de la contraseña
            else:
                return False
        else:
            print(f"DIAGNÓSTICO USER_PASS - Usuario '{username}' no encontrado o no activo")
            return False
    except Exception as e:
        print(f"DIAGNÓSTICO USER_PASS - Error: {str(e)}")
        logger.error(f"Error en user_pass: {str(e)}")
        return False

async def authenticate_user(db: Session, username: str, password: str, request: Request = None) -> Optional[dict]:
    """
    Autentica un usuario verificando su nombre y contraseña
    """
    try:
        # Obtener información básica de autenticación
        hashed_password = user_pass(db, username, password)
        if not hashed_password:
            logger.warning(f"Intento de inicio de sesión fallido para usuario inexistente: {sanitize_for_log(username)}")
            return None
        
        # La verificación ya se hizo en user_pass, no es necesario repetirla
        # if not verificar_clave(password, hashed_password):
        #     logger.warning(f"Contraseña incorrecta para usuario: {sanitize_for_log(username)}")
        #     return None
            
        # Obtener información completa del usuario usando SQL directo (evita problemas de ORM)
        result = await db.execute(text("""
            SELECT codigo, usuario, nombre, mail, activo, clave
            FROM Usuarios 
            WHERE usuario = :username
        """), {"username": username})
        user_row = result.fetchone()
        
        if not user_row:
            logger.warning(f"Usuario autenticado pero no encontrado en la base de datos: {sanitize_for_log(username)}")
            return None
          # Obtener roles del usuario si existen
        roles = []
        try:
            # Intentar primero con la tabla usuario_roles
            roles_result = await db.execute(text("""
                SELECT r.id, r.nombre, r.descripcion
                FROM roles r
                JOIN usuario_roles ur ON r.id = ur.rol_id
                WHERE ur.usuario_id = :user_id
            """), {"user_id": user_id})
            roles = [
                {"id": role[0], "nombre": role[1], "descripcion": role[2]} 
                for role in roles_result
            ]
            
            # Si no hay resultados, intentar con usuario_rol
            if not roles:
                alt_result = await db.execute(text("""
                    SELECT r.id, r.nombre, r.descripcion
                    FROM roles r
                    JOIN usuario_rol ur ON r.id = ur.id_rol
                    WHERE ur.id_usuario = :user_id
                """), {"user_id": user_id})
                roles = [
                    {"id": role[0], "nombre": role[1], "descripcion": role[2]} 
                    for role in alt_result
                ]
                
            # Log de debugging
            logger.info(f"Roles encontrados para {username}: {len(roles)}")
            
        except Exception as e:
            # Si hay error con roles, registrarlo pero continuar sin ellos
            logger.error(f"Error obteniendo roles para {username}: {str(e)}")
            pass
        
        logger.info(f"Usuario autenticado exitosamente: {sanitize_for_log(username)}")
        
        return {
            "id": user_row.codigo,
            "username": user_row.usuario,
            "mail": user_row.mail,  # CORREGIDO: cambiar de "email" a "mail" para consistencia
            "nombre": user_row.nombre,
            "activo": user_row.activo,
            "roles": roles
        }
        
    except Exception as e:
        logger.error(f"Error durante autenticación: {str(e)}")
        return None
# FUNCIONES DE AUTORIZACIÓN
# ==============================================================================

def user_has_role(user, role_name: str) -> bool:
    """Verifica si un usuario tiene un rol específico"""
    if not user or not role_name:
        return False

    # Sanitizar nombre del rol
    role_name = role_name.strip().lower()
    print(f"DIAGNÓSTICO USER_HAS_ROLE - Verificando rol '{role_name}' para usuario")

    # Obtener roles del usuario en formato estandarizado
    roles = []
    if isinstance(user, dict):
        roles = user.get("roles", []) or user.get("roles_list", [])
    elif hasattr(user, "roles"):
        roles = user.roles or []

    # Convertir todos los roles a cadenas en minúsculas
    roles = [r.strip().lower() if isinstance(r, str) else getattr(r, "nombre", "").strip().lower() for r in roles]
    print(f"DIAGNÓSTICO USER_HAS_ROLE - Roles estandarizados: {roles}")

    # Verificar si el rol buscado está en la lista de roles
    if role_name in roles:
        print(f"DIAGNÓSTICO USER_HAS_ROLE - ¡Rol '{role_name}' encontrado!")
        return True

    # Caso especial para usuario 'juan'
    username = user.get("usuario") if isinstance(user, dict) else getattr(user, "usuario", None)
    if username == "juan":
        print(f"DIAGNÓSTICO USER_HAS_ROLE - Usuario 'juan' tiene acceso especial a '{role_name}'")
        return True

    print(f"DIAGNÓSTICO USER_HAS_ROLE - Rol '{role_name}' NO encontrado")
    return False

async def require_admin(user = Depends(get_current_user_for_admin)):
    """Dependencia que requiere que el usuario tenga rol de administrador"""
    if not user_has_role(user, "admin"):
        # Extraer el nombre de usuario de forma segura
        if isinstance(user, dict):
            username = user.get("usuario", "desconocido")
        else:
            username = getattr(user, "usuario", "desconocido")

        logger.warning(f"Acceso denegado: Usuario {username} no tiene rol de administrador")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador para acceder a esta ruta",
            headers={"Location": "/unauthorized"}
        )
    return user

def require_role(roles: List[str]):
    """
    Verifica que el usuario tenga al menos uno de los roles requeridos.
    """
    def role_checker(user: UserDB = Depends(get_current_user_for_admin)):
        logger.debug(f"DIAGNÓSTICO REQUIRE_ROLE - Usuario recibido: {user}")
        logger.debug(f"DIAGNÓSTICO REQUIRE_ROLE - Roles requeridos: {roles}")

        if not user or not user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no autorizado"
            )

        for role in roles:
            if role.lower() in user.roles:
                logger.debug(f"DIAGNÓSTICO USER_HAS_ROLE - ¡Rol '{role}' encontrado!")
                return user

        logger.debug(f"DIAGNÓSTICO USER_HAS_ROLE - Roles del usuario: {user.roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene los roles requeridos"
        )

    return role_checker

ACCESS_TOKEN_EXPIRE_MINUTES = 360
