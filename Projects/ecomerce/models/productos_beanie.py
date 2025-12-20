from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class EcomerceProductos(Document):
    codigo: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    id_categoria: str = Field(default="")
    precio: int = Field(default=0)
    imagen_url: Optional[str] = None
    active: bool = Field(default=False)

    class Settings:
        name = "ecomerce_productos"

class ProductoVariante(BaseModel):
    color: Optional[str] = None
    tipo: Optional[str] = None
    precio_adicional: int = Field(default=0)
    stock: int = Field(default=0)
    imagen_url: Optional[str] = None
    active: bool = Field(default=True)

class EcomerceProductosVariantes(Document):
    product_id: str  # Referencia al ObjectId del producto
    color: Optional[str] = None
    tipo: Optional[str] = None
    modelo: Optional[str] = None  # Campo dinámico agregado
    precio_adicional: int = Field(default=0)
    stock: int = Field(default=0)
    imagen_url: Optional[str] = None
    active: bool = Field(default=True)
    estado: Optional[str] = None  # Campo agregado para estado

    class Settings:
        name = "ecomerce_productos_variantes"
