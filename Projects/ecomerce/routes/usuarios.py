# ============================================================================
# Router de gestión de usuarios
# ============================================================================
# Este archivo contiene las rutas y lógica para la gestión de usuarios:
# - Registro, activación, edición de perfil, cambio y recuperación de contraseña.
# - Listado y administración de usuarios (solo admin).
# - Compatible con frontend moderno y flujos de autenticación JWT.
#
# Notas de seguridad:
# - La lógica de autenticación y validación de JWT está centralizada en el middleware y servicios de seguridad.
# - No se recomienda definir SECRET_KEY ni ALGORITHM aquí; deben importarse desde la configuración global del proyecto.
#
# Uso recomendado:
# - Mantener este router enfocado en la gestión de usuarios y delegar la autenticación al middleware y dependencias.
# - Usar las constantes y utilidades de config.py o security para claves y algoritmos.
# ============================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
import jwt
from jose import JWTError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from fastapi import status, Form, Depends

# Configure logger
logger = logging.getLogger(__name__)

# =============================
# CONFIGURACIÓN DE CONSTANTES
# =============================
from config import BASE_URL, SECRET, ALGORITHM  # Usar la configuración global

ACTIVATION_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas
PASSWORD_RESET_EXPIRE_MINUTES = 60      # 1 hora

activation_token_expires = timedelta(minutes=ACTIVATION_TOKEN_EXPIRE_MINUTES)
password_reset_expires = timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)

# Intentos de restablecimiento por IP (rate limiting básico)
reset_attempts = {}
max_reset_attempts = 5  # Limitar a 5 intentos por hora por IP

# Project-specific imports
# from db.models.config.usuarios import Usuarios as UsuariosModel
from Projects.ecomerce.models.usuarios import EcomerceUsuarios as UsuariosModel
# from db.schemas.config.Usuarios import (UserDB, UserRegistration, UserUpdate, PasswordChange,SecurePasswordResetRequest, ConfirmPasswordReset)

# Local Pydantic models for compatibility
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserDB(BaseModel):
    id: Optional[str] = None
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    active: bool = True
    roles: Optional[list] = None

class UserRegistration(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    contraseña: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None

class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class SecurePasswordResetRequest(BaseModel):
    email: EmailStr

class ConfirmPasswordReset(BaseModel):
    token: str
    new_password: str
    confirm_password: str

# from db.crud.config.Usuarios import (get_usuario,create_usuario,update_usuario,delete_usuario,gets_usuarios)

# from security.security import (crear_access_token,get_current_user_secure,get_current_user,get_current_user_for_admin,encriptar_clave,sanitize_for_log,log_security_event,verify_password)

# Local security functions for compatibility
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from config import SECRET_KEY, ALGORITHM


def encriptar_clave(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def sanitize_for_log(data: str) -> str:
    """Sanitize sensitive data for logging"""
    if not data:
        return ""
    if len(data) > 50:
        return data[:20] + "..." + data[-10:]
    return data

def log_security_event(event_type: str, details: dict, level: str = "INFO"):
    """Log security events"""
    import logging
    logger = logging.getLogger(__name__)
    message = f"Security Event: {event_type} - {details}"
    if level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    else:
        logger.info(message)

from Services.mail.mail import validar_email, enviar_email_simple
from security.get_optional_user import get_optional_user
from security.hybrid_validation import validate_password

# Helper function to get client info for logging
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

# Configuración de Jinja2Templates para plantillas HTML
try:
    templates = Jinja2Templates(directory="static")
except Exception as e:
    logger.error(f"Error al inicializar templates: {str(e)}")
    templates = None

router = APIRouter(
    prefix="/user",
    tags=["usuarios"],
)

usuarios_router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios-auth"],
)

# ============================================================================
# NUEVAS RUTAS PARA COMPATIBILIDAD CON FRONTEND
# ============================================================================

# Helper function to get user from request (cookies or headers)
async def get_current_user_from_request(request: Request):
    """Extrae el usuario desde cookies o headers Authorization"""
    token = None

    # Intentar obtener token de Authorization header
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    # Si no hay header Authorization, intentar con cookies
    if not token:
        token = request.cookies.get("access_token") or request.cookies.get("ecommerce_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado"
        )

    try:
        # Decodificar token
        from jose import jwt
        from config import SECRET_KEY, ALGORITHM

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        # Buscar usuario en MongoDB usando Beanie
        user = await UsuariosModel.find_one(
            UsuariosModel.email == email,
            UsuariosModel.active == True
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

@usuarios_router.get("/profile")
async def obtener_perfil_usuario(
    request: Request,
    response: Response,
    user: UsuariosModel = Depends(get_current_user_from_request)
):
    """Obtener información del perfil del usuario autenticado - Endpoint específico para perfil"""
    try:
        # Retornar información del usuario autenticado
        user_data = {
            "id": user.codigo,
            "codigo": user.codigo,
            "usuario": user.usuario,
            "nombre": user.nombre,
            "email": user.mail,
            "mail": user.mail,  # Por compatibilidad
            "imagen_perfil": user.imagen_perfil if hasattr(user, 'imagen_perfil') else None,
            "autenticado": True,
            "activo": user.activo,
            "fecha_creacion": user.fecha_creacion.isoformat() if hasattr(user, 'fecha_creacion') and user.fecha_creacion else None,
            "ultimo_acceso": user.ultimo_acceso.isoformat() if hasattr(user, 'ultimo_acceso') and user.ultimo_acceso else None
        }
        
        # Incluir roles si están disponibles
        if hasattr(user, "roles") and user.roles:
            user_data["roles"] = [
                {
                    "id": role.id if hasattr(role, 'id') else 0,
                    "nombre": role.nombre if hasattr(role, 'nombre') else str(role),
                    "descripcion": role.descripcion if hasattr(role, 'descripcion') else ""
                }
                for role in user.roles
            ]
        else:
            user_data["roles"] = []
        
        # Determinar si es admin (para compatibilidad frontend)
        is_admin = False
        if hasattr(user, "roles") and user.roles:
            is_admin = any(
                role.nombre.lower() in ['admin', 'administrador'] 
                for role in user.roles
            )
        user_data["is_admin"] = is_admin
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error obteniendo perfil del usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo información del perfil"
        )

@usuarios_router.get("/current")
async def obtener_usuario_actual(
    request: Request,
    response: Response,
    user: UsuariosModel = Depends(get_current_user_from_request)
):
    """Obtener información del usuario actualmente autenticado - Compatible con frontend"""
    try:
        # Retornar información del usuario autenticado
        user_data = {
            "id": user.codigo,
            "codigo": user.codigo,
            "usuario": user.usuario,
            "nombre": user.nombre,
            "email": user.mail,
            "mail": user.mail,  # Por compatibilidad
            "imagen_perfil": user.imagen_perfil if hasattr(user, 'imagen_perfil') else None,
            "autenticado": True,
            "activo": user.activo,
            "fecha_creacion": user.fecha_creacion.isoformat() if hasattr(user, 'fecha_creacion') and user.fecha_creacion else None,
            "ultimo_acceso": user.ultimo_acceso.isoformat() if hasattr(user, 'ultimo_acceso') and user.ultimo_acceso else None
        }
        
        # Incluir roles si están disponibles
        if hasattr(user, "roles") and user.roles:
            user_data["roles"] = [
                {
                    "id": role.id if hasattr(role, 'id') else 0,
                    "nombre": role.nombre if hasattr(role, 'nombre') else str(role),
                    "descripcion": role.descripcion if hasattr(role, 'descripcion') else ""
                }
                for role in user.roles
            ]
        else:
            user_data["roles"] = []
        
        # Determinar si es admin (para compatibilidad frontend)
        is_admin = False
        if hasattr(user, "roles") and user.roles:
            is_admin = any(
                role.nombre.lower() in ['admin', 'administrador'] 
                for role in user.roles
            )
        user_data["is_admin"] = is_admin
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo información del usuario"
        )

# ============================================================================
# RUTAS DE GESTIÓN DE USUARIOS
# ============================================================================

@router.post("/registro")
async def registrar_usuario(
    usuario_data: UserRegistration,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Registra nuevo usuario con validaciones de seguridad híbrida (PIN o contraseña segura) y deja inactivo hasta activación por email."""
    client_info = get_client_info(request)
    logger.info(f"Intento de registro: usuario={sanitize_for_log(usuario_data.usuario)}, email={sanitize_for_log(usuario_data.mail)}")
    try:
        # Validar email
        if not validar_email(usuario_data.mail):
            log_security_event(
                "REGISTRATION_FAILED",
                {
                    "reason": "invalid_email",
                    "usuario": sanitize_for_log(usuario_data.usuario),
                    "email": sanitize_for_log(usuario_data.mail),
                    **client_info
                },
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El email no es válido"
            )
        # Verificar si el usuario ya existe
        existing_user = get_usuario(db, usuario=usuario_data.usuario)
        if existing_user:
            log_security_event(
                "REGISTRATION_FAILED",
                {
                    "reason": "user_exists",
                    "usuario": sanitize_for_log(usuario_data.usuario),
                    **client_info
                },
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de usuario ya está en uso"
            )
        # VALIDACIÓN HÍBRIDA: PIN o contraseña segura
        validation_result = validate_password(usuario_data.clave)
        if not validation_result["valid"]:
            log_security_event(
                "REGISTRATION_FAILED",
                {
                    "reason": "invalid_password",
                    "usuario": sanitize_for_log(usuario_data.usuario),
                    "password_type": validation_result.get("type", "unknown"),
                    **client_info
                },
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=validation_result["message"]
            )
        # Log tipo de autenticación seleccionado
        auth_type = "PIN" if validation_result.get("type") == "pin" else "Contraseña Segura"
        logger.info(f"Usuario {sanitize_for_log(usuario_data.usuario)} registrado con {auth_type}")
        # Encriptar contraseña
        clave_encriptada = encriptar_clave(usuario_data.clave)
        # Crear usuario INACTIVO
        result = create_usuario(
            db=db,
            nombre=usuario_data.nombre,
            usuario=usuario_data.usuario,
            clave=clave_encriptada,
            mail=usuario_data.mail,
            activo=False  # <-- usuario inactivo hasta activación
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando usuario"
            )
        # Crear token de activación
        token_activacion = crear_access_token(
            data={"sub": usuario_data.usuario, "type": "activation"},
            expires_delta=activation_token_expires
        )
        # Enviar email de activación
        try:
            if validar_email(usuario_data.mail):
                activation_link = f"{BASE_URL}/user/activar-cuenta?token={token_activacion}"
                background_tasks.add_task(
                    enviar_email_simple,
                    usuario_data.mail,
                    "Activa tu cuenta",
                    f"""
                    Bienvenido/a {usuario_data.nombre},\n\nPor favor activa tu cuenta haciendo clic en el siguiente enlace:\n{activation_link}\n\nEste enlace expira en 24 horas.\n\nSi no solicitaste esto, ignora este mensaje.
                    """
                )
                logger.info(f"Email de activación enviado a {sanitize_for_log(usuario_data.mail)}")
        except Exception as e:
            logger.warning(f"Error validando/enviando email de activación: {str(e)}")
        log_security_event(
            "USER_REGISTERED",
            {
                "usuario": sanitize_for_log(usuario_data.usuario),
                "email": sanitize_for_log(usuario_data.mail),
                **client_info
            },
            "INFO"
        )
        return JSONResponse(
            content={
                "message": "Usuario registrado exitosamente. Revisa tu email para activar la cuenta.",
                "usuario": usuario_data.usuario,
                "activacion_requerida": True
            },
            status_code=status.HTTP_201_CREATED
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en registro: {str(e)}")
        log_security_event(
            "REGISTRATION_ERROR",
            {"error": str(e), **client_info},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.get("/activar-cuenta")
async def activar_cuenta(token: Optional[str] = Query(None)):
    """Activa la cuenta de usuario usando el token enviado por email."""
    try:
        if not token:
            raise HTTPException(
                status_code=400, 
                detail="Token de activación requerido. Por favor, usa el enlace enviado a tu email."
            )
        payload = jwt.decode(token, SECRET.key, algorithms=[ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("type")
        if not username or token_type != "activation":
            raise HTTPException(status_code=400, detail="Token inválido")
        user = db.query(UsuariosModel).filter(UsuariosModel.usuario == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if user.activo:
            return {"message": "La cuenta ya está activada"}
        user.activo = True
        db.commit()
        log_security_event(
            "USER_ACTIVATED",
            {"usuario": sanitize_for_log(username)},
            "INFO"
        )
        return {"message": "Cuenta activada exitosamente. Ya puedes iniciar sesión."}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="El enlace de activación ha expirado")
    except Exception as e:
        log_security_event(
            "USER_ACTIVATION_ERROR",
            {"error": str(e)},
            "ERROR"
        )
        raise HTTPException(status_code=400, detail="Token inválido o error de activación")
