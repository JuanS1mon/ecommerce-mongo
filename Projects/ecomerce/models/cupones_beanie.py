from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TipoDescuento(str, Enum):
    PORCENTAJE = "porcentaje"
    MONTO_FIJO = "monto_fijo"
    ENVIO_GRATIS = "envio_gratis"

class EcomerceCupones(Document):
    codigo: str = Field(unique=True)
    descripcion: str
    tipo_descuento: TipoDescuento
    valor_descuento: float  # porcentaje (0-100) o monto fijo
    monto_minimo: Optional[float] = None  # Monto mínimo para aplicar
    usos_maximos: Optional[int] = None
    usos_actuales: int = Field(default=0)
    fecha_expiracion: Optional[datetime] = None
    activo: bool = Field(default=True)
    productos_aplicables: Optional[List[str]] = None  # IDs de productos específicos, None = todos
    categorias_aplicables: Optional[List[str]] = None  # IDs de categorías
    usuarios_permitidos: Optional[List[str]] = None  # IDs de usuarios específicos, None = todos
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ecomerce_cupones"

class CuponCreate(BaseModel):
    codigo: str
    descripcion: str
    tipo_descuento: TipoDescuento
    valor_descuento: float
    monto_minimo: Optional[float] = None
    usos_maximos: Optional[int] = None
    fecha_expiracion: Optional[datetime] = None
    productos_aplicables: Optional[List[str]] = None
    categorias_aplicables: Optional[List[str]] = None
    usuarios_permitidos: Optional[List[str]] = None

class AplicarCuponRequest(BaseModel):
    codigo_cupon: str
    id_carrito: str