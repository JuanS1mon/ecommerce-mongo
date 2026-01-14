# routers/admin_users.py
from fastapi import APIRouter, HTTPException, Query
from models.models_beanie import Usuario, Contrato, Servicio, Presupuesto, Proyecto, UsuarioProyecto
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import math
from security.security import hash_password
from routers.admin_auth import get_current_admin_user
from fastapi import Depends

router = APIRouter()

class UserToggle(BaseModel):
    active: bool

class ChangePasswordRequest(BaseModel):
    new_password: str

class AsignarProyectoRequest(BaseModel):
    proyecto_id: str
    fecha_vencimiento: str  # ISO 8601 format

class ActualizarVencimientoRequest(BaseModel):
    fecha_vencimiento: str  # ISO 8601 format

@router.get("/admin/users")
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Lista usuarios con paginación y proyectos asignados"""
    skip = (page - 1) * limit
    
    # Obtener total de usuarios para calcular páginas
    total = await Usuario.find_all().count()
    
    # Obtener usuarios con paginación
    users = await Usuario.find_all().skip(skip).limit(limit).to_list()
    result = []
    
    for user in users:
        # Buscar proyectos asignados al usuario
        usuario_proyectos = await UsuarioProyecto.find(
            UsuarioProyecto.usuario_id == str(user.id)
        ).to_list()
        
        proyectos_info = []
        todos_vencidos = True
        tiene_proyectos = len(usuario_proyectos) > 0
        
        for up in usuario_proyectos:
            # Obtener información del proyecto
            proyecto = await Proyecto.get(up.proyecto_id)
            if not proyecto:
                continue
            
            now = datetime.utcnow()
            dias_restantes = (up.fecha_vencimiento - now).days
            esta_vencido = up.fecha_vencimiento < now
            
            if not esta_vencido and up.activo and proyecto.activo:
                todos_vencidos = False
            
            estado = "vencido" if esta_vencido else "activo"
            
            proyectos_info.append({
                "proyecto_id": str(proyecto.id),
                "nombre": proyecto.nombre,
                "fecha_vencimiento": up.fecha_vencimiento.isoformat(),
                "dias_restantes": dias_restantes if not esta_vencido else 0,
                "estado": estado,
                "proyecto_activo": proyecto.activo,
                "vinculacion_activa": up.activo
            })
        
        # Validación lazy: desactivar usuario si todos los proyectos están vencidos
        if tiene_proyectos and todos_vencidos and user.is_active:
            user.is_active = False
            await user.save()
        
        result.append({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "proyectos": proyectos_info,
            "sin_proyectos": not tiene_proyectos,
            "last_validated_at": user.last_validated_at.isoformat() if user.last_validated_at else None,
            "last_validation_attempt": user.last_validation_attempt.isoformat() if user.last_validation_attempt else None,
            "created_at": user.created_at.isoformat()
        })
    
    total_pages = math.ceil(total / limit)
    
    return {
        "users": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": total_pages
    }

@router.post("/admin/users/{user_id}/toggle")
async def toggle_user(user_id: str, data: UserToggle, admin=Depends(get_current_admin_user)):
    from beanie import PydanticObjectId
    
    try:
        obj_id = PydanticObjectId(user_id)
        user = await Usuario.get(obj_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Usuario no encontrado: {str(e)}")
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.is_active = data.active
    await user.save()
    return {"message": "Estado actualizado"}

@router.post("/admin/users/{user_id}/change-password")
async def change_user_password(user_id: str, data: ChangePasswordRequest, admin=Depends(get_current_admin_user)):
    from beanie import PydanticObjectId
    
    try:
        # Convertir string a ObjectId
        obj_id = PydanticObjectId(user_id)
        user = await Usuario.get(obj_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Usuario no encontrado: {str(e)}")
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.hashed_password = hash_password(data.new_password)
    await user.save()
    return {"message": "Contraseña cambiada exitosamente"}

# ===== ENDPOINTS DE GESTIÓN DE PROYECTOS DE USUARIO =====

@router.post("/admin/users/{user_id}/proyectos")
async def asignar_proyecto(
    user_id: str,
    data: AsignarProyectoRequest,
    admin=Depends(get_current_admin_user)
):
    """Asignar un proyecto a un usuario con fecha de vencimiento"""
    # Verificar que el usuario existe
    user = await Usuario.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar que el proyecto existe
    proyecto = await Proyecto.get(data.proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que no existe ya esta asignación
    existing = await UsuarioProyecto.find_one(
        UsuarioProyecto.usuario_id == user_id,
        UsuarioProyecto.proyecto_id == data.proyecto_id
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"El usuario ya está asignado al proyecto '{proyecto.nombre}'"
        )
    
    # Parsear fecha de vencimiento
    try:
        fecha_vencimiento = datetime.fromisoformat(data.fecha_vencimiento.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido. Use formato ISO 8601 (ej: 2026-12-31T23:59:59Z)"
        )
    
    # Crear la asignación
    usuario_proyecto = UsuarioProyecto(
        usuario_id=user_id,
        proyecto_id=data.proyecto_id,
        fecha_vencimiento=fecha_vencimiento,
        activo=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await usuario_proyecto.insert()
    
    # Activar el usuario
    if not user.is_active:
        user.is_active = True
        await user.save()
    
    return {
        "message": "Proyecto asignado exitosamente",
        "usuario": user.email,
        "proyecto": proyecto.nombre,
        "fecha_vencimiento": fecha_vencimiento.isoformat(),
        "usuario_activo": user.is_active
    }

@router.get("/admin/users/{user_id}/proyectos")
async def get_proyectos_usuario(
    user_id: str,
    admin=Depends(get_current_admin_user)
):
    """Listar todos los proyectos asignados a un usuario"""
    user = await Usuario.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    usuario_proyectos = await UsuarioProyecto.find(
        UsuarioProyecto.usuario_id == user_id
    ).to_list()
    
    result = []
    for up in usuario_proyectos:
        proyecto = await Proyecto.get(up.proyecto_id)
        if not proyecto:
            continue
        
        now = datetime.utcnow()
        dias_restantes = (up.fecha_vencimiento - now).days
        esta_vencido = up.fecha_vencimiento < now
        
        result.append({
            "id": str(up.id),
            "proyecto_id": str(proyecto.id),
            "proyecto_nombre": proyecto.nombre,
            "proyecto_descripcion": proyecto.descripcion,
            "proyecto_activo": proyecto.activo,
            "fecha_vencimiento": up.fecha_vencimiento.isoformat(),
            "dias_restantes": dias_restantes,
            "estado": "vencido" if esta_vencido else "activo",
            "vinculacion_activa": up.activo,
            "created_at": up.created_at.isoformat()
        })
    
    return {
        "usuario": {
            "id": user_id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active
        },
        "proyectos": result
    }

@router.put("/admin/users/{user_id}/proyectos/{proyecto_id}")
async def actualizar_vencimiento_proyecto(
    user_id: str,
    proyecto_id: str,
    data: ActualizarVencimientoRequest,
    admin=Depends(get_current_admin_user)
):
    """Actualizar fecha de vencimiento de un proyecto asignado"""
    usuario_proyecto = await UsuarioProyecto.find_one(
        UsuarioProyecto.usuario_id == user_id,
        UsuarioProyecto.proyecto_id == proyecto_id
    )
    
    if not usuario_proyecto:
        raise HTTPException(
            status_code=404,
            detail="Asignación de proyecto no encontrada"
        )
    
    # Parsear nueva fecha
    try:
        nueva_fecha = datetime.fromisoformat(data.fecha_vencimiento.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido. Use formato ISO 8601"
        )
    
    usuario_proyecto.fecha_vencimiento = nueva_fecha
    usuario_proyecto.updated_at = datetime.utcnow()
    await usuario_proyecto.save()
    
    proyecto = await Proyecto.get(proyecto_id)
    
    return {
        "message": "Fecha de vencimiento actualizada",
        "proyecto": proyecto.nombre if proyecto else "Desconocido",
        "nueva_fecha_vencimiento": nueva_fecha.isoformat()
    }

@router.delete("/admin/users/{user_id}/proyectos/{proyecto_id}")
async def desvincular_proyecto(
    user_id: str,
    proyecto_id: str,
    admin=Depends(get_current_admin_user)
):
    """Desvincular un proyecto de un usuario"""
    usuario_proyecto = await UsuarioProyecto.find_one(
        UsuarioProyecto.usuario_id == user_id,
        UsuarioProyecto.proyecto_id == proyecto_id
    )
    
    if not usuario_proyecto:
        raise HTTPException(
            status_code=404,
            detail="Asignación de proyecto no encontrada"
        )
    
    proyecto = await Proyecto.get(proyecto_id)
    proyecto_nombre = proyecto.nombre if proyecto else "Desconocido"
    
    await usuario_proyecto.delete()
    
    return {
        "message": "Proyecto desvinculado exitosamente",
        "proyecto": proyecto_nombre
    }