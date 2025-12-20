from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class UsuariosCreate(BaseModel):
    id: Optional[int] = None
    nombre: str
    apellido: str
    email: str
    contraseña_hash: str
    telefono: str
    direccion: str
    ciudad: str
    provincia: str
    pais: str
    created_at: datetime
    active: bool
    cuit: str

class UsuariosUpdate(BaseModel):
    id: Optional[int] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[str] = None
    contraseña_hash: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    google_maps_link: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
    created_at: Optional[datetime] = None
    active: Optional[bool] = None
    cuit: Optional[str] = None

class UsuariosRead(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    contraseña_hash: str
    telefono: str
    direccion: str
    ciudad: str
    provincia: str
    pais: str
    created_at: datetime
    active: bool
    cuit: str
    model_config = ConfigDict(from_attributes=True)

class UsuariosProfile(BaseModel):
    id: int
    nombre: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    google_maps_link: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
    created_at: Optional[datetime] = None
    active: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)

class UserProfileComplete(BaseModel):
    user: dict  # Cambiar a dict para ser más flexible
    orders: List[dict]  # Lista de pedidos con items
    active_cart: Optional[dict]  # Carrito activo con items
    budgets: List[dict]  # Presupuestos
    orders_count: Optional[int] = 0
    budgets_count: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)
