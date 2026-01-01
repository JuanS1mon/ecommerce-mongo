"""
Modelo de Historial de Pedidos para auditoría
Colección en MongoDB: ecomerce_pedido_historial
"""
from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime


class EcomercePedidoHistorial(Document):
    """
    Modelo de historial de cambios de estado de pedidos
    Registra cada cambio de estado para auditoría
    """
    id_pedido: str = Field(..., description="ID del pedido (ObjectId)")
    estado_anterior: str = Field(..., description="Estado anterior del pedido")
    estado_nuevo: str = Field(..., description="Nuevo estado del pedido")
    
    # Usuario admin que realizó el cambio
    id_usuario_admin: Optional[str] = Field(default=None, description="ID del admin que hizo el cambio")
    nombre_usuario_admin: Optional[str] = Field(default=None, description="Nombre del admin")
    
    # Observaciones
    observaciones: Optional[str] = Field(default=None, description="Observaciones del cambio")
    
    # Timestamp
    fecha: datetime = Field(default_factory=datetime.utcnow, description="Fecha del cambio")

    class Settings:
        name = "ecomerce_pedido_historial"

    class Config:
        json_schema_extra = {
            "example": {
                "id_pedido": "507f1f77bcf86cd799439011",
                "estado_anterior": "pendiente",
                "estado_nuevo": "procesando",
                "id_usuario_admin": "507f1f77bcf86cd799439012",
                "nombre_usuario_admin": "Juan Admin",
                "observaciones": "Se verificó el pago",
                "fecha": "2025-12-27T10:30:00"
            }
        }
