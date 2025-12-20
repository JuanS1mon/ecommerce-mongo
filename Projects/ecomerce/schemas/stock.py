from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class StockCreate(BaseModel):
    id: Optional[int] = None
    id_producto: int
    cantidad_disponible: int
    cantidad_reservada: int
    ubicacion: str
    updated_at: datetime

class StockUpdate(BaseModel):
    id: Optional[int] = None
    id_producto: Optional[int] = None
    cantidad_disponible: Optional[int] = None
    cantidad_reservada: Optional[int] = None
    ubicacion: Optional[str] = None
    updated_at: Optional[datetime] = None

class StockRead(BaseModel):
    id: int
    id_producto: int
    cantidad_disponible: int
    cantidad_reservada: int
    ubicacion: str
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
