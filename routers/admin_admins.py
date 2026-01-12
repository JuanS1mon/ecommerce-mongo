# routers/admin_admins.py
from fastapi import APIRouter, HTTPException
from models.models_beanie import AdminUsuarios
from pydantic import BaseModel, EmailStr
from typing import List
from security.security import hash_password
from routers.admin_auth import get_current_admin_user
from fastapi import Depends
from datetime import datetime

router = APIRouter()

class AdminToggle(BaseModel):
    activo: bool

class ChangeAdminPasswordRequest(BaseModel):
    new_password: str

class CreateAdminRequest(BaseModel):
    usuario: str
    nombre: str
    mail: EmailStr
    password: str
    activo: bool = True

@router.get("/admin/admins")
async def get_admins(current_admin=Depends(get_current_admin_user)):
    admins = await AdminUsuarios.find_all().to_list()
    result = []
    for admin in admins:
        result.append({
            "id": str(admin.id),
            "usuario": admin.usuario,
            "nombre": admin.nombre,
            "mail": admin.mail,
            "activo": admin.activo,
            "created_at": admin.created_at.strftime("%Y-%m-%d")
        })
    return result

@router.post("/admin/admins")
async def create_admin(data: CreateAdminRequest, current_admin=Depends(get_current_admin_user)):
    # Verificar si el usuario ya existe
    existing_admin = await AdminUsuarios.find_one(AdminUsuarios.usuario == data.usuario)
    if existing_admin:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    # Verificar si el email ya existe
    existing_email = await AdminUsuarios.find_one(AdminUsuarios.mail == data.mail)
    if existing_email:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Validar contraseña
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    # Crear nuevo administrador
    new_admin = AdminUsuarios(
        usuario=data.usuario,
        nombre=data.nombre,
        mail=data.mail,
        clave_hash=hash_password(data.password),
        activo=data.activo,
        created_at=datetime.now()
    )
    
    await new_admin.insert()
    
    return {
        "message": "Administrador creado exitosamente",
        "admin": {
            "id": str(new_admin.id),
            "usuario": new_admin.usuario,
            "nombre": new_admin.nombre,
            "mail": new_admin.mail,
            "activo": new_admin.activo
        }
    }

@router.post("/admin/admins/{admin_id}/toggle")
async def toggle_admin(admin_id: str, data: AdminToggle, current_admin=Depends(get_current_admin_user)):
    admin = await AdminUsuarios.find_one(AdminUsuarios.id == admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin no encontrado")
    admin.activo = data.activo
    await admin.save()
    return {"message": "Estado actualizado"}

@router.post("/admin/admins/{admin_id}/change-password")
async def change_admin_password(admin_id: str, data: ChangeAdminPasswordRequest, current_admin=Depends(get_current_admin_user)):
    admin = await AdminUsuarios.find_one(AdminUsuarios.id == admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin no encontrado")
    admin.clave_hash = hash_password(data.new_password)
    await admin.save()
    return {"message": "Contraseña cambiada exitosamente"}