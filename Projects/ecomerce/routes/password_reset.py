"""
Router para la gestión de restablecimiento de contraseñas
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import traceback

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError

from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from Projects.ecomerce.routes.usuarios import SecurePasswordResetRequest, ConfirmPasswordReset, log_security_event, sanitize_for_log
from config import SECRET_KEY, ALGORITHM, BASE_URL
from Services.mail.mail import enviar_email_simple

# Configuración de contraseñas local
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encriptar_clave(password: str) -> str:
    """Encripta una contraseña usando bcrypt"""
    return pwd_context.hash(password)

# Configure logger
logger = logging.getLogger(__name__)

# Verificar que la función esté importada
try:
    assert enviar_email_simple is not None
    logger.info("Función enviar_email_simple importada correctamente")
except (NameError, AssertionError) as e:
    logger.error(f"Error importando enviar_email_simple: {e}")
    enviar_email_simple = None

# Crear router
router = APIRouter(
    tags=["auth"],
    responses={404: {"description": "Not Found"}},
)

# Verificar que el modelo se importe correctamente
try:
    # El modelo ya está importado arriba, solo verificar que existe
    assert EcomerceUsuarios is not None
    logger.info("Modelo EcomerceUsuarios importado correctamente")
except (ImportError, AssertionError) as e:
    logger.error(f"Error importando EcomerceUsuarios: {e}")
    EcomerceUsuarios = None

# Configuration constants
PASSWORD_RESET_EXPIRE_MINUTES = 60  # 1 hour

# Create timedelta objects for token expiration
password_reset_expires = timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)

# Función para resetear rate limiting (para debugging)
def reset_rate_limiting():
    """Resetea el rate limiting para testing"""
    global reset_attempts
    reset_attempts = {}
    logger.info("Rate limiting reseteado para testing")

# Intentos de restablecimiento por IP
reset_attempts = {}
max_reset_attempts = 5  # Limitar a 5 intentos por hora por IP

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
        "ip": client_ip,
        "user_agent": user_agent
    }

# Configuración de Jinja2Templates para plantillas HTML
try:
    import os
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    templates = Jinja2Templates(directory=static_dir)
except Exception as e:
    logger.error(f"Error al inicializar templates: {str(e)}")
    templates = None

@router.post("/test-email")
async def test_email():
    """Ruta temporal para probar envío de email"""
    try:
        result = enviar_email_simple(
            "fjuansimon@gmail.com",
            "Test de email",
            "Este es un email de prueba para verificar la configuración SMTP."
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error en test email: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/password-reset", response_class=HTMLResponse)
async def password_reset_page(request: Request):
    """Página de recuperación de contraseña (alias)"""
    if templates is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sistema de plantillas no disponible"
        )
    return templates.TemplateResponse("reset_password.html", {"request": request})

@router.post("/test-full-password-reset")
async def test_full_password_reset():
    """Endpoint para probar el flujo completo de password reset sin BD"""
    try:
        logger.info("=== TEST FULL PASSWORD RESET ===")
        
        # Simular usuario encontrado
        user_email = "fjuansimon@gmail.com"
        user_name = "Juan"
        
        logger.info(f"Simulando usuario encontrado: {user_email}")
        
        # Crear token JWT
        token_data = {
            "sub": user_email,
            "email": user_email,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(minutes=15)
        }
        
        reset_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        reset_link = f"{BASE_URL}/confirm-password-reset?token={reset_token}"
        
        message = f"""
Hola {user_name},

Recibimos una solicitud para restablecer tu contraseña.

Si solicitaste restablecer tu contraseña, haz clic en el siguiente enlace:
{reset_link}

Este enlace expira en 15 minutos.

Si no solicitaste esto, puedes ignorar este mensaje con seguridad.

Saludos,
El equipo de soporte
        """
        
        logger.info("Enviando email...")
        result = enviar_email_simple(
            user_email,
            "Restablecimiento de contraseña - Acción requerida",
            message
        )
        
        logger.info(f"Resultado del envío: {result}")
        
        return {
            "message": "Flujo completo simulado",
            "user_found": True,
            "token_created": True,
            "email_sent": True,
            "result": str(result),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error en test full password reset: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "message": "Error en el flujo",
            "error": str(e),
            "success": False
        }

@router.post("/password-reset-request")
async def password_reset_request(
    request_data: SecurePasswordResetRequest, 
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Solicita reset de contraseña con protecciones de seguridad"""
    try:
        logger.info(f"=== INICIO PASSWORD RESET REQUEST ===")
        logger.info(f"Email recibido: {request_data.email}")
        
        client_info = get_client_info(request)
        
        # Rate limiting por IP
        client_ip = client_info.get("ip", "unknown")
        current_time = datetime.now()
        
        # Limpiar intentos antiguos (más de 1 hora)
        reset_attempts[client_ip] = [
            attempt for attempt in reset_attempts.get(client_ip, [])
            if current_time - attempt < timedelta(hours=1)
        ]
        
        # Verificar límite de intentos
        # TEMPORALMENTE DESHABILITADO PARA TESTING
        if False:  # len(reset_attempts.get(client_ip, [])) >= max_reset_attempts:
            log_security_event(
                "PASSWORD_RESET_RATE_LIMIT_EXCEEDED",
                {"email": sanitize_for_log(request_data.email), **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos de restablecimiento. Intenta de nuevo en 1 hora."
            )
        
        # Registrar intento
        reset_attempts.setdefault(client_ip, []).append(current_time)
        
        logger.info(f"Password reset request recibida para: {sanitize_for_log(request_data.email)}")
        
        # Buscar usuario por email
        logger.info("Buscando usuario en tabla ecomerce_usuarios...")
        
        try:
            logger.info(f"Buscando usuario en MongoDB con email: {request_data.email}")
            user = await EcomerceUsuarios.find_one(
                EcomerceUsuarios.email == request_data.email,
                EcomerceUsuarios.activo == True
            )
            
            # Si no se encuentra con 'activo', intentar con 'active' (compatibilidad con datos existentes)
            if not user:
                logger.info("Usuario no encontrado con campo 'activo', intentando con 'active'...")
                # Usar consulta directa con MongoDB para compatibilidad
                from db.database import database
                collection = database["ecomerce_usuarios"]
                user_doc = await collection.find_one({
                    "email": request_data.email,
                    "active": True
                })
                if user_doc:
                    # Convertir documento MongoDB a objeto Beanie
                    user = EcomerceUsuarios(**user_doc)
                    logger.info("Usuario encontrado usando campo 'active'")
            logger.info(f"Resultado de consulta MongoDB: {'Encontrado' if user else 'No encontrado'}")
            if user:
                logger.info(f"Usuario encontrado: ID={user.id}, Email={user.email}, Nombre={user.nombre}, Activo={user.activo}")
            else:
                logger.info("Usuario NO encontrado en MongoDB")
                # Devolver respuesta indicando que no se encontró el usuario
                return {
                    "message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña",
                    "success": True,
                    "debug": {"user_found": False, "email": request_data.email}
                }
        except Exception as query_error:
            logger.error(f"Error en consulta de usuario: {str(query_error)}")
            logger.error(f"Tipo de error: {type(query_error)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            user = None
        
        if user:
            logger.info(f"Creando token para usuario: {sanitize_for_log(user.email)}")
            
            # Crear token JWT con información del usuario
            token_data = {
                "sub": user.email,  # Usar email como identificador único
                "email": user.email,
                "type": "password_reset",
                "exp": datetime.utcnow() + password_reset_expires
            }
            
            reset_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            
            # Crear enlace de restablecimiento
            reset_link = f"{BASE_URL}/confirm-password-reset?token={reset_token}"
            
            message = f"""Hola {user.nombre},

Recibimos una solicitud para restablecer tu contraseña.

Si solicitaste restablecer tu contraseña, haz clic en el siguiente enlace:
{reset_link}

Este enlace expira en {PASSWORD_RESET_EXPIRE_MINUTES} minutos.

Si no solicitaste esto, puedes ignorar este mensaje con seguridad.

Saludos,
El equipo de soporte"""
            
            try:
                # TEMPORALMENTE SIN BACKGROUND TASK PARA DEBUGGING
                logger.info("Enviando email de password reset de manera síncrona...")
                result = enviar_email_simple(
                    request_data.email,
                    "Restablecimiento de contraseña - Acción requerida",
                    message
                )
                logger.info(f"Resultado del envío de email: {result}")
                
                # Incluir información de debug en la respuesta
                debug_info = {
                    "email_sent": True,
                    "result": str(result),
                    "user_found": True,
                    "user_email": user.email,
                    "token_created": True
                }
                
                # background_tasks.add_task(
                #     enviar_email_simple,
                #     request_data.email,
                #     "Restablecimiento de contraseña - Acción requerida",
                #     message
                # )
                # logger.info("Email programado para envío exitosamente")
                
                log_security_event(
                    "PASSWORD_RESET_TOKEN_SENT",
                    {"email": sanitize_for_log(request_data.email), "user_id": user.id, **client_info},
                    "INFO"
                )
                
                # Devolver respuesta con debug info
                return {
                    "message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña",
                    "success": True,
                    "debug": debug_info
                }
            except Exception as email_error:
                logger.error(f"Error programando envío de email: {str(email_error)}")
                log_security_event(
                    "PASSWORD_RESET_EMAIL_ERROR",
                    {"email": sanitize_for_log(request_data.email), "error": str(email_error), **client_info},
                    "ERROR"
                )
        else:
            # Log security event for non-existent email attempts
            log_security_event(
                "PASSWORD_RESET_NONEXISTENT_EMAIL",
                {"email": sanitize_for_log(request_data.email), **client_info},
                "WARNING"
            )
        
        # Respuesta genérica por seguridad (no revelar si el email existe)
        return {
            "message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña",
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en password reset request: {str(e)}")
        log_security_event(
            "PASSWORD_RESET_UNEXPECTED_ERROR",
            {"email": sanitize_for_log(request_data.email), "error": str(e), **client_info},
            "ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando solicitud"
        )
        
    except Exception as global_error:
        logger.error(f"Error global en password reset request: {str(global_error)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "message": "Error procesando solicitud",
            "success": False,
            "debug": {"error": str(global_error)}
        }

@router.get("/confirm-password-reset", response_class=HTMLResponse)
async def confirm_password_reset_page(request: Request):
    """Página para confirmar el reset de contraseña con token"""
    logger.info("=== CONFIRM PASSWORD RESET PAGE ===")
    logger.info(f"Templates object: {templates}")
    logger.info(f"Templates is None: {templates is None}")
    
    if templates is None:
        logger.error("Sistema de plantillas no disponible")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sistema de plantillas no disponible"
        )
    
    try:
        logger.info("Intentando renderizar plantilla confirm_password_reset.html")
        response = templates.TemplateResponse("confirm_password_reset.html", {"request": request})
        logger.info("Plantilla renderizada exitosamente")
        return response
    except Exception as e:
        logger.error(f"Error al renderizar plantilla: {str(e)}")
        logger.error(f"Tipo de error: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al renderizar plantilla: {str(e)}"
        )

@router.post("/confirm-password-reset")
async def confirm_password_reset(
    reset_data: ConfirmPasswordReset,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Confirma el reset de contraseña con token y nueva contraseña"""
    client_info = get_client_info(request)
    
    logger.info("=== CONFIRM PASSWORD RESET POST ===")
    logger.info(f"Token recibido: {reset_data.token[:20]}...")
    logger.info(f"New password length: {len(reset_data.new_password)}")
    
    try:
        if reset_data.new_password != reset_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las contraseñas no coinciden"
            )
        
        # Validar longitud mínima de contraseña
        if len(reset_data.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 6 caracteres"
            )
        
        # Validar longitud máxima de contraseña (bcrypt limita a 72 bytes)
        if len(reset_data.new_password.encode('utf-8')) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña es demasiado larga. Máximo 72 bytes permitidos."
            )
        
        logger.info("Validaciones de contraseña completadas, procediendo con token...")
        # Verificar y decodificar el token
        logger.info("Intentando decodificar token JWT")
        try:
            logger.info(f"SECRET_KEY disponible: {bool(SECRET_KEY)}")
            logger.info(f"ALGORITHM: {ALGORITHM}")
            payload = jwt.decode(reset_data.token, SECRET_KEY, algorithms=[ALGORITHM])
            logger.info(f"Token decodificado exitosamente: {payload}")
            username = payload.get("sub")
            token_type = payload.get("type")
            email = payload.get("email")
            
            if not username:
                raise ValueError("Token no contiene username")
                
            if token_type != "password_reset":
                raise ValueError("Token no es de reset de contraseña")
                
        except jwt.ExpiredSignatureError:
            log_security_event(
                "PASSWORD_RESET_TOKEN_EXPIRED",
                {"token": sanitize_for_log(reset_data.token[:20]), **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enlace de restablecimiento ha expirado. Solicita uno nuevo."
            )
        except JWTError as jwt_error:
            log_security_event(
                "PASSWORD_RESET_INVALID_TOKEN",
                {"token": sanitize_for_log(reset_data.token[:20]), "error": str(jwt_error), **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enlace de restablecimiento inválido. Solicita uno nuevo."
            )
        except Exception as token_error:
            log_security_event(
                "PASSWORD_RESET_TOKEN_ERROR",
                {"token": sanitize_for_log(reset_data.token[:20]), "error": str(token_error), **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enlace de restablecimiento inválido o expirado. Solicita uno nuevo."
            )
        
        # Buscar usuario
        logger.info(f"Buscando usuario con email: {username}")
        try:
            user = await EcomerceUsuarios.find_one(
                EcomerceUsuarios.email == username,
                EcomerceUsuarios.activo == True
            )
            logger.info(f"Consulta con sintaxis Beanie ejecutada, resultado: {user is not None}")
        except Exception as query_error:
            logger.error(f"Error en consulta Beanie: {str(query_error)}")
            logger.info("Intentando consulta con diccionario...")
            user = await EcomerceUsuarios.find_one({"email": username, "activo": True})
            logger.info(f"Consulta con diccionario ejecutada, resultado: {user is not None}")
        
        if not user:
            log_security_event(
                "PASSWORD_RESET_USER_NOT_FOUND",
                {"username": sanitize_for_log(username), **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enlace de restablecimiento inválido o expirado"
            )
        
        # Verificar que el email coincida
        if email and user.email != email:
            log_security_event(
                "PASSWORD_RESET_EMAIL_MISMATCH",
                {"username": sanitize_for_log(username), "expected_email": sanitize_for_log(email), **client_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enlace de restablecimiento inválido o expirado"
            )
        
        # Verificar que la nueva contraseña no sea igual a la actual
        try:
            from security.security import verificar_clave
            if verificar_clave(reset_data.new_password, user.contraseña_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La nueva contraseña debe ser diferente a la actual"
                )
        except Exception:
            # Si hay error verificando, continuar (mejor que fallar)
            pass
        
        # Encriptar nueva contraseña
        new_password_hash = encriptar_clave(reset_data.new_password)
        
        # Actualizar contraseña en base de datos
        user.contraseña_hash = new_password_hash
        await user.save()
        
        log_security_event(
            "PASSWORD_RESET_COMPLETED",
            {"username": sanitize_for_log(username), "user_id": user.id, **client_info},
            "INFO"
        )
        
        # Enviar email de confirmación en background
        confirmation_message = f"""
Hola {user.nombre},

Tu contraseña ha sido cambiada exitosamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}.

Detalles del cambio:
- IP: {client_info.get('ip', 'No disponible')}
- Fecha: {datetime.now().strftime('%d de %B de %Y a las %H:%M')}

Si no realizaste esta acción, por favor contacta inmediatamente con nuestro equipo de soporte.

Por tu seguridad, te recomendamos:
- Usar contraseñas únicas y seguras
- No compartir tus credenciales
- Cerrar sesión en dispositivos públicos

Saludos,
El equipo de soporte
        """
        
        try:
            background_tasks.add_task(
                enviar_email_simple,
                user.email,
                "Contraseña cambiada exitosamente - Notificación de seguridad",
                confirmation_message
            )
        except Exception as email_error:
            # Log pero no fallar si no se puede enviar email de confirmación
            logger.warning(f"No se pudo programar email de confirmación: {str(email_error)}")
        
        return {
            "message": "Contraseña actualizada exitosamente. Puedes iniciar sesión con tu nueva contraseña.",
            "success": True,
            "redirect_url": "/login"  # Para que el frontend pueda redirigir
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en confirm password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando solicitud"
        )

@router.get("/test-endpoint")
async def test_endpoint():
    """Endpoint de prueba simple"""
    logger.info("Test endpoint called")
    return {"message": "Test endpoint working"}
