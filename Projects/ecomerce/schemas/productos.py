from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class ProductVariantCreate(BaseModel):
    color: Optional[str] = None
    tipo: Optional[str] = None
    precio_adicional: int = 0
    stock: int = 0
    imagen_url: Optional[str] = None
    active: bool = True

class ProductVariantUpdate(BaseModel):
    color: Optional[str] = None
    tipo: Optional[str] = None
    precio_adicional: Optional[int] = None
    stock: Optional[int] = None
    imagen_url: Optional[str] = None
    active: Optional[bool] = None

class ProductVariantRead(BaseModel):
    id: int
    product_id: int
    color: Optional[str]
    tipo: Optional[str]
    precio_adicional: int
    stock: int
    imagen_url: Optional[str]
    active: bool
    model_config = ConfigDict(from_attributes=True)

class ProductosCreate(BaseModel):
    id: Optional[int] = None
    codigo: str
    nombre: str
    descripcion: str
    id_categoria: int
    precio: int
    imagen_url: str
    active: bool
    variants: Optional[List[ProductVariantCreate]] = None

class ProductosUpdate(BaseModel):
    id: Optional[int] = None
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    id_categoria: Optional[int] = None
    precio: Optional[int] = None
    imagen_url: Optional[str] = None
    active: Optional[bool] = None
    variants: Optional[List[ProductVariantUpdate]] = None

class ProductosRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str
    id_categoria: int
    precio: int
    imagen_url: str
    active: bool
    variants: Optional[List[ProductVariantRead]] = None
    model_config = ConfigDict(from_attributes=True)
