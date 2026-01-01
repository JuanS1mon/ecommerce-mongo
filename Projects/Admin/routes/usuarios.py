"""
Router de Administración de Usuarios para Admin - MongoDB/Beanie
CRUD de usuarios del ecommerce y admin
"""
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from bson import ObjectId
from beanie.operators import Or, RegEx

from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/usuarios",
    tags=["admin-usuarios"]
)


@router.get("/", response_class=HTMLResponse)
async def lista_usuarios_view(request: Request):
    """Vista de lista de usuarios (clientes ecommerce y usuarios admin)"""
    try:
        return render_admin_template(
            "usuarios_admin.html",
            request,
            active_page="usuarios"
        )
    except Exception as e:
        logger.error(f"Error cargando usuarios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando usuarios"
        )


@router.get("/api/sistema/list")
async def listar_usuarios_sistema_api(
    admin_user: AdminUsuarios = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    activo: Optional[bool] = None
):
    """
    API para listar usuarios del sistema (admins) con filtros
    
    Query params:
    - skip: Número de usuarios a saltar (paginación)
    - limit: Número máximo de usuarios a devolver
    - search: Buscar por usuario, nombre o email
    - activo: Filtrar por estado activo
    """
    try:
        # Construir filtros
        filtros = []
        
        if search:
            filtros.append(
                Or(
                    RegEx(AdminUsuarios.usuario, search, "i"),
                    RegEx(AdminUsuarios.nombre, search, "i"),
                    RegEx(AdminUsuarios.mail, search, "i")
                )
            )
        
        if activo is not None:
            filtros.append(AdminUsuarios.activo == activo)
        
        # Obtener usuarios con filtros
        if filtros:
            query = AdminUsuarios.find(*filtros)
        else:
            query = AdminUsuarios.find()
        
        # Total de usuarios
        total = await query.count()
        
        # Obtener usuarios paginados
        usuarios = await query.skip(skip).limit(limit).to_list()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "usuarios": [
                {
                    "id": str(u.id),
                    "usuario": u.usuario,
                    "nombre": u.nombre,
                    "email": u.mail,
                    "activo": u.activo,
                    "fecha_creacion": u.created_at.isoformat() if u.created_at else None,
                    "ultimo_acceso": u.updated_at.isoformat() if u.updated_at else None
                }
                for u in usuarios
            ]
        }
    except Exception as e:
        logger.error(f"Error listando usuarios del sistema: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando usuarios"
        )


@router.get("/api/ecommerce/list")
async def listar_usuarios_ecommerce_api(
    admin_user: AdminUsuarios = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    activo: Optional[bool] = None
):
    """API para listar usuarios del ecommerce con filtros"""
    try:
        # Construir filtros
        filtros = []
        
        if search:
            filtros.append(
                Or(
                    RegEx(EcomerceUsuarios.nombre, search, "i"),
                    RegEx(EcomerceUsuarios.email, search, "i")
                )
            )
        
        if activo is not None:
            filtros.append(EcomerceUsuarios.activo == activo)
        
        # Obtener usuarios con filtros
        if filtros:
            query = EcomerceUsuarios.find(*filtros)
        else:
            query = EcomerceUsuarios.find()
        
        # Total de usuarios
        total = await query.count()
        
        # Obtener usuarios paginados
        usuarios = await query.skip(skip).limit(limit).to_list()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "usuarios": [
                {
                    "id": str(u.id),
                    "nombre": u.nombre,
                    "email": u.email,
                    "telefono": u.telefono if hasattr(u, 'telefono') else None,
                    "direccion": u.direccion if hasattr(u, 'direccion') else None,
                    "activo": u.activo,
                    "fecha_registro": u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else None
                }
                for u in usuarios
            ]
        }
    except Exception as e:
        logger.error(f"Error listando usuarios del ecommerce: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando usuarios"
        )


@router.get("/api/sistema/{usuario_id}")
async def obtener_usuario_sistema(
    usuario_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener detalles de un usuario del sistema (admin)"""
    try:
        usuario = await AdminUsuarios.get(ObjectId(usuario_id))
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return {
            "id": str(usuario.id),
            "usuario": usuario.usuario,
            "nombre": usuario.nombre,
            "email": usuario.mail,
            "activo": usuario.activo,
            "fecha_creacion": usuario.created_at.isoformat() if usuario.created_at else None,
            "ultimo_acceso": usuario.updated_at.isoformat() if usuario.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario del sistema: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo usuario"
        )


@router.put("/api/sistema/{usuario_id}/toggle-active")
async def toggle_usuario_sistema_activo(
    usuario_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Activar/desactivar un usuario del sistema"""
    try:
        usuario = await AdminUsuarios.get(ObjectId(usuario_id))
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Evitar que el admin se desactive a sí mismo
        if str(usuario.id) == str(admin_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivar tu propia cuenta"
            )
        
        # Cambiar el estado
        usuario.activo = not usuario.activo
        await usuario.save()
        
        logger.info(
            f"Usuario {usuario.usuario} {'activado' if usuario.activo else 'desactivado'} "
            f"por admin {admin_user.usuario}"
        )
        
        return {
            "message": f"Usuario {'activado' if usuario.activo else 'desactivado'} exitosamente",
            "usuario_id": usuario_id,
            "activo": usuario.activo
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando estado del usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cambiando estado del usuario"
        )


@router.put("/api/ecommerce/{usuario_id}/toggle-active")
async def toggle_usuario_ecommerce_activo(
    usuario_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Activar/desactivar un usuario del ecommerce"""
    try:
        # Buscar usuario por ObjectId
        usuario = await EcomerceUsuarios.get(ObjectId(usuario_id))
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Cambiar el estado
        usuario.activo = not usuario.activo
        await usuario.save()
        
        logger.info(
            f"Usuario ecommerce {usuario.nombre} {'activado' if usuario.activo else 'desactivado'} "
            f"por admin {admin_user.usuario}"
        )
        
        return {
            "message": f"Usuario {'activado' if usuario.activo else 'desactivado'} exitosamente",
            "usuario_id": usuario_id,
            "activo": usuario.activo
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando estado del usuario ecommerce: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cambiando estado del usuario"
        )


@router.get("/api/ecommerce/{usuario_id}")
async def obtener_usuario_ecommerce(
    usuario_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener detalles de un usuario del ecommerce"""
    try:
        usuario = await EcomerceUsuarios.get(ObjectId(usuario_id))
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return {
            "id": str(usuario.id),
            "nombre": usuario.nombre,
            "email": usuario.email,
            "telefono": usuario.telefono if hasattr(usuario, 'telefono') else None,
            "direccion": usuario.direccion if hasattr(usuario, 'direccion') else None,
            "ciudad": usuario.ciudad if hasattr(usuario, 'ciudad') else None,
            "activo": usuario.activo,
            "fecha_registro": usuario.created_at.isoformat() if hasattr(usuario, 'created_at') and usuario.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario del ecommerce: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo usuario"
        )


@router.put("/api/ecommerce/{usuario_id}")
async def actualizar_usuario_ecommerce(
    usuario_id: str,
    nombre: Optional[str] = None,
    email: Optional[str] = None,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None,
    ciudad: Optional[str] = None,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Actualizar información de un usuario del ecommerce"""
    try:
        usuario = await EcomerceUsuarios.get(ObjectId(usuario_id))
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Actualizar campos si se proporcionaron
        if nombre is not None:
            usuario.nombre = nombre
        if email is not None:
            # Verificar que el email no esté en uso por otro usuario
            existing = await EcomerceUsuarios.find_one(
                EcomerceUsuarios.email == email,
                EcomerceUsuarios.id != usuario.id
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está en uso por otro usuario"
                )
            usuario.email = email
        if telefono is not None:
            usuario.telefono = telefono
        if direccion is not None:
            usuario.direccion = direccion
        if ciudad is not None:
            usuario.ciudad = ciudad
        
        usuario.updated_at = datetime.utcnow()
        await usuario.save()
        
        logger.info(f"Usuario ecommerce {usuario.nombre} actualizado por admin {admin_user.usuario}")
        
        return {
            "message": "Usuario actualizado exitosamente",
            "usuario": {
                "id": str(usuario.id),
                "nombre": usuario.nombre,
                "email": usuario.email,
                "telefono": usuario.telefono if hasattr(usuario, 'telefono') else None,
                "direccion": usuario.direccion if hasattr(usuario, 'direccion') else None,
                "ciudad": usuario.ciudad if hasattr(usuario, 'ciudad') else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando usuario: {str(e)}"
        )


@router.put("/api/ecommerce/{usuario_id}/password")
async def cambiar_password_usuario_ecommerce(
    usuario_id: str,
    nueva_password: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Cambiar contraseña de un usuario del ecommerce"""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        usuario = await EcomerceUsuarios.get(ObjectId(usuario_id))
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Validar que la contraseña tenga al menos 6 caracteres
        if len(nueva_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 6 caracteres"
            )
        
        # Hashear la nueva contraseña
        usuario.contraseña_hash = pwd_context.hash(nueva_password)
        usuario.updated_at = datetime.utcnow()
        await usuario.save()
        
        logger.info(f"Contraseña del usuario {usuario.nombre} cambiada por admin {admin_user.usuario}")
        
        return {
            "message": "Contraseña actualizada exitosamente",
            "usuario_id": usuario_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cambiando contraseña: {str(e)}"
        )
