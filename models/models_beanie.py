# models_beanie.py
from beanie import Document
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Union, Any
from datetime import datetime

class Servicio(Document):
    nombre: str
    descripcion: str
    tipo_servicio: str  # e.g., "creación web", "ecommerce", "consultoría"
    precio_base: float
    activo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "servicios"

class Producto(Document):
    nombre: str
    descripcion: str
    precio: float
    categoria: str
    imagen_url: Optional[str] = None
    stock: int = 0
    activo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "productos"

class Presupuesto(Document):
    usuario_id: str
    servicio_id: str
    descripcion: str
    precio_estimado: float
    estado: str = "pendiente"  # pendiente, aprobado, rechazado
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "presupuestos"

class Contrato(Document):
    # For budget-based contracts
    presupuesto_id: Optional[str] = None
    # For service-based contracts
    servicio_id: Optional[str] = None
    usuario_id: str
    precio_mensual: Optional[float] = None
    renovacion_automatica: bool = True
    estado: str = "pendiente"  # pendiente, activo, cancelado, expirado
    detalles: str = ""
    duracion_meses: int = 1  # duración en meses
    fecha_contrato: datetime = Field(default_factory=datetime.utcnow)
    fecha_fin: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "contratos"

# Modelo para configuraciones del sitio
class Configuracion(Document):
    key: str  # e.g., "hero_title"
    value: Union[str, int]  # Allow both string and int for backward compatibility
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "configuraciones"

# Mantener modelo de usuario básico
class Usuario(Document):
    username: str
    email: str
    hashed_password: str
    role: str = "usuario"  # usuario, admin
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated_at: Optional[datetime] = None
    last_validation_attempt: Optional[datetime] = None

    class Settings:
        name = "usuarios"
        indexes = [
            "last_validated_at",
        ]

# Modelo para usuarios administradores
class AdminUsuarios(Document):
    usuario: str
    nombre: str
    mail: EmailStr
    clave_hash: str
    activo: bool = Field(default=True)
    imagen_perfil: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "admin_usuarios"

# Modelo para proyectos
class Proyecto(Document):
    nombre: str  # Nombre único del proyecto
    descripcion: str
    activo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "proyectos"
        indexes = [
            "nombre",  # Índice único para búsquedas rápidas
        ]

# Modelo para relación Usuario-Proyecto con fecha de vencimiento
class UsuarioProyecto(Document):
    usuario_id: str
    proyecto_id: str
    fecha_vencimiento: datetime
    activo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "usuario_proyectos"
        indexes = [
            [("usuario_id", 1), ("proyecto_id", 1)],  # Índice compuesto único
        ]