"""
Modelos para el Sistema de Proyectos y Validación Externa
Maneja proyectos y la vinculación de usuarios con fechas de vencimiento
"""
from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import datetime


class Proyecto(Document):
    """
    Modelo de Proyectos del sistema
    Colección: proyectos
    Representa un proyecto al cual los usuarios pueden estar vinculados
    """
    nombre: str = Field(..., description="Nombre único del proyecto (case-sensitive)")
    descripcion: Optional[str] = Field(None, description="Descripción del proyecto")
    activo: bool = Field(default=True, description="Estado activo/inactivo del proyecto")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")

    class Settings:
        name = "proyectos"
        indexes = [
            "nombre",  # Índice para búsquedas por nombre
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "CRM Ventas 2026",
                "descripcion": "Sistema CRM para gestión de ventas",
                "activo": True
            }
        }


class UsuarioProyecto(Document):
    """
    Modelo de Vinculación Usuario-Proyecto
    Colección: usuario_proyectos
    Relaciona usuarios administradores con proyectos específicos
    """
    usuario_id: PydanticObjectId = Field(..., description="ID del usuario en admin_usuarios")
    proyecto_id: PydanticObjectId = Field(..., description="ID del proyecto")
    fecha_asignacion: datetime = Field(default_factory=datetime.utcnow, description="Fecha de asignación")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha de vencimiento del acceso (null = sin vencimiento)")
    activo: bool = Field(default=True, description="Estado activo/inactivo de la vinculación")
    
    # Campos de tracking
    last_validation_attempt: Optional[datetime] = Field(None, description="Último intento de validación (exitoso o fallido)")
    last_validated_at: Optional[datetime] = Field(None, description="Última validación exitosa")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")

    class Settings:
        name = "usuario_proyectos"
        indexes = [
            "usuario_id",
            "proyecto_id",
            [("usuario_id", 1), ("proyecto_id", 1)],  # Índice compuesto para búsquedas combinadas
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "usuario_id": "507f1f77bcf86cd799439011",
                "proyecto_id": "507f1f77bcf86cd799439012",
                "fecha_asignacion": "2026-01-01T00:00:00Z",
                "fecha_vencimiento": "2027-01-01T23:59:59Z",
                "activo": True
            }
        }
