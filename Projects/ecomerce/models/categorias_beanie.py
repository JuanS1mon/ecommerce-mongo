from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EcomerceCategorias(Document):
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    id_padre: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)

    class Settings:
        name = "ecomerce_categorias"
