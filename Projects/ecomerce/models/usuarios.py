from beanie import Document
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class EcomerceUsuarios(Document):
    nombre: str
    email: EmailStr
    contraseña_hash: Optional[str] = None
    google_id: Optional[str] = None
    google_email: Optional[str] = None
    google_name: Optional[str] = None
    google_picture: Optional[str] = None
    profile_image: Optional[str] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    genero: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
    rol: str = Field(default="user")
    roles: Optional[List[str]] = None
    activo: bool = Field(default=True)
    email_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ecomerce_usuarios"