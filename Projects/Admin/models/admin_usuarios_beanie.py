"""
Modelo de Usuarios Administradores para el Panel Admin
Colección separada en MongoDB: admin_usuarios
"""
from beanie import Document
from pydantic import Field, EmailStr
from typing import Optional
from datetime import datetime


class AdminUsuarios(Document):
    """
    Modelo de usuarios administradores del sistema
    Colección: admin_usuarios (separada de ecomerce_usuarios)
    """
    usuario: str = Field(..., description="Username único del administrador")
    nombre: str = Field(..., description="Nombre completo del administrador")
    mail: EmailStr = Field(..., description="Email del administrador")
    clave_hash: str = Field(..., description="Contraseña hasheada con bcrypt")
    activo: bool = Field(default=True, description="Estado activo/inactivo")
    imagen_perfil: Optional[str] = Field(default=None, description="URL de imagen de perfil")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")

    class Settings:
        name = "admin_usuarios"  # Nombre de la colección en MongoDB

    class Config:
        json_schema_extra = {
            "example": {
                "usuario": "juan",
                "nombre": "Juan Admin",
                "mail": "juan@admin.com",
                "clave_hash": "$2b$12$...",
                "activo": True
            }
        }
