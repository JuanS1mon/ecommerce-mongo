"""
Modelo de Presupuestos para el sistema de ecommerce
Colección en MongoDB: ecomerce_presupuestos
"""
from beanie import Document
from pydantic import Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class EcomercePresupuestos(Document):
    """
    Modelo de presupuestos solicitados por clientes
    Items embebidos como lista de diccionarios
    """
    id_usuario: str = Field(..., description="ID del usuario que solicita el presupuesto")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Items del presupuesto")
    # Estructura de items: [{"id_producto": str, "nombre": str, "cantidad": int, "precio_unitario": int, "subtotal": int}]
    
    total: int = Field(default=0, description="Total del presupuesto")
    estado: str = Field(default="pendiente", description="Estado: pendiente, aprobado, rechazado, enviado")
    
    # Información de contacto
    nombre_cliente: Optional[str] = Field(default=None, description="Nombre del cliente")
    email_cliente: Optional[str] = Field(default=None, description="Email del cliente")
    telefono_cliente: Optional[str] = Field(default=None, description="Teléfono del cliente")
    
    # Notas y observaciones
    notas_cliente: Optional[str] = Field(default=None, description="Notas del cliente")
    notas_admin: Optional[str] = Field(default=None, description="Notas del administrador")
    
    # Timestamps
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")
    fecha_respuesta: Optional[datetime] = Field(default=None, description="Fecha de respuesta del admin")

    class Settings:
        name = "ecomerce_presupuestos"

    class Config:
        json_schema_extra = {
            "example": {
                "id_usuario": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "id_producto": "507f1f77bcf86cd799439012",
                        "nombre": "Producto Ejemplo",
                        "cantidad": 2,
                        "precio_unitario": 1000,
                        "subtotal": 2000
                    }
                ],
                "total": 2000,
                "estado": "pendiente",
                "nombre_cliente": "Juan Pérez",
                "email_cliente": "juan@example.com"
            }
        }
