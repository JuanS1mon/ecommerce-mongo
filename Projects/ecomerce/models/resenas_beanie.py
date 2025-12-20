from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EcomerceResenas(Document):
    id_usuario: str
    id_producto: str
    calificacion: int = Field(ge=1, le=5)  # 1-5 estrellas
    comentario: Optional[str] = None
    titulo: Optional[str] = None
    verificada: bool = Field(default=False)  # Si el usuario compró el producto
    util: int = Field(default=0)  # Votos de utilidad
    no_util: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ecomerce_resenas"

class ResenaCreate(BaseModel):
    id_producto: str
    calificacion: int = Field(ge=1, le=5)
    comentario: Optional[str] = None
    titulo: Optional[str] = None

class ResenaResponse(BaseModel):
    id: str
    id_usuario: str
    id_producto: str
    calificacion: int
    comentario: Optional[str]
    titulo: Optional[str]
    verificada: bool
    util: int
    no_util: int
    created_at: datetime
    nombre_usuario: Optional[str] = None  # Para mostrar en frontend