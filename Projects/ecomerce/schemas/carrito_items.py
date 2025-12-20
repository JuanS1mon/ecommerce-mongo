from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class Carrito_itemsCreate(BaseModel):
    id: Optional[int] = None
    id_carrito: int
    id_producto: int
    cantidad: int
    precio_unitario: float

class Carrito_itemsUpdate(BaseModel):
    id: Optional[int] = None
    id_carrito: Optional[int] = None
    id_producto: Optional[int] = None
    cantidad: Optional[int] = None
    precio_unitario: Optional[float] = None

class Carrito_itemsRead(BaseModel):
    id: int
    id_carrito: int
    id_producto: int
    cantidad: int
    precio_unitario: float
    model_config = ConfigDict(from_attributes=True)

class Carrito_itemsSimpleCreate(BaseModel):
    product_id: int
    quantity: int = 1
    price: float = 0.0
