"""
Router de Validación Externa de Usuarios
Endpoint público para validar acceso de usuarios a proyectos específicos
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import bcrypt

from Projects.Admin.schemas.validacion_externa import ValidateRequest, ValidateResponse, DatosUsuario
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Validación Externa"])


@router.get(
    "/proyecto/{proyecto_nombre}/usuarios",
    summary="Listar usuarios admin de un proyecto",
    description="""
    Endpoint público para listar todos los usuarios administradores vinculados a un proyecto.
    
    **Uso:** Este endpoint permite sincronizar usuarios entre sistemas.
    
    **Retorna:**
    - Lista de usuarios con email, username, activo, fecha_vencimiento
    - Solo usuarios vinculados al proyecto especificado
    """,
    responses={
        200: {
            "description": "Lista de usuarios del proyecto",
            "content": {
                "application/json": {
                    "example": {
                        "proyecto": "Ecomerce",
                        "usuarios": [
                            {
                                "email": "admin@sysneg.com",
                                "username": "admin",
                                "activo": True,
                                "fecha_vencimiento": "2026-07-03T23:59:59Z",
                                "clave_hash": "$2b$12$..."
                            }
                        ],
                        "total": 1
                    }
                }
            }
        },
        404: {
            "description": "Proyecto no encontrado"
        }
    }
)
async def listar_usuarios_proyecto(proyecto_nombre: str, request: Request):
    """
    Lista todos los usuarios administradores vinculados a un proyecto específico.
    
    Args:
        proyecto_nombre: Nombre del proyecto
        request: Request object para logging
        
    Returns:
        JSONResponse con la lista de usuarios
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"[LISTA USUARIOS] Solicitud desde IP {client_ip} - Proyecto: {proyecto_nombre}")
        
        # Buscar proyecto
        proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
        
        if not proyecto:
            logger.warning(f"[LISTA USUARIOS] Proyecto no encontrado: {proyecto_nombre}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Proyecto no encontrado",
                    "proyecto": proyecto_nombre
                }
            )
        
        # Buscar todas las vinculaciones del proyecto
        vinculaciones = await UsuarioProyecto.find(
            UsuarioProyecto.proyecto_id == proyecto.id
        ).to_list()
        
        # Obtener datos de cada usuario
        usuarios_data = []
        
        for vinc in vinculaciones:
            usuario = await AdminUsuarios.get(vinc.usuario_id)
            
            if usuario:
                usuarios_data.append({
                    "email": usuario.mail,
                    "username": usuario.usuario,
                    "nombre": usuario.nombre,
                    "activo": usuario.activo and vinc.activo,  # Ambos deben estar activos
                    "fecha_vencimiento": vinc.fecha_vencimiento.isoformat() + "Z" if vinc.fecha_vencimiento else None,
                    "clave_hash": usuario.clave_hash  # Para sincronización
                })
        
        logger.info(f"[LISTA USUARIOS] Encontrados {len(usuarios_data)} usuarios para proyecto {proyecto_nombre}")
        
        return JSONResponse(
            status_code=200,
            content={
                "proyecto": proyecto_nombre,
                "proyecto_activo": proyecto.activo,
                "usuarios": usuarios_data,
                "total": len(usuarios_data)
            }
        )
    
    except Exception as e:
        logger.error(f"[LISTA USUARIOS] Error listando usuarios: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Error interno del servidor",
                "detalle": str(e)
            }
        )


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validar acceso de usuario a proyecto",
    description="""
    Endpoint público para validar credenciales de usuario y su acceso a un proyecto específico.
    
    **Características:**
    - No requiere autenticación previa
    - CORS habilitado
    - Valida credenciales + asignación al proyecto + vencimiento
    - Registra automáticamente los intentos de acceso
    
    **Casos de rechazo:**
    - Credenciales inválidas
    - Usuario inactivo
    - Proyecto no encontrado
    - Proyecto inactivo
    - Usuario no asignado al proyecto
    - Acceso vencido
    - Vinculación inactiva
    """,
    responses={
        200: {
            "description": "Validación procesada (puede ser válida o inválida)",
            "content": {
                "application/json": {
                    "examples": {
                        "acceso_valido": {
                            "summary": "Acceso válido",
                            "value": {
                                "valid": True,
                                "mensaje": "Acceso válido",
                                "datos_usuario": {
                                    "email": "usuario@ejemplo.com",
                                    "username": "juanperez"
                                },
                                "fecha_vencimiento": "2027-01-11T23:59:59Z"
                            }
                        },
                        "acceso_denegado": {
                            "summary": "Acceso denegado",
                            "value": {
                                "valid": False,
                                "mensaje": "Usuario no asignado a este proyecto"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def validate_user_project_access(request_data: ValidateRequest, request: Request):
    """
    Valida el acceso de un usuario a un proyecto específico.
    
    Args:
        request_data: Datos de validación (email, password, proyecto_nombre)
        request: Request object para logging
        
    Returns:
        ValidateResponse con el resultado de la validación
    """
    try:
        # Registrar intento de validación
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"[VALIDACIÓN] Intento desde IP {client_ip} - Email: {request_data.email}, Proyecto: {request_data.proyecto_nombre}")
        
        # 1. Buscar usuario por email
        usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == request_data.email)
        
        if not usuario:
            logger.warning(f"[VALIDACIÓN] Usuario no encontrado: {request_data.email}")
            return ValidateResponse(
                valid=False,
                mensaje="Credenciales inválidas"
            )
        
        # 2. Verificar contraseña
        password_bytes = request_data.password.encode('utf-8')
        clave_hash_bytes = usuario.clave_hash.encode('utf-8')
        
        if not bcrypt.checkpw(password_bytes, clave_hash_bytes):
            logger.warning(f"[VALIDACIÓN] Contraseña incorrecta para: {request_data.email}")
            # Actualizar last_validation_attempt (intento fallido)
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Credenciales inválidas"
            )
        
        # 3. Verificar que el usuario esté activo
        if not usuario.activo:
            logger.warning(f"[VALIDACIÓN] Usuario inactivo: {request_data.email}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Usuario no está activo"
            )
        
        # 4. Buscar proyecto por nombre (case-sensitive)
        proyecto = await Proyecto.find_one(Proyecto.nombre == request_data.proyecto_nombre)
        
        if not proyecto:
            logger.warning(f"[VALIDACIÓN] Proyecto no encontrado: {request_data.proyecto_nombre}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Proyecto no encontrado"
            )
        
        # 5. Verificar que el proyecto esté activo
        if not proyecto.activo:
            logger.warning(f"[VALIDACIÓN] Proyecto inactivo: {request_data.proyecto_nombre}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="El proyecto no está activo"
            )
        
        # 6. Buscar vinculación usuario-proyecto
        vinculacion = await UsuarioProyecto.find_one(
            UsuarioProyecto.usuario_id == usuario.id,
            UsuarioProyecto.proyecto_id == proyecto.id
        )
        
        if not vinculacion:
            logger.warning(f"[VALIDACIÓN] Usuario {request_data.email} no asignado al proyecto {request_data.proyecto_nombre}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Usuario no asignado a este proyecto"
            )
        
        # 7. Verificar que la vinculación esté activa
        if not vinculacion.activo:
            logger.warning(f"[VALIDACIÓN] Vinculación inactiva para {request_data.email} - {request_data.proyecto_nombre}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="La vinculación está inactiva"
            )
        
        # 8. Verificar fecha de vencimiento (si existe)
        if vinculacion.fecha_vencimiento:
            ahora = datetime.utcnow()
            if ahora > vinculacion.fecha_vencimiento:
                logger.warning(f"[VALIDACIÓN] Acceso vencido para {request_data.email} - {request_data.proyecto_nombre}")
                await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
                return ValidateResponse(
                    valid=False,
                    mensaje="El acceso al proyecto ha vencido"
                )
        
        # 9. ACCESO VÁLIDO - Actualizar tracking
        await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=True)
        
        logger.info(f"[VALIDACIÓN] ✅ Acceso válido para {request_data.email} - {request_data.proyecto_nombre}")
        
        # Preparar respuesta exitosa
        return ValidateResponse(
            valid=True,
            mensaje="Acceso válido",
            datos_usuario=DatosUsuario(
                email=usuario.mail,
                username=usuario.usuario
            ),
            fecha_vencimiento=vinculacion.fecha_vencimiento
        )
    
    except Exception as e:
        logger.error(f"[VALIDACIÓN] Error en validación: {str(e)}", exc_info=True)
        return ValidateResponse(
            valid=False,
            mensaje="Error interno del servidor"
        )


async def _update_validation_attempt(usuario_id, proyecto_nombre: str, success: bool):
    """
    Actualiza los campos de tracking de validación en la vinculación usuario-proyecto.
    
    Args:
        usuario_id: ID del usuario
        proyecto_nombre: Nombre del proyecto
        success: True si la validación fue exitosa, False si falló
    """
    try:
        # Buscar el proyecto
        proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
        if not proyecto:
            return
        
        # Buscar la vinculación
        vinculacion = await UsuarioProyecto.find_one(
            UsuarioProyecto.usuario_id == usuario_id,
            UsuarioProyecto.proyecto_id == proyecto.id
        )
        
        if vinculacion:
            ahora = datetime.utcnow()
            vinculacion.last_validation_attempt = ahora
            
            if success:
                vinculacion.last_validated_at = ahora
            
            vinculacion.updated_at = ahora
            await vinculacion.save()
            
            logger.debug(f"[TRACKING] Actualizado tracking para usuario {usuario_id} - proyecto {proyecto_nombre}")
    
    except Exception as e:
        logger.error(f"[TRACKING] Error al actualizar tracking: {str(e)}")
