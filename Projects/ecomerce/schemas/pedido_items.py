from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class PedidoItemsCreate(BaseModel):
    id_pedido: int
    id_producto: int
    cantidad: int
    precio_unitario: float
    nombre_producto: str

class PedidoItemsUpdate(BaseModel):
    cantidad: Optional[int] = None
    precio_unitario: Optional[float] = None

class PedidoItemsRead(BaseModel):
    id: int
    id_pedido: int
    id_producto: int
    cantidad: int
    precio_unitario: float
    nombre_producto: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
