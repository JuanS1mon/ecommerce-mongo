from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class CategoriasCreate(BaseModel):
    id: Optional[int] = None
    nombre: str
    descripcion: str
    id_padre: int
    created_at: datetime
    active: bool

class CategoriasUpdate(BaseModel):
    id: Optional[int] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    id_padre: Optional[int] = None
    created_at: Optional[datetime] = None
    active: Optional[bool] = None

class CategoriasRead(BaseModel):
    id: int
    nombre: str
    descripcion: str
    id_padre: int
    created_at: datetime
    active: bool
    model_config = ConfigDict(from_attributes=True)
