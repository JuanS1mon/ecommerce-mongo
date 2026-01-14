# routers/admin_proyectos.py
from fastapi import APIRouter, HTTPException, Depends
from models.models_beanie import Proyecto, UsuarioProyecto
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from routers.admin_auth import get_current_admin_user
from beanie import PydanticObjectId

router = APIRouter()

class ProyectoCreate(BaseModel):
    nombre: str
    descripcion: str

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

class ProyectoToggle(BaseModel):
    activo: bool

@router.get("/admin/proyectos")
async def get_proyectos(admin=Depends(get_current_admin_user)):
    """Lista todos los proyectos con conteo de usuarios asignados"""
    proyectos = await Proyecto.find_all().to_list()
    result = []
    
    for proyecto in proyectos:
        # Contar usuarios asignados a este proyecto
        usuarios_count = await UsuarioProyecto.find(
            UsuarioProyecto.proyecto_id == str(proyecto.id)
        ).count()
        
        result.append({
            "id": str(proyecto.id),
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "activo": proyecto.activo,
            "usuarios_asignados": usuarios_count,
            "created_at": proyecto.created_at.isoformat(),
            "updated_at": proyecto.updated_at.isoformat()
        })
    
    return result

@router.post("/admin/proyectos")
async def create_proyecto(data: ProyectoCreate, admin=Depends(get_current_admin_user)):
    """Crear nuevo proyecto con validación de nombre único"""
    # Verificar que el nombre sea único
    existing = await Proyecto.find_one(Proyecto.nombre == data.nombre)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un proyecto con el nombre '{data.nombre}'"
        )
    
    proyecto = Proyecto(
        nombre=data.nombre,
        descripcion=data.descripcion,
        activo=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await proyecto.insert()
    
    return {
        "id": str(proyecto.id),
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "activo": proyecto.activo,
        "message": "Proyecto creado exitosamente"
    }

@router.put("/admin/proyectos/{proyecto_id}")
async def update_proyecto(
    proyecto_id: str,
    data: ProyectoUpdate,
    admin=Depends(get_current_admin_user)
):
    """Actualizar proyecto existente"""
    proyecto = await Proyecto.get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Si se está actualizando el nombre, verificar que sea único
    if data.nombre and data.nombre != proyecto.nombre:
        existing = await Proyecto.find_one(Proyecto.nombre == data.nombre)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un proyecto con el nombre '{data.nombre}'"
            )
        proyecto.nombre = data.nombre
    
    if data.descripcion is not None:
        proyecto.descripcion = data.descripcion
    
    proyecto.updated_at = datetime.utcnow()
    await proyecto.save()
    
    return {
        "id": str(proyecto.id),
        "nombre": proyecto.nombre,
        "descripcion": proyecto.descripcion,
        "activo": proyecto.activo,
        "message": "Proyecto actualizado exitosamente"
    }

@router.post("/admin/proyectos/{proyecto_id}/toggle")
async def toggle_proyecto(
    proyecto_id: str,
    data: ProyectoToggle,
    admin=Depends(get_current_admin_user)
):
    """Activar o desactivar proyecto"""
    proyecto = await Proyecto.get(proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    proyecto.activo = data.activo
    proyecto.updated_at = datetime.utcnow()
    await proyecto.save()
    
    estado = "activado" if data.activo else "desactivado"
    return {
        "id": str(proyecto.id),
        "nombre": proyecto.nombre,
        "activo": proyecto.activo,
        "message": f"Proyecto {estado} exitosamente"
    }
