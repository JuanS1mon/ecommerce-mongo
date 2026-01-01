"""
Modelo de Configuraciones del Sistema
Colección en MongoDB: ecomerce_configuracion
"""
from beanie import Document
from pydantic import Field
from typing import Optional, Any
from datetime import datetime


class EcomerceConfiguracion(Document):
    """
    Modelo de configuraciones generales del sistema
    Almacena pares clave-valor con metadatos
    """
    clave: str = Field(..., description="Clave única de configuración", unique=True)
    valor: Any = Field(..., description="Valor de la configuración (puede ser cualquier tipo)")
    descripcion: Optional[str] = Field(default=None, description="Descripción de la configuración")
    tipo: str = Field(default="string", description="Tipo de dato: string, int, float, bool, json")
    
    # Metadata
    categoria: Optional[str] = Field(default="general", description="Categoría de la configuración")
    es_publica: bool = Field(default=False, description="Si es visible públicamente")
    modificable: bool = Field(default=True, description="Si puede ser modificada por admin")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")
    updated_by: Optional[str] = Field(default=None, description="ID del admin que actualizó")

    class Settings:
        name = "ecomerce_configuracion"

    class Config:
        json_schema_extra = {
            "example": {
                "clave": "nombre_tienda",
                "valor": "Mi Tienda Online",
                "descripcion": "Nombre de la tienda que aparece en el sitio",
                "tipo": "string",
                "categoria": "general",
                "es_publica": True,
                "modificable": True
            }
        }
