"""
Schemas para el sistema de validación externa de usuarios
Define los modelos de request/response para el endpoint de validación
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ValidateRequest(BaseModel):
    """
    Schema para la solicitud de validación de acceso
    """
    email: EmailStr = Field(..., description="Email del usuario registrado")
    password: str = Field(..., description="Contraseña del usuario")
    proyecto_nombre: str = Field(..., description="Nombre exacto del proyecto (case-sensitive)")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "password": "mi_password_seguro",
                "proyecto_nombre": "CRM Ventas 2026"
            }
        }


class DatosUsuario(BaseModel):
    """
    Datos básicos del usuario para incluir en la respuesta
    """
    email: str = Field(..., description="Email del usuario")
    username: str = Field(..., description="Nombre de usuario")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "username": "juanperez"
            }
        }


class ValidateResponse(BaseModel):
    """
    Schema para la respuesta de validación de acceso
    """
    valid: bool = Field(..., description="true si el acceso es válido, false si no")
    mensaje: str = Field(..., description="Descripción del resultado de la validación")
    datos_usuario: Optional[DatosUsuario] = Field(None, description="Datos del usuario (solo si valid=true)")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha de vencimiento del acceso (solo si valid=true)")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "mensaje": "Acceso válido",
                "datos_usuario": {
                    "email": "usuario@ejemplo.com",
                    "username": "juanperez"
                },
                "fecha_vencimiento": "2027-01-11T23:59:59Z"
            }
        }
