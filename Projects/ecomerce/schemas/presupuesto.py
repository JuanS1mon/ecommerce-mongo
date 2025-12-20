from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Modelo Pydantic para la solicitud de presupuesto
class PresupuestoRequest(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str
    mensaje: str

    class Config:
        from_attributes = True

# Modelo Pydantic para la respuesta
class PresupuestoResponse(BaseModel):
    id: int
    nombre: str
    email: str
    telefono: str
    mensaje: str
    fecha_creacion: datetime
    estado: str

    class Config:
        from_attributes = True
