"""
Router para recuperación de contraseña de administradores
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import BaseModel
try:
    from pydantic import EmailStr
except ImportError:
    # Fallback si email-validator no está instalado
    EmailStr = str
import logging

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from security.security import encriptar_clave
from Services.mail.mail import enviar_email_simple
from config import SECRET_KEY, ALGORITHM, BASE_URL

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin-password-reset"]
)

# Configurar templates
import os
# __file__ está en Projects/Admin/routes/password_reset.py
# templates está en Projects/Admin/templates/
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates_dir = os.path.abspath(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

PASSWORD_RESET_EXPIRE_MINUTES = 60

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str

@router.get("/recuperar-password", response_class=HTMLResponse, name="admin_password_reset")
async def password_reset_page(request: Request):
    """Página de recuperación de contraseña para administradores"""
    try:
        logger.info(f"Templates directory: {templates_dir}")
        logger.info(f"Templates directory exists: {os.path.exists(templates_dir)}")
        if os.path.exists(templates_dir):
            logger.info(f"Files in templates dir: {os.listdir(templates_dir)}")
        return templates.TemplateResponse("recuperar_password.html", {"request": request})
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error loading template: {str(e)}")

@router.post("/recuperar-password/solicitar")
async def request_password_reset(
    data: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Solicitar enlace de recuperación de contraseña"""
    try:
        # Buscar usuario por email
        usuario = db.query(Usuarios).filter(Usuarios.mail == data.email).first()
        
        if usuario and usuario.activo:
            # Crear token JWT
            token_data = {
                "sub": usuario.usuario,
                "user_id": usuario.codigo,
                "email": usuario.mail,
                "type": "admin_password_reset",
                "exp": datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
            }
            
            reset_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            
            # Crear enlace
            reset_link = f"{BASE_URL}/admin/recuperar-password/confirmar?token={reset_token}"
            
            # Preparar email
            message = f"""
Hola {usuario.nombre},

Recibimos una solicitud para restablecer la contraseña de tu cuenta de administrador.

Para restablecer tu contraseña, haz clic en el siguiente enlace:

{reset_link}

Este enlace expirará en {PASSWORD_RESET_EXPIRE_MINUTES} minutos.

Si no solicitaste este cambio, ignora este mensaje y tu contraseña permanecerá sin cambios.

Saludos,
Equipo de Administración
            """
            
            # Enviar email en background
            background_tasks.add_task(
                enviar_email_simple,
                data.email,
                "Recuperación de Contraseña - Panel de Administración",
                message
            )
            
            logger.info(f"Solicitud de reset de password para admin: {usuario.usuario}")
        else:
            logger.warning(f"Intento de reset para email no registrado o inactivo: {data.email}")
        
        # Respuesta genérica por seguridad
        return {
            "success": True,
            "message": "Si el correo está registrado, recibirás instrucciones para recuperar tu contraseña"
        }
        
    except Exception as e:
        logger.error(f"Error en solicitud de reset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al procesar la solicitud"
        )

@router.get("/recuperar-password/confirmar", response_class=HTMLResponse, name="admin_password_reset_confirm")
async def password_reset_confirm_page(request: Request, token: str):
    """Página de confirmación con formulario de nueva contraseña"""
    return templates.TemplateResponse(
        "confirmar_password.html",
        {"request": request, "token": token}
    )

@router.post("/recuperar-password/confirmar")
async def confirm_password_reset(
    data: PasswordResetConfirm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Confirmar y actualizar contraseña"""
    try:
        # Validar que las contraseñas coincidan
        if data.new_password != data.confirm_password:
            raise HTTPException(
                status_code=400,
                detail="Las contraseñas no coinciden"
            )
        
        # Validar longitud
        if len(data.new_password) < 6:
            raise HTTPException(
                status_code=400,
                detail="La contraseña debe tener al menos 6 caracteres"
            )
        
        # Verificar token
        try:
            payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            token_type = payload.get("type")
            
            if token_type != "admin_password_reset":
                raise ValueError("Token inválido")
                
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=400,
                detail="El enlace ha expirado. Solicita uno nuevo."
            )
        except JWTError:
            raise HTTPException(
                status_code=400,
                detail="Enlace inválido. Solicita uno nuevo."
            )
        
        # Buscar usuario
        usuario = db.query(Usuarios).filter(Usuarios.codigo == user_id).first()
        
        if not usuario:
            raise HTTPException(
                status_code=400,
                detail="Usuario no encontrado"
            )
        
        if not usuario.activo:
            raise HTTPException(
                status_code=400,
                detail="Usuario inactivo"
            )
        
        # Actualizar contraseña
        nueva_password_hash = encriptar_clave(data.new_password)
        usuario.clave = nueva_password_hash
        db.commit()
        
        logger.info(f"Contraseña actualizada para admin: {usuario.usuario}")
        
        # Enviar email de confirmación
        confirmation_message = f"""
Hola {usuario.nombre},

Tu contraseña de administrador ha sido cambiada exitosamente.

Fecha: {datetime.now().strftime('%d/%m/%Y a las %H:%M')}

Si no realizaste este cambio, contacta inmediatamente con el equipo de soporte.

Saludos,
Equipo de Administración
        """
        
        background_tasks.add_task(
            enviar_email_simple,
            usuario.mail,
            "Contraseña Actualizada - Panel de Administración",
            confirmation_message
        )
        
        return {
            "success": True,
            "message": "Contraseña actualizada correctamente",
            "redirect_url": "/admin/login"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirmando reset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al procesar la solicitud"
        )
